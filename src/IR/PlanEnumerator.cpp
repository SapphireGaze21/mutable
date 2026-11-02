#include <mutable/IR/PlanEnumerator.hpp>

#include <algorithm>
#include <bit>
#include <chrono>
#include <cstring>
#include <execution>
#include <functional>
#include <iostream>
#include <iterator>
#include <limits>
#include <memory>
#include <mutable/catalog/Catalog.hpp>
#include <mutable/catalog/CostFunction.hpp>
#include <mutable/util/ADT.hpp>
#include <mutable/util/fn.hpp>
#include <mutable/util/list_allocator.hpp>
#include <mutable/util/malloc_allocator.hpp>
#include <queue>
#include <set>
#include <stdexcept>
#include <type_traits>
#ifdef __BMI2__
#include <x86intrin.h>
#endif


using namespace m;
using namespace m::pe;


/*======================================================================================================================
 * PEall
 *====================================================================================================================*/

/** Computes the join order by enumerating *all* join orders, including Cartesian products. */
struct PEall final : PlanEnumeratorCRTP<PEall>
{
    using base_type = PlanEnumeratorCRTP<PEall>;
    using base_type::operator();

    template<typename PlanTable>
    void operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const {
        auto &sources = G.sources();
        const std::size_t n = sources.size();
        auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();

        for (std::size_t i = 1, end = 1UL << n; i < end; ++i) {
            Subproblem S(i);
            if (S.size() == 1) continue; // skip
            /* Compute break condition to avoid enumerating symmetric subproblems. */
            uint64_t offset = S.capacity() - __builtin_clzl(uint64_t(S));
            M_insist(offset != 0, "invalid subproblem offset");
            Subproblem limit = Subproblem::Singleton(offset - 1);
            for (Subproblem S1(least_subset(S)); S1 != limit; S1 = Subproblem(next_subset(S1, S))) {
                Subproblem S2 = S - S1; // = S \ S1;
                M_insist(PT.has_plan(S1), "must have found the optimal plan for S1");
                M_insist(PT.has_plan(S2), "must have found the optimal plan for S2");
                /* Exploit commutativity of join. */
                cnf::CNF condition; // TODO use join condition
                PT.update(G, CE, CF, S1, S2, condition);
            }
        }
    }
};


/*======================================================================================================================
 * DPsize
 *====================================================================================================================*/

/** Computes the join order using size-based dynamic programming. */
struct DPsize final : PlanEnumeratorCRTP<DPsize>
{
    using base_type = PlanEnumeratorCRTP<DPsize>;
    using base_type::operator();

    mutable std::size_t EvaluatedCounter = 0;
    mutable std::size_t CCPCounter = 0;

    template<typename PlanTable>
    void operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const {
        auto &sources = G.sources();
        std::size_t n = sources.size();
        const AdjacencyMatrix &M = G.adjacency_matrix();
        auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();

        /* Process all subplans of size greater than one. */
        auto t_start = std::chrono::high_resolution_clock::now();
        for (std::size_t s = 2; s <= n; ++s) {
            for (std::size_t s1 = 1; s1 < s; ++s1) {
                std::size_t s2 = s - s1;
                /* Check for all combinations of subsets if they are valid joins and if so, forward the combination to the
                 * plan table. */
                for (auto S1 = GospersHack::enumerate_all(s1, n); S1; ++S1) { // enumerate all subsets of size `s1`
                    if (not PT.has_plan(*S1)) continue; // subproblem S1 not connected -> skip
                    for (auto S2 = GospersHack::enumerate_all(s2, n); S2; ++S2) { // enumerate all subsets of size `s - s1`
                        ++EvaluatedCounter;
                        if (not PT.has_plan(*S2)) continue; // subproblem S2 not connected -> skip
                        if (*S1 & *S2) continue; // subproblems not disjoint -> skip
                        if (not M.is_connected(*S1, *S2)) continue; // subproblems not connected -> skip
                        ++CCPCounter;
                        cnf::CNF condition; // TODO use join condition
                        PT.update(G, CE, CF, *S1, *S2, condition);
                    }
                }
            }
        }
        auto t_end = std::chrono::high_resolution_clock::now();
        auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(t_end - t_start).count();
        std::cout << "EvaluatedCounter = "<< EvaluatedCounter << '\n';
        std::cout << "CCPCounter = "<< CCPCounter << '\n';
        std::cout << "PlanningTime_us = " << elapsed_us << '\n';
    }
};


/*======================================================================================================================
 * DPsizeOpt
 *====================================================================================================================*/

/** Computes the join order using size-based dynamic programming.  In addition to `DPsize`, applies the following
 * optimizations.  First, do not enumerate symmetric subproblems.  Second, in case both subproblems are of equal size,
 * consider only subproblems succeeding the first subproblem. */
struct DPsizeOpt final : PlanEnumeratorCRTP<DPsizeOpt>
{
    using base_type = PlanEnumeratorCRTP<DPsizeOpt>;
    using base_type::operator();

