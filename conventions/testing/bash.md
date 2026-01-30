# Bash/Shell Testing Conventions

## Test Structure

```
scripts/
├── bin/
│   └── deploy.sh
├── lib/
│   └── utils.sh
└── tests/
    ├── test_helper.bash       # Shared test utilities
    ├── deploy.bats            # Tests for deploy.sh
    ├── utils.bats             # Tests for utils.sh
    └── fixtures/
        └── config.txt
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{script}.bats` | `deploy.bats` |
| Test function | `@test "description"` | `@test "deploys to dev"` |
| Helper | `test_helper.bash` | `test_helper.bash` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | Bats | Bash Automated Testing System |
| Assertions | bats-assert | Assertion helpers |
| File utilities | bats-file | File assertions |
| Mocking | bats-mock | Command mocking |
| Linting | ShellCheck | Static analysis |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `bats tests/` |
| Run file | `bats tests/deploy.bats` |
| Verbose | `bats -v tests/` |
| TAP output | `bats -t tests/` |
| Lint | `shellcheck scripts/**/*.sh` |

## Bats Test File

```bash
#!/usr/bin/env bats

# Load test helpers
load 'test_helper'
load 'bats-support/load'
load 'bats-assert/load'
load 'bats-file/load'

# Setup - runs before each test
setup() {
    # Create temp directory
    TEST_TEMP_DIR="$(mktemp -d)"
    export TEST_TEMP_DIR

    # Source the script under test
    source "${BATS_TEST_DIRNAME}/../lib/utils.sh"
}

# Teardown - runs after each test
teardown() {
    # Clean up temp files
    rm -rf "${TEST_TEMP_DIR}"
}

@test "command_exists returns 0 for existing command" {
    run command_exists "bash"
    assert_success
}

@test "command_exists returns 1 for non-existing command" {
    run command_exists "nonexistent_command_12345"
    assert_failure
}

@test "log_info outputs message with INFO prefix" {
    run log_info "test message"
    assert_success
    assert_output --partial "[INFO]"
    assert_output --partial "test message"
}

@test "log_error outputs to stderr" {
    run log_error "error message"
    assert_output --partial "[ERROR]"
}

@test "retry succeeds on first attempt" {
    run retry 3 true
    assert_success
}

@test "retry fails after max attempts" {
    run retry 2 false
    assert_failure
    assert_output --partial "failed after 2 attempts"
}

@test "confirm returns 0 for yes input" {
    run bash -c 'echo "y" | source lib/utils.sh && confirm "Continue?"'
    assert_success
}

@test "confirm returns 1 for no input" {
    run bash -c 'echo "n" | source lib/utils.sh && confirm "Continue?"'
    assert_failure
}
```

## Testing Script Execution

```bash
#!/usr/bin/env bats

load 'test_helper'
load 'bats-support/load'
load 'bats-assert/load'

SCRIPT="${BATS_TEST_DIRNAME}/../bin/deploy.sh"

setup() {
    TEST_TEMP_DIR="$(mktemp -d)"
    export TEST_TEMP_DIR
}

teardown() {
    rm -rf "${TEST_TEMP_DIR}"
}

@test "deploy.sh shows help with --help" {
    run "${SCRIPT}" --help
    assert_success
    assert_output --partial "Usage:"
    assert_output --partial "environment"
}

@test "deploy.sh fails without environment" {
    run "${SCRIPT}"
    assert_failure
    assert_output --partial "Environment is required"
}

@test "deploy.sh accepts valid environment" {
    run "${SCRIPT}" --dry-run dev
    assert_success
    assert_output --partial "Would deploy to dev"
}

@test "deploy.sh rejects invalid option" {
    run "${SCRIPT}" --invalid-option
    assert_failure
    assert_output --partial "Unknown option"
}

@test "deploy.sh verbose mode shows debug output" {
    run "${SCRIPT}" --verbose --dry-run dev
    assert_success
    # Verify verbose output if applicable
}
```

## Mocking Commands

```bash
#!/usr/bin/env bats

load 'test_helper'
load 'bats-support/load'
load 'bats-assert/load'

setup() {
    # Create mock command directory
    MOCK_DIR="$(mktemp -d)"
    export PATH="${MOCK_DIR}:${PATH}"
}

teardown() {
    rm -rf "${MOCK_DIR}"
}

# Create a mock command
create_mock() {
    local cmd="$1"
    local exit_code="${2:-0}"
    local output="${3:-}"

    cat > "${MOCK_DIR}/${cmd}" << EOF
#!/bin/bash
echo "${output}"
exit ${exit_code}
EOF
    chmod +x "${MOCK_DIR}/${cmd}"
}

@test "handles kubectl failure gracefully" {
    create_mock "kubectl" 1 "connection refused"

    source "${BATS_TEST_DIRNAME}/../lib/deploy.sh"

    run deploy_to_kubernetes "dev"
    assert_failure
    assert_output --partial "connection refused"
}

@test "retries on transient failure" {
    # First call fails, second succeeds
    local call_count=0

    kubectl() {
        call_count=$((call_count + 1))
        if [[ ${call_count} -lt 2 ]]; then
            return 1
        fi
        return 0
    }
    export -f kubectl

    source "${BATS_TEST_DIRNAME}/../lib/utils.sh"

    run retry 3 kubectl apply -f manifest.yaml
    assert_success
}
```

## Test Helper

```bash
# tests/test_helper.bash

# Get the directory containing the test files
BATS_TEST_DIRNAME="$(cd "$(dirname "${BATS_TEST_FILENAME}")" && pwd)"

# Project root
PROJECT_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"

# Helper to run script with environment
run_script() {
    local script="$1"
    shift
    run bash "${PROJECT_ROOT}/bin/${script}" "$@"
}

# Helper to create test fixture
create_fixture() {
    local name="$1"
    local content="$2"
    echo "${content}" > "${TEST_TEMP_DIR}/${name}"
}

# Helper to assert file contains
assert_file_contains() {
    local file="$1"
    local expected="$2"
    grep -q "${expected}" "${file}" || {
        echo "Expected '${expected}' not found in ${file}"
        cat "${file}"
        return 1
    }
}
```

## ShellCheck Configuration

```yaml
# .shellcheckrc
# Ignore specific codes
disable=SC2034  # Unused variable (often used by sourced files)

# Shell to use
shell=bash

# External sources
source-path=lib

# Enable optional checks
enable=require-variable-braces
enable=deprecate-which
```

## Coverage Target

- Test all public functions
- Test error paths and edge cases
- Test argument parsing
- Lint all scripts with ShellCheck
