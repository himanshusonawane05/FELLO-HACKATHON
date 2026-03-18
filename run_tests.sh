#!/usr/bin/env bash
# Fello AI Account Intelligence — Test Runner (Linux/macOS)
#
# Usage:
#   ./run_tests.sh              # Run all fast unit + integration tests
#   ./run_tests.sh --fast       # Run only domain + storage tests (no LLM/network)
#   ./run_tests.sh --e2e        # Run end-to-end API validation (requires running backend)
#   ./run_tests.sh --all        # Run everything including pipeline tests

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=$(command -v python3 || command -v python)
MODE="default"
BASE_URL="http://localhost:8000/api/v1"

for arg in "$@"; do
    case $arg in
        --fast) MODE="fast" ;;
        --e2e) MODE="e2e" ;;
        --all) MODE="all" ;;
        --base-url=*) BASE_URL="${arg#*=}" ;;
    esac
done

echo ""
echo "  Fello AI — Test Runner"
echo "  ======================="
echo ""

# Install test dependencies
echo "  Installing test dependencies..."
$PYTHON -m pip install -r "$ROOT/requirements.txt" -r "$ROOT/requirements-dev.txt" -q

case $MODE in
    e2e)
        echo "  Running E2E API validation against $BASE_URL ..."
        $PYTHON "$ROOT/e2e-tests/validate_api.py" --base-url "$BASE_URL"
        ;;
    fast)
        echo "  Running fast tests (domain + storage, no LLM/network)..."
        $PYTHON -m pytest \
            "$ROOT/tests/test_domain.py" \
            "$ROOT/tests/test_storage.py" \
            "$ROOT/tests/test_sqlite_store.py" \
            -v --tb=short
        ;;
    all)
        echo "  Running ALL tests (includes pipeline tests that call real LLM)..."
        echo "  NOTE: Pipeline tests may take 5-10 minutes."
        $PYTHON -m pytest "$ROOT/tests" -v --tb=short
        ;;
    *)
        echo "  Running unit + API tests (excludes slow pipeline tests)..."
        echo "  Use --all to include pipeline tests, --fast for storage/domain only."
        echo ""
        $PYTHON -m pytest \
            "$ROOT/tests/test_domain.py" \
            "$ROOT/tests/test_storage.py" \
            "$ROOT/tests/test_sqlite_store.py" \
            "$ROOT/tests/test_api.py" \
            -v --tb=short -x
        ;;
esac
