#!/usr/bin/env bash
# ==============================================================================
# Automated Benchmarking Script for DNS-SDN Resolution System
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "================================================================="
echo "  Executing DNS-SDN Empirical Performance Evaluation Suite       "
echo "================================================================="

cd "$PROJECT_ROOT"
python3 monitoring/performance_monitor.py --local

echo ""
echo "Evaluating generated artifacts in results/..."
ls -lh "$PROJECT_ROOT/results"

echo "================================================================="
echo "  Benchmarks complete. Open 'results/' to inspect charts & CSVs. "
echo "================================================================="

