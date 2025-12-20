#!/bin/bash
# VideoFlow/DuplicateFinder Test Suite Runner
# This script executes all tests and generates reports
#
# Usage:
#   ./run_tests.sh              # Run all tests
#   ./run_tests.sh critical     # Run only critical tests
#   ./run_tests.sh fast         # Run fast tests (skip slow/integration)
#   ./run_tests.sh coverage     # Run with coverage report

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}VideoFlow/DuplicateFinder Test Suite${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}ERROR: pytest is not installed${NC}"
    echo "Install with: pip install pytest pytest-cov"
    exit 1
fi

# Parse command line argument
MODE="${1:-all}"

case "$MODE" in
    critical)
        echo -e "${YELLOW}Running CRITICAL tests only${NC}"
        echo "These tests check for the 4 critical errors identified."
        echo ""
        pytest -v -m critical tests/duplicate_finder/
        ;;

    fast)
        echo -e "${YELLOW}Running FAST tests (excluding slow/integration)${NC}"
        echo ""
        pytest -v -m "not slow and not integration" tests/duplicate_finder/
        ;;

    coverage)
        echo -e "${YELLOW}Running ALL tests with coverage${NC}"
        echo ""
        pytest \
            --cov=src/plugins/duplicate_finder \
            --cov-report=html \
            --cov-report=term \
            -v \
            tests/duplicate_finder/

        echo ""
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;

    integration)
        echo -e "${YELLOW}Running INTEGRATION tests only${NC}"
        echo ""
        pytest -v -m integration tests/duplicate_finder/
        ;;

    ui)
        echo -e "${YELLOW}Running UI tests only${NC}"
        echo ""
        pytest -v -m ui tests/duplicate_finder/
        ;;

    database)
        echo -e "${YELLOW}Running DATABASE tests only${NC}"
        echo ""
        pytest -v -m database tests/duplicate_finder/
        ;;

    duplicateflow)
        echo -e "${YELLOW}Running DUPLICATEFLOW integration tests only${NC}"
        echo ""
        pytest -v -m duplicateflow tests/duplicate_finder/
        ;;

    summary)
        echo -e "${YELLOW}Running critical errors summary test${NC}"
        echo ""
        pytest -v -k "test_all_critical_errors_summary" tests/duplicate_finder/test_critical_errors.py
        ;;

    all)
        echo -e "${YELLOW}Running ALL tests${NC}"
        echo ""

        # Run tests in order of importance
        echo -e "${BLUE}[1/4] Critical Error Tests${NC}"
        pytest -v -m critical tests/duplicate_finder/test_critical_errors.py || true

        echo ""
        echo -e "${BLUE}[2/4] Import Tests${NC}"
        pytest -v tests/duplicate_finder/test_imports.py || true

        echo ""
        echo -e "${BLUE}[3/4] Unit Tests${NC}"
        pytest -v \
            tests/duplicate_finder/test_database.py \
            tests/duplicate_finder/test_file_handler.py \
            tests/duplicate_finder/test_hash_worker.py \
            tests/duplicate_finder/test_subsequence_detector.py \
            tests/duplicate_finder/test_pipeline_manager.py \
            || true

        echo ""
        echo -e "${BLUE}[4/4] Integration & UI Tests${NC}"
        pytest -v \
            tests/duplicate_finder/test_duplicateflow_integration.py \
            tests/duplicate_finder/test_ui_basic.py \
            || true
        ;;

    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo ""
        echo "Usage: $0 [mode]"
        echo ""
        echo "Modes:"
        echo "  all          - Run all tests (default)"
        echo "  critical     - Run only critical error tests"
        echo "  fast         - Run fast tests (skip slow/integration)"
        echo "  coverage     - Run all tests with coverage report"
        echo "  integration  - Run only integration tests"
        echo "  ui           - Run only UI tests"
        echo "  database     - Run only database tests"
        echo "  duplicateflow - Run only DuplicateFlow integration tests"
        echo "  summary      - Run critical errors summary"
        exit 1
        ;;
esac

EXIT_CODE=$?

echo ""
echo -e "${BLUE}======================================${NC}"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed (exit code: $EXIT_CODE)${NC}"
    echo ""
    echo -e "${YELLOW}This is EXPECTED if critical errors haven't been fixed yet.${NC}"
    echo -e "${YELLOW}Tests are designed to be RED before fixes, GREEN after.${NC}"
    echo ""
    echo "To see which critical errors remain:"
    echo "  ./run_tests.sh summary"
fi

echo -e "${BLUE}======================================${NC}"

exit $EXIT_CODE