    mutable std::size_t EvaluatedCounter = 0;
    mutable std::size_t CCPCounter = 0;

    template<typename PlanTable>
    void operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const {
        auto &sources = G.sources();
        std::size_t n = sources.size();
        const AdjacencyMatrix &M = G.adjacency_matrix();
        auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();

        /* Process all subplans of size greater than one. */
        auto t_start = std::chrono::high_resolution_clock::now();
        for (std::size_t s = 2; s <= n; ++s) {
            std::size_t m = s / 2; // division with rounding down
            for (std::size_t s1 = 1; s1 <= m; ++s1) {
                std::size_t s2 = s - s1;
                /* Check for all combinations of subsets if they are valid joins and if so, forward the combination to the
                 * plan table. */
                if (s1 == s2) { // exploit commutativity of join: if A⋈ B is possible, so is B⋈ A
                    for (auto S1 = GospersHack::enumerate_all(s1, n); S1; ++S1) { // enumerate all subsets of size `s1`
                        if (not PT.has_plan(*S1)) continue; // subproblem not connected -> skip
                        GospersHack S2 = GospersHack::enumerate_from(*S1, n);
                        for (++S2; S2; ++S2) { // enumerate only the subsets following S1
                            ++EvaluatedCounter;
                            if (not PT.has_plan(*S2)) continue; // subproblem not connected -> skip
                            if (*S1 & *S2) continue; // subproblems not disjoint -> skip
                            if (not M.is_connected(*S1, *S2)) continue; // subproblems not connected -> skip
                            ++CCPCounter;
                            /* Exploit commutativity of join. */
                            cnf::CNF condition; // TODO use join condition
                            PT.update(G, CE, CF, *S1, *S2, condition);
                        }
                    }
                } else {
                    for (auto S1 = GospersHack::enumerate_all(s1, n); S1; ++S1) { // enumerate all subsets of size `s1`
                        if (not PT.has_plan(*S1)) continue; // subproblem not connected -> skip
                        for (auto S2 = GospersHack::enumerate_all(s2, n); S2; ++S2) { // enumerate all subsets of size `s2`
                            ++EvaluatedCounter;
                            if (not PT.has_plan(*S2)) continue; // subproblem not connected -> skip
                            if (*S1 & *S2) continue; // subproblems not disjoint -> skip
                            if (not M.is_connected(*S1, *S2)) continue; // subproblems not connected -> skip
                            ++CCPCounter;
                            /* Exploit commutativity of join. */
                            cnf::CNF condition; // TODO use join condition
                            PT.update(G, CE, CF, *S1, *S2, condition);
                        }
                    }
                }
            }
        }
        auto t_end = std::chrono::high_resolution_clock::now();
        auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(t_end - t_start).count();
        std::cout << "EvaluatedCounter = "<< EvaluatedCounter << '\n';
        std::cout << "CCPCounter = "<< CCPCounter << '\n';
        std::cout << "PlanningTime_us = " << elapsed_us << '\n';
    }
};


/*======================================================================================================================
 * DPsizeSub
 *====================================================================================================================*/

/** Computes the join order using size-based dynamic programming. */
struct DPsizeSub final : PlanEnumeratorCRTP<DPsizeSub>
{
    using base_type = PlanEnumeratorCRTP<DPsizeSub>;
    using base_type::operator();

    template<typename PlanTable>
    void operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const {
        auto &sources = G.sources();
        std::size_t n = sources.size();
        const AdjacencyMatrix &M = G.adjacency_matrix();
        auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();

        /* Process all subplans of size greater than one. */
        for (std::size_t s = 2; s <= n; ++s) {
            for (auto S = GospersHack::enumerate_all(s, n); S; ++S) { // enumerate all subsets of size `s`
                if (not M.is_connected(*S)) continue; // not connected -> skip
                for (Subproblem O(least_subset(*S)); O != *S; O = Subproblem(next_subset(O, *S))) {
                    Subproblem Comp = *S - O;
                    M_insist(M.is_connected(O, Comp), "implied by S inducing a connected subgraph");
                    if (not PT.has_plan(O)) continue; // not connected -> skip
                    if (not PT.has_plan(Comp)) continue; // not connected -> skip
                    cnf::CNF condition; // TODO use join condition
                    PT.update(G, CE, CF, O, Comp, condition);
                }
            }
        }
    }
};


/*======================================================================================================================
 * DPsub
 *====================================================================================================================*/

/** Computes the join order using subset-based dynamic programming. */
struct DPsub final : PlanEnumeratorCRTP<DPsub>
{
    using base_type = PlanEnumeratorCRTP<DPsub>;
    using base_type::operator();

    mutable std::size_t EvaluatedCounter = 0;
    mutable std::size_t CCPCounter = 0;

