import sys
import benchmark.Benchmark as BM
from argparse import Namespace

args = Namespace(path=['tpcds queries/tpcds-kit/query_templates/query91.tpl'], output=None, binargs=None, num_runs=1, verbose=True, pgsql=False, compare=False, builddir='build/debug_shared')
BM.run_benchmarks(args)
