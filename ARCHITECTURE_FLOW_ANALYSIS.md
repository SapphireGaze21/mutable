# Mutable Database Engine — Query Execution Flow Analysis

During the course of the ISRP work, an in-depth analysis of Mutable's query compilation pipeline was conducted to understand exactly how a SQL query is parsed, optimized, and executed via WebAssembly (Wasm) Just-In-Time (JIT) compilation. 

The pipeline is strictly divided into three mathematical and structural representations.

---

## 1. The Query Graph (The "What you asked for" Stage)
When a SQL query is submitted, the parser builds a **Query Graph** directly from the Abstract Syntax Tree (AST).
* **Nodes:** Represent the base relations/tables (e.g., `Table A`, `Table B`).
* **Edges:** Represent the `WHERE` or `JOIN` conditions connecting them (e.g., `A.id = B.id`).
* **Purpose:** The Query Graph models the structure of the SQL query but has **no order of execution**. It simply defines the constraints.
* **Role in our work:** This is the exact data structure passed *into* the dynamic programming algorithms (`DPsize`, `DPsub`, `DPccp`). The DP algorithms analyze this graph to find all valid connected sub-graphs (CSGs) to determine the optimal join sequence.

---

## 2. The Logical Plan (The "Order of Operations" Stage)
Once the DP algorithms (`plan_enumerator`) finish evaluating the O(3ⁿ) search space of the Query Graph, the optimizer outputs a **Logical Plan** (Logical Operator Tree).
* **Nodes:** Are relational algebra operators (e.g., `JoinOperator`, `FilterOperator`, `ProjectionOperator`).
* **Edges:** Represent the flow of data (rows flowing from children to parent operators).
* **Purpose:** The Logical Plan dictates the strict **order of operations**. For example, it defines: *"Join table A and B together first, then take that intermediate result and join it with C."*
* **Key Characteristic:** It is purely abstract/mathematical. It knows *what* operations must occur (a join), but it doesn't know *how* to physically execute them (e.g., hash join vs. nested loops).

---

## 3. The Physical Plan (The "How to execute it" Stage)
The purely abstract Logical Plan is passed to the `PhysicalOptimizer`. The Wasm backend registers all its available physical algorithms, and the optimizer runs a "tree covering" algorithm (similar to instruction selection in compilers) to map logical operators to physical algorithms.
* **Nodes:** Are concrete physical algorithms (e.g., `Match<wasm::NestedLoopsJoin>`, `Match<wasm::SimpleHashJoin>`, `Match<wasm::SortMergeJoin>`).
* **Edges:** Still represent the flow of data, but are now tied to real memory buffers and WebAssembly pipelines.
* **Purpose:** It replaces abstract math with code generation blueprints. For example, it decides: *"Build a Hash Table in memory for table A, and then iterate through table B to probe the hash table."*

---

## 4. JIT Compilation and Execution (`WasmOperator.hpp`)
Because Mutable is a compiling database engine (rather than an interpreting one), physical operators don't just run loops in C++. Instead, every physical operator has an `execute()` method that **generates WebAssembly code**.
* **Setup:** Generates Wasm to allocate memory and initialize structures (like hash tables).
* **Pipeline:** Generates Wasm nested loops to iterate over rows, evaluate join conditions inline, and pipe matching rows to the next operator.
* **Teardown:** Generates Wasm to clean up allocations.

The backend then compiles this generated Wasm bytecode directly into raw machine code, executing the query in a fraction of the time of a traditional interpreted engine.