    template<typename PlanTable>
    void operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const {
        auto &sources = G.sources();
        const std::size_t n = sources.size();
        const AdjacencyMatrix &M = G.adjacency_matrix();
        auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();

    /*  for (std::size_t i = 1, end = 1UL << n; i < end; ++i) {
            Subproblem S(i);
            if (S.size() == 1) continue; // no non-empty and strict subset of S -> skip
            if (not M.is_connected(S)) continue; // not connected -> skip
            for (Subproblem S1(least_subset(S)); S1 != S; S1 = Subproblem(next_subset(S1, S))) {
                Subproblem S2 = S - S1;
                std::cout << "[DPsub] Checking disjoint pair " << S1 << " and " << S2 << " to form " << S << std::endl;
                M_insist(M.is_connected(S1, S2), "implied by S inducing a connected subgraph");
                if (not PT.has_plan(S1)) continue; // not connected -> skip
                if (not PT.has_plan(S2)) continue; // not connected -> skip
                cnf::CNF condition; // TODO use join condition
                PT.update(G, CE, CF, S1, S2, condition);
            }
        }
    } */

        auto t_start = std::chrono::high_resolution_clock::now();
        for (std::size_t i = 1, end = 1UL << n; i < end; ++i) {
            Subproblem S(i);
            if (S.size() == 1)
                continue;
            for (Subproblem S1(least_subset(S));S1 != S;S1 = Subproblem(next_subset(S1, S))){
                Subproblem S2 = S - S1;
                ++EvaluatedCounter;
                if (!M.is_connected(S1))
                    continue;
                if (!M.is_connected(S2))
                    continue;
                if (!M.is_connected(S1, S2))
                    continue;
                ++CCPCounter;
                if (!PT.has_plan(S1))
                    continue;
                if (!PT.has_plan(S2))
                    continue;
                cnf::CNF condition;
                PT.update(G, CE, CF, S1, S2, condition);
            }
        }
        auto t_end = std::chrono::high_resolution_clock::now();
        auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(t_end - t_start).count();
        std::cout << "EvaluatedCounter = "<< EvaluatedCounter << '\n';
        std::cout << "CCPCounter = "<< CCPCounter << '\n';
        std::cout << "PlanningTime_us = " << elapsed_us << '\n';
    }
};


/*======================================================================================================================
 * DPsubOpt
 *====================================================================================================================*/

/** Computes the join order using subset-based dynamic programming.  In comparison to `DPsub`, do not enumerate
 * symmetric subproblems. */
struct DPsubOpt final : PlanEnumeratorCRTP<DPsubOpt>
{
    using base_type = PlanEnumeratorCRTP<DPsubOpt>;
    using base_type::operator();

    template<typename PlanTable>
    void operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const {
        auto &sources = G.sources();
        const std::size_t n = sources.size();
        const AdjacencyMatrix &M = G.adjacency_matrix();
        auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();

        for (std::size_t i = 1, end = 1UL << n; i < end; ++i) {
            Subproblem S(i);
            if (S.size() == 1) continue; // no non-empty and strict subset of S -> skip
            if (not M.is_connected(S)) continue;
            /* Compute break condition to avoid enumerating symmetric subproblems. */
            uint64_t offset = S.capacity() - __builtin_clzl(uint64_t(S));
            M_insist(offset != 0, "invalid subproblem offset");
            Subproblem limit = Subproblem::Singleton(offset - 1);
            for (Subproblem S1(least_subset(S)); S1 != limit; S1 = Subproblem(next_subset(S1, S))) {
                Subproblem S2 = S - S1; // = S \ S1;
                M_insist(M.is_connected(S1, S2), "implied by S inducing a connected subgraph");
                if (not PT.has_plan(S1)) continue; // not connected -> skip
                if (not PT.has_plan(S2)) continue; // not connected -> skip
                /* Exploit commutativity of join. */
                cnf::CNF condition; // TODO use join condition
                PT.update(G, CE, CF, S1, S2, condition);
            }
        }
    }
};


/*======================================================================================================================
 * DPccp
 *====================================================================================================================*/

template<typename PlanTable>
void DPccp::operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const
{
    const AdjacencyMatrix &M = G.adjacency_matrix();
    auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();
    const Subproblem All = SmallBitset::All(G.num_sources());
    cnf::CNF condition; // TODO use join condition

    std::size_t CCPCounter = 0;
    auto t_start = std::chrono::high_resolution_clock::now();

    auto handle_CSG_pair = [&](const Subproblem left, const Subproblem right) {
        ++CCPCounter;
        PT.update(G, CE, CF, left, right, condition);
    };

    M.for_each_CSG_pair_undirected(All, handle_CSG_pair);

    auto t_end = std::chrono::high_resolution_clock::now();
    auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(t_end - t_start).count();
    std::cout << "CCPCounter = " << CCPCounter << '\n';
    std::cout << "PlanningTime_us = " << elapsed_us << '\n';
}


/*======================================================================================================================
 * DPconv
 *====================================================================================================================*/

