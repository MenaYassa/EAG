#!/bin/bash
LOG_FILE="$HOME/ubuntu/logs.md"

# Ensure the directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Initialize the log file
echo "# EAG Test Execution Logs" > "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Function to execute test commands and append to logs.md
run_test() {
    echo "Running: $*" 
    echo "## Command: \`$*\`" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    echo '```text' >> "$LOG_FILE"
    "$@" >> "$LOG_FILE" 2>&1
    echo '```' >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    echo "---" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
}

echo "=================================================="
echo "Running tests. Output is being saved to $LOG_FILE"
echo "=================================================="

# --- TEST COMMANDS (Logged to logs.md) ---
run_test uv run eag run pytest -- -q
run_test uv run eag policy pytest -- -q
run_test uv run pytest tests/test_execution_policy.py -v
run_test uv run pytest tests/test_execution.py -v
run_test uv run pytest tests/test_command.py -v
run_test uv run pytest

echo "=================================================="
echo "Running non-test commands (output printed to terminal)"
echo "=================================================="

# --- NON-TEST COMMANDS (Printed to terminal) ---
uv run eag policy git -- reset --hard HEAD
uv run eag policy git -- commit -m test
uv run eag policy rm -- -rf src
uv run eag run git -- commit -m test
uv run eag run rm -- -rf src
uv run ruff check . --fix
uv run ruff format .
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run eag policy git status
uv run eag policy docker compose ps
uv run eag policy docker compose down
uv run eag policy sudo apt update
uv run eag policy strange-tool hello

echo "=================================================="
echo "Done! Check your test results at $LOG_FILE"
echo "=================================================="
