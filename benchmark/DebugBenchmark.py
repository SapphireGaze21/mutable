#!/usr/bin/env python3
import sys
import os

# Ensure the benchmark directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import Benchmark
from database_connectors.connector import Connector
import argparse

# Save the original benchmark_query function
orig_benchmark_query = Connector.benchmark_query

# Create a wrapper that forcefully prints the stdout of the database executable
def debug_benchmark_query(self, command, query, timeout, benchmark_info, verbose, popen_args=dict(), encode_query=True):
    print("\n\n" + "="*80)
    print("DEBUG RUNNING COMMAND:")
    print(" ".join([str(c) for c in command]))
    print("="*80)
    print("DEBUG QUERY:")
    print(query)
    print("="*80)

    # Call the original function to actually run the shell executable
    out = orig_benchmark_query(self, command, query, timeout, benchmark_info, verbose, popen_args, encode_query)

    print("DEBUG STANDARD OUTPUT FROM MUTABLE SHELL:")
    print(out)
    print("="*80 + "\n\n")
    return out

# Inject our wrapper into the Connector class
Connector.benchmark_query = debug_benchmark_query

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run benchmarks on mutable while printing all hidden output.')
    parser.add_argument('path', nargs='*', help='directory path of a benchmark suite or path to single experiment to be run')
    parser.add_argument('--no-compare', dest='compare', default=True, action='store_false', help='Skip comparison to other systems')
    parser.add_argument('-o', '--output', dest='output', metavar='FILE.csv', default=None, action='store')
    parser.add_argument('--args', dest='binargs', metavar='ARGS', default=None, action='store')
    parser.add_argument('-n', '--num-runs', dest='num_runs', metavar='RUNS', default=1, action='store', type=int)
    parser.add_argument('-v', '--verbose', help='verbose output', dest='verbose', default=True, action='store_true')
    parser.add_argument('--pgsql', dest='pgsql', default=False, action='store_true')
    # Default to the build directory you are actually using for your debugging!
    parser.add_argument('-b', '--builddir', help='path to the build directory', default=os.path.join('build', 'debug_shared'), type=str, metavar='PATH')

    args = parser.parse_args()

    # Forward the execution back to Benchmark.py but with our new args and injected logger
    Benchmark.run_benchmarks(args)