/**
 * DPconv's Cmax algorithm is a thresholded Boolean subset-convolution DP.  For a threshold W, a subset is feasible iff
 * it is connected, its estimated cardinality is at most W, and it can be split into two feasible disjoint subsets.
 * Ranked zeta transforms and Möbius inversion compute all such splits in O(n^2 2^n), rather than enumerating every
 * connected-subgraph complement pair.  We use Mutable's plan table to cache the estimator's DataModel for each subset,
 * and materialize only the winning join tree back into the plan table.
 *
 * This initial implementation intentionally limits n to 20: Mutable's estimators return polymorphic models, while the
 * convolution itself also needs O(n 2^n) temporary storage.  The upstream implementation uses specialized packed
 * containers and additional optimizations for larger n.
 */
template<typename PlanTable>
void DPconv::operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const
{
    const auto t_start = std::chrono::high_resolution_clock::now();
    const std::size_t n = G.num_sources();
    if (n > 20)
        throw std::invalid_argument("DPconv currently supports at most 20 data sources");
    if (n == 0)
        throw std::invalid_argument("DPconv requires at least one data source");

    const std::size_t N = std::size_t{1} << n;
    const auto &M = G.adjacency_matrix();
    auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();
    const std::uint64_t disconnected = std::numeric_limits<std::uint64_t>::max();
    std::vector<std::uint64_t> cardinalities(N, disconnected);
    std::vector<std::uint8_t> connected(N, false);

    // Seed singleton cardinalities from the scan models Mutable already prepared in the plan table.
    for (std::size_t i = 0; i < n; ++i) {
        const std::uint64_t mask = std::uint64_t{1} << i;
        connected[mask] = true;
        M_insist(bool(PT[Subproblem(mask)].model), "DPconv requires a model for every scan");
        cardinalities[mask] = CE.predict_cardinality(*PT[Subproblem(mask)].model);
    }
    if (n == 1) {
        const auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::high_resolution_clock::now() - t_start).count();
        std::cout << "DPconv_Cmax = 0\nDPconv_Thresholds = 0\nPlanningTime_us = " << elapsed_us << '\n';
        return;
    }

    // Ask the estimator directly for each whole-subproblem model.  This avoids tying the Cmax input to a particular
    // join-tree decomposition, and uses the estimator's intended multi-source API.  The selected tree is subsequently
    // materialized with PT.update(), which calculates Mutable's configured plan cost.
    for (std::size_t size = 2; size <= n; ++size) {
        for (std::uint64_t mask = 1; mask < N; ++mask) {
            if (static_cast<std::size_t>(std::popcount(mask)) != size)
                continue;
            const Subproblem S(mask);
            if (not M.is_connected(S))
                continue;
            connected[mask] = true;
            cnf::CNF condition; // Consistent with current plan enumerators; join-condition estimation is TODO.
            PT[S].model = CE.estimate_join_all(G, PT, S, condition);
            cardinalities[mask] = CE.predict_cardinality(*PT[S].model);
        }
    }

    std::vector<std::uint64_t> thresholds;
    thresholds.reserve(N);
    for (std::uint64_t mask = 1; mask < N; ++mask)
        if (std::popcount(mask) > 1 and connected[mask])
            thresholds.emplace_back(cardinalities[mask]);
    std::sort(thresholds.begin(), thresholds.end());
    thresholds.erase(std::unique(thresholds.begin(), thresholds.end()), thresholds.end());
    if (thresholds.empty() or not connected[N - 1])
        throw std::invalid_argument("DPconv requires a connected query graph with at least one join");

    auto solve_threshold = [&](std::uint64_t W) {
        std::vector<std::uint8_t> feasible(N, false);
        // Ranked subset zeta values: row r at mask S is the sum of feasible r-element subsets of S.
        std::vector<std::uint32_t> ranked((n + 1) * N, 0);
        for (std::uint64_t mask = 1; mask < N; ++mask) {
            if (std::popcount(mask) == 1) {
                feasible[mask] = true; // Base relations are not counted as intermediate results in Cmax.
                ranked[N + mask] = 1;
            }
        }
        for (std::size_t bit = 0; bit < n; ++bit)
            for (std::uint64_t mask = 0; mask < N; ++mask)
                if (mask & (std::uint64_t{1} << bit))
                    ranked[N + mask] += ranked[N + (mask ^ (std::uint64_t{1} << bit))];

        for (std::size_t k = 2; k <= n; ++k) {
            std::vector<std::int64_t> convolution(N, 0);
            for (std::uint64_t mask = 0; mask < N; ++mask) {
                for (std::size_t i = 1; i < k; ++i)
                    convolution[mask] += std::int64_t(ranked[i * N + mask]) * ranked[(k - i) * N + mask];
            }
            // Möbius inversion leaves exactly the ordered disjoint partitions for each k-element subset.
            for (std::size_t bit = 0; bit < n; ++bit)
                for (std::uint64_t mask = 0; mask < N; ++mask)
                    if (mask & (std::uint64_t{1} << bit))
                        convolution[mask] -= convolution[mask ^ (std::uint64_t{1} << bit)];

            for (std::uint64_t mask = 1; mask < N; ++mask) {
                if (std::popcount(mask) != k)
                    continue;
                feasible[mask] = connected[mask] and cardinalities[mask] <= W and convolution[mask] > 0;
                ranked[k * N + mask] = feasible[mask];
            }
            for (std::size_t bit = 0; bit < n; ++bit)
                for (std::uint64_t mask = 0; mask < N; ++mask)
                    if (mask & (std::uint64_t{1} << bit))
                        ranked[k * N + mask] += ranked[k * N + (mask ^ (std::uint64_t{1} << bit))];
        }
        return feasible;
    };

    // Feasibility is monotone in W. Search the sorted set of distinct estimated intermediate cardinalities.
    std::size_t low = 0, high = thresholds.size();
    while (low < high) {
        const std::size_t middle = low + (high - low) / 2;
        const auto feasible = solve_threshold(thresholds[middle]);
        if (feasible[N - 1])
            high = middle;
        else
            low = middle + 1;
    }
    if (low == thresholds.size())
        throw std::runtime_error("DPconv could not find a feasible join tree");
    const std::uint64_t best_cmax = thresholds[low];
    const auto feasible = solve_threshold(best_cmax);

    // Recover a witness split only along the final tree. This costs at most O(2^n) subset checks overall.
    cnf::CNF condition;
    std::function<void(std::uint64_t)> materialize = [&](std::uint64_t mask) {
        if (std::popcount(mask) == 1)
            return;
        bool found = false;
        for (std::uint64_t left = (mask - 1) & mask; left != 0; left = (left - 1) & mask) {
            const std::uint64_t right = mask ^ left;
            if (left >= right or not feasible[left] or not feasible[right])
                continue;
            materialize(left);
            materialize(right);
            PT.update(G, CE, CF, Subproblem(left), Subproblem(right), condition);
            found = true;
            break;
        }
        M_insist(found, "DPconv feasibility result must have a witness split");
    };
    materialize(N - 1);

    const auto t_end = std::chrono::high_resolution_clock::now();
    const auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(t_end - t_start).count();
    std::cout << "DPconv_Cmax = " << best_cmax << '\n';
    std::cout << "DPconv_Thresholds = " << thresholds.size() << '\n';
    std::cout << "PlanningTime_us = " << elapsed_us << '\n';
}


