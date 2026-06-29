#!/bin/bash
lldb build/debug_shared/bin/shell --batch -o "run --dryrun benchmark/tpcds/query_templates_flat/query12.sql" -o "bt" -o "quit"
