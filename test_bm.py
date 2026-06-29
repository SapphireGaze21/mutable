import sys
import argparse
from argparse import Namespace

import benchmark.Benchmark as BM

args = Namespace(path=['tpcds queries/tpcds-kit/query_templates/query91.tpl'], output=None, binargs=None, num_runs=1, verbose=True, pgsql=False, compare=False, builddir='build/debug_shared')
BM.run_benchmarks(args)