/*======================================================================================================================
 * IK/KBZ
 *====================================================================================================================*/

/** Implements join ordering using the IK/KBZ algorithm.
 *
 * See Toshihide (I)baraki and Tiko (K)ameda. "On the optimal nesting order for computing n-relational joins." and Ravi
 * (K)rishnamurthy, Haran (B)oral, and Carlo (Z)aniolo. "Optimization of Nonrecursive Queries." */
struct IKKBZ final : PlanEnumeratorCRTP<IKKBZ>
{
    using base_type = PlanEnumeratorCRTP<IKKBZ>;
    using base_type::operator();

    template<typename PlanTable>
    std::vector<std::size_t>
    linearize(PlanTable &PT, const QueryGraph &G, const AdjacencyMatrix &M, const CostFunction &CF,
              const CardinalityEstimator &CE) const
    {
        /* Computes the selectivity between two relations, identified by indices `u` and `v`, respectively. */
        auto selectivity = [&](std::size_t u, std::size_t v) {
            const SmallBitset U = SmallBitset::Singleton(u);
            const SmallBitset V = SmallBitset::Singleton(v);
            auto &model_u = *PT[U].model;
            auto &model_v = *PT[V].model;
            auto &joined = PT[U|V];
            if (not joined.model) {
                cnf::CNF condition; // TODO use join condition
                joined.model = CE.estimate_join(G, model_u, model_v, condition);
            }
            const double cardinality_joined = double(CE.predict_cardinality(*joined.model));
            return cardinality_joined / double(CE.predict_cardinality(model_u)) / double(CE.predict_cardinality(model_v));
        };

        /* Compute MST w.r.t. selectivity of join edges.  See Ravi Krishnamurthy, Haran Boral, and Carlo Zaniolo.
         * "Optimization of Nonrecursive Queries." */
        const AdjacencyMatrix MST = M.minimum_spanning_forest(selectivity);

        std::vector<std::size_t> linearization;
        linearization.reserve(G.num_sources());
        std::vector<std::size_t> best_linearization;
        best_linearization.reserve(G.num_sources());
        double least_cost = std::numeric_limits<decltype(least_cost)>::infinity();

        /* The *rank* of a relation is defined as the factor by which the result set grows when joining with this
         * relation.  The rank is defined for a *child* relation and its *parent* relation w.r.t. the MST.
         * "Intuitively, the rank measures the increase in the intermediate result per unit differential cost of doing
         * the join." */
        auto rank = [&](std::size_t parent_id, std::size_t child_id) -> double {
            const SmallBitset parent = SmallBitset::Singleton(parent_id);
            const SmallBitset child = SmallBitset::Singleton(child_id);
            M_insist(MST.is_connected(parent, child), "relations must be joinable");
            M_insist(MST.neighbors(parent)[child_id]);

            const auto &model_parent = *PT[parent].model;
            const auto &model_child = *PT[child].model;
            if (not PT[parent|child].model) {
                cnf::CNF condition; // TODO use join condition
                PT[parent|child].model = CE.estimate_join(G, model_parent, model_child, condition);
            }
            const double cardinality_joined = CE.predict_cardinality(*PT[parent|child].model);
            const double cardinality_parent  = CE.predict_cardinality(model_parent);
            const double cardinality_child  = CE.predict_cardinality(model_child);
            auto g = [](double cardinality) -> double { return 1 * cardinality; }; // TODO adapt to cost function
            return (cardinality_joined - cardinality_parent) / g(cardinality_child);
        };

        struct ranked_relation
        {
            private:
            std::size_t id_;
            double rank_;

            public:
            ranked_relation(std::size_t id, double rank) : id_(id), rank_(rank) { }

            std::size_t id() const { return id_; }
            double rank() const { return rank_; }

            bool operator<(const ranked_relation &other) const { return this->rank() < other.rank(); }
            bool operator>(const ranked_relation &other) const { return this->rank() > other.rank(); }
        };

        /*---- Consider each relation as root and linearize the query tree. -----*/
        for (std::size_t root_id = 0; root_id != G.num_sources(); ++root_id) {
            Subproblem root = Subproblem::Singleton(root_id);

            linearization.clear();
            linearization.emplace_back(root_id);

            /* Initialize MIN heap with successors of root of query tree. */
            std::priority_queue<ranked_relation, std::vector<ranked_relation>, std::greater<ranked_relation>> Q;
            for (std::size_t n : MST.neighbors(root))
                Q.emplace(n, rank(root_id, n));

            Subproblem joined = root;
            while (not Q.empty()) {
                ranked_relation ranked_relation = Q.top();
                Q.pop();

                const Subproblem R = Subproblem::Singleton(ranked_relation.id());
                M_insist((joined & R).empty());
                M_insist(MST.is_connected(joined, R));
                linearization.emplace_back(ranked_relation.id());

                /*----- Join next relation with already joined relations. -----*/
                cnf::CNF condition; // TODO use join condition
                PT.update(G, CE, CF, joined, R, condition);
                joined |= R; // add R to the joined relations

                /*----- Add all children of `R` to the priority queue. -----*/
                const Subproblem N = MST.neighbors(R) - joined;
                for (std::size_t n : N)
                    Q.emplace(n, rank(ranked_relation.id(), n));
            }

            /* Get the cost of the final plan. */
            const double cost = PT[joined].cost;

            /*----- Clear plan table. -----*/
            Subproblem runner = root;
            M_insist(linearization[0] == root_id);
            for (std::size_t i = 1; i != linearization.size(); ++i) {
                const std::size_t R = linearization[i];
                M_insist(not runner[R]);
                runner[R] = true;
                M_insist(not runner.is_singleton());
                M_insist(bool(PT[runner].model), "must have computed a model during linearization");
                M_insist(bool(PT[runner].left), "must have a left subplan");
                M_insist(bool(PT[runner].right), "must have a right subplan");
                PT[runner] = PlanTableEntry();
            }

            if (cost < least_cost) {
                using std::swap;
                swap(best_linearization, linearization);
                least_cost = cost;
            }
        }

        return best_linearization;
    }

    template<typename PlanTable>
    void operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const {
        const AdjacencyMatrix &M = G.adjacency_matrix();
        auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();

        /* Linearize the vertices. */
        const std::vector<std::size_t> linearization = linearize(PT, G, M, CF, CE);
        M_insist(linearization.size() == G.num_sources());

        /*----- Reconstruct the right-deep plan from the linearization. -----*/
        Subproblem right = Subproblem::Singleton(linearization[0]);
        for (std::size_t i = 1; i < G.num_sources(); ++i) {
            const Subproblem left = Subproblem::Singleton(linearization[i]);
            cnf::CNF condition; // TODO use join condition
            PT.update(G, CE, CF, left, right, condition);
            right = left | right;
        }
    }
};


/*======================================================================================================================
 * LinearizedDP
 *====================================================================================================================*/

struct LinearizedDP final : PlanEnumeratorCRTP<LinearizedDP>
{
    using base_type = PlanEnumeratorCRTP<LinearizedDP>;
    using base_type::operator();

    struct Sequence
    {
        private:
        const std::vector<std::size_t> &linearization_;
        ///> the index in the linearization of the first element of this sequence
        std::size_t begin_;
        ///> the index in the linearization one past the last element of this sequence
        std::size_t end_;
        ///> the subproblem formed by this sequence
        Subproblem S_;

        public:
        Sequence(const std::vector<std::size_t> &linearization, std::size_t begin, std::size_t end)
            : linearization_(linearization), begin_(begin), end_(end)
        {
            S_ = compute_subproblem_from_sequence(begin_, end_);
        }

        std::size_t length() const { return end_ - begin_; }
        Subproblem subproblem() const { return S_; }
        /** Returns the index in linearization of the first element of this sequence. */
        std::size_t first_index() const { return begin_; }
        /** Returns the index in linearization of the last element of this sequence. */
        std::size_t last_index() const { return end_ - 1; }
        std::size_t end() const { return end_; }

        std::size_t first() const { return linearization_[first_index()]; }
        std::size_t last() const { return linearization_[last_index()]; }

        bool is_at_front() const { return begin_ == 0; }
        bool is_at_back() const { return end_ == linearization_.size(); }

        Subproblem compute_subproblem_from_sequence(std::size_t begin, std::size_t end) {
            M_insist(begin < end);
            M_insist(end <= linearization_.size());
            Subproblem S;
            while (begin != end)
                S[linearization_[begin++]] = true;
            return S;
        }

        void extend_at_front() {
            M_insist(begin_ > 0);
            --begin_;
            S_[first()] = true;
        }

        void extend_at_back() {
            M_insist(end_ < linearization_.size());
            ++end_;
            S_[last()] = true;
        }

        void shrink_at_front() {
            M_insist(begin_ < end_);
            S_[first()] = false;
            ++begin_;
        }

        void shrink_at_back() {
            M_insist(begin_ < end_);
            S_[last()] = false;
            --end_;
        }

        friend std::ostream & operator<<(std::ostream &out, const Sequence &seq) {
            out << seq.first_index() << '-' << seq.last_index() << ": [";
            for (std::size_t i = seq.first_index(); i <= seq.last_index(); ++i) {
                if (i != seq.first_index()) out << ", ";
                out << seq.linearization_[i];
            }
            return out << ']';
        }

        void dump(std::ostream &out) const { out << *this << std::endl; }
        void dump() const { dump(std::cerr); }
    };

    template<typename PlanTable>
    void operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const {
        if (G.num_sources() <= 1) return;

        auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();
        const AdjacencyMatrix &M = G.adjacency_matrix();
        const std::vector<std::size_t> linearization = IKKBZ{}.linearize(PT, G, M, CF, CE);
        const std::size_t num_relations = G.num_sources();

        Sequence seq(linearization, 0, 2);
        bool moves_right = true;
        for (;;) {
            if (M.is_connected(seq.subproblem())){
                /*----- Consider all dissections of `seq` into two sequences. -----*/
                for (std::size_t mid = seq.first_index() + 1; mid <= seq.last_index(); ++mid) {
                    const Subproblem left = seq.compute_subproblem_from_sequence(seq.first_index(), mid);
                    const Subproblem right = seq.subproblem() - left;

                    const bool is_left_connected = PT.has_plan(left);
                    const bool is_right_connected = PT.has_plan(right);
                    if (is_left_connected and is_right_connected) {
                        cnf::CNF condition; // TODO use join condition
                        PT.update(G, CE, CF, left, right, condition);
                    }
                }
            }

            if (seq.length() == num_relations)
                break;

            /*----- Move and grow the sequence. -----*/
            if (moves_right) {
                if (seq.is_at_back()) [[unlikely]] {
                    moves_right = false;
                    seq.extend_at_front();
                } else {
                    seq.extend_at_back();
                    seq.shrink_at_front();
                }
            } else {
                if (seq.is_at_front()) [[unlikely]] {
                    moves_right = true;
                    seq.extend_at_back();
                } else {
                    seq.extend_at_front();
                    seq.shrink_at_back();
                }
            }
        }
    }
};


/*======================================================================================================================
 * TDbasic
 *====================================================================================================================*/

struct TDbasic final : PlanEnumeratorCRTP<TDbasic>
{
    using base_type = PlanEnumeratorCRTP<TDbasic>;
    using base_type::operator();

    template<typename PlanTable>
    void PlanGen(const QueryGraph &G, const AdjacencyMatrix &M, const CostFunction &CF, const CardinalityEstimator &CE,
                 PlanTable &PT, Subproblem S) const
    {
        if (not PT.has_plan(S)) {
            /* Naive Partitioning */
            /* Iterate over all non-empty and strict subsets in `S`. */
            for (Subproblem sub(least_subset(S)); sub != S; sub = Subproblem(next_subset(sub, S))) {
                Subproblem complement = S - sub;
                /* Check for valid connected subgraph complement pair. */
                if (uint64_t(least_subset(sub)) < uint64_t(least_subset(complement)) and
                    M.is_connected(sub) and M.is_connected(complement))
                {
                    /* Process `sub` and `complement` recursively. */
                    PlanGen(G, M, CF, CE, PT, sub);
                    PlanGen(G, M, CF, CE, PT, complement);

                    /* Update `PlanTable`. */
                    cnf::CNF condition; // TODO use join condition
                    PT.update(G, CE, CF, sub, complement, condition);
                }
            }
        }
    }

    template<typename PlanTable>
    void operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const {
        auto &sources = G.sources();
        std::size_t n = sources.size();
        const AdjacencyMatrix &M = G.adjacency_matrix();
        auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();

        PlanGen(G, M, CF, CE, PT, Subproblem::All(n));
    }
};


/*======================================================================================================================
 * TDMinCutAGaT
 *====================================================================================================================*/

struct TDMinCutAGaT final : PlanEnumeratorCRTP<TDMinCutAGaT>
{
    using base_type = PlanEnumeratorCRTP<TDMinCutAGaT>;
    using base_type::operator();

    template<typename PlanTable>
    void operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const {
        const AdjacencyMatrix &M = G.adjacency_matrix();
        auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();

        auto handle_ccp = [&](const Subproblem first, const Subproblem second) -> void {
            auto recurse = [&](const Subproblem first, const Subproblem second, auto recurse) -> void {
                auto handle_ccp = std::bind(recurse, std::placeholders::_1, std::placeholders::_2, recurse);
                /*----- Solve recursively. -----*/
                if (not PT.has_plan(first))
                    MinCutAGaT{}.partition(M, handle_ccp, first);
                M_insist(PT.has_plan(first));
                if (not PT.has_plan(second))
                    MinCutAGaT{}.partition(M, handle_ccp, second);
                M_insist(PT.has_plan(second));

                /*----- Update `PlanTable`. -----*/
                cnf::CNF condition; // TODO use join condition
                PT.update(G, CE, CF, first, second, condition);
            };
            recurse(first, second, recurse);
        };

        if (G.num_sources() > 1) {
            const Subproblem All = Subproblem::All(G.num_sources());
            MinCutAGaT{}.partition(M, handle_ccp, All);
        }
    }
};


/*======================================================================================================================
 * GOO
 *====================================================================================================================*/

template<typename PlanTable>
void GOO::operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const
{
    const AdjacencyMatrix &M = G.adjacency_matrix();
    auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();

    /*----- Initialize subproblems and their neighbors. -----*/
    node nodes[G.num_sources()];
    for (std::size_t i = 0; i != G.num_sources(); ++i) {
        Subproblem S = Subproblem::Singleton(i);
        Subproblem N = M.neighbors(S);
        nodes[i] = node(S, N);
    }

    /*----- Greedyly enumerate joins, thereby computing a plan. -----*/
    compute_plan(PT, G, M, CF, CE, nodes, nodes + G.num_sources());
}


/*======================================================================================================================
 * TDGOO
 *====================================================================================================================*/

template<typename PlanTable>
void TDGOO::operator()(enumerate_tag, PlanTable &PT, const QueryGraph &G, const CostFunction &CF) const
{
    const AdjacencyMatrix &M = G.adjacency_matrix();
    auto &CE = Catalog::Get().get_database_in_use().cardinality_estimator();

    const Subproblem All = Subproblem::All(G.num_sources());
    std::vector<Subproblem> worklist;
    worklist.reserve(G.num_sources());
    worklist.emplace_back(All);

    /*----- Compute a plan with top-down GOO. -----*/
    auto update_PT = [&](Subproblem left, Subproblem right) {
        PT.update(G, CE, CF, left, right, cnf::CNF{}); // TODO: use actual condition
    };
    for_each_join(update_PT, PT, G, M, CF, CE, std::move(worklist));
}


#define LIST_PE(X) \
    X(DPccp,        "enumerates connected subgraph complement pairs") \
    X(DPconv,       "subset-convolution join ordering minimizing maximum intermediate cardinality") \
    X(DPsize,       "size-based subproblem enumeration") \
    X(DPsizeOpt,    "optimized DPsize: does not enumerate symmetric subproblems") \
    X(DPsizeSub,    "DPsize with enumeration of subset complement pairs") \
    X(DPsub,        "subset-based subproblem enumeration") \
    X(DPsubOpt,     "optimized DPsub: does not enumerate symmetric subproblems") \
    X(GOO,          "Greedy Operator Ordering") \
    X(TDGOO,        "Top-down variant of Greedy Operator Ordering") \
    X(IKKBZ,        "greedy algorithm by IK/KBZ, ordering joins by rank") \
    X(LinearizedDP, "DP with search space linearization based on IK/KBZ") \
    X(TDbasic,      "basic top-down join enumeration using generate-and-test partitioning") \
    X(TDMinCutAGaT, "top-down join enumeration using minimal graph cuts and advanced generate-and-test partitioning") \
    X(PEall,        "enumerates ALL join orders, inclding Cartesian products")

#define INSTANTIATE(NAME, _) \
    template void NAME::operator()(enumerate_tag, PlanTableSmallOrDense &PT, const QueryGraph &G, const CostFunction &CF) const; \
    template void NAME::operator()(enumerate_tag, PlanTableLargeAndSparse &PT, const QueryGraph &G, const CostFunction &CF) const;
LIST_PE(INSTANTIATE)
#undef INSTANTIATE

__attribute__((constructor(202)))
static void register_plan_enumerators()
{
    Catalog &C = Catalog::Get();
#define REGISTER(NAME, DESCRIPTION) \
    C.register_plan_enumerator(C.pool(#NAME), std::make_unique<NAME>(), DESCRIPTION);
LIST_PE(REGISTER)
#undef REGISTER
}
