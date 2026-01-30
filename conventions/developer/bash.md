# Bash/Shell Conventions

## Project Structure

```
scripts/
├── bin/                     # Executable scripts
│   ├── deploy.sh
│   └── backup.sh
├── lib/                     # Shared functions
│   ├── logging.sh
│   ├── utils.sh
│   └── config.sh
├── tests/                   # Test scripts
│   └── test_utils.sh
├── .shellcheckrc            # ShellCheck config
└── README.md
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Script file | snake_case | `deploy_app.sh` |
| Function | snake_case | `log_error` |
| Variable | UPPER_SNAKE_CASE | `DATABASE_HOST` |
| Local variable | lower_snake_case | `local file_path` |
| Constant | UPPER_SNAKE_CASE | `readonly MAX_RETRIES=3` |

## Script Template

```bash
#!/usr/bin/env bash
#
# Script: deploy.sh
# Description: Deploy application to target environment
# Usage: ./deploy.sh [options] <environment>
#

set -euo pipefail
IFS=$'\n\t'

# Constants
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

# Default values
VERBOSE=false
DRY_RUN=false

# Source shared libraries
# shellcheck source=lib/logging.sh
source "${SCRIPT_DIR}/../lib/logging.sh"
# shellcheck source=lib/utils.sh
source "${SCRIPT_DIR}/../lib/utils.sh"

#######################################
# Display usage information
# Globals:
#   SCRIPT_NAME
# Arguments:
#   None
# Outputs:
#   Usage text to stdout
#######################################
usage() {
    cat << EOF
Usage: ${SCRIPT_NAME} [options] <environment>

Deploy application to the specified environment.

Options:
    -h, --help      Show this help message
    -v, --verbose   Enable verbose output
    -n, --dry-run   Show what would be done

Arguments:
    environment     Target environment (dev, staging, prod)

Examples:
    ${SCRIPT_NAME} dev
    ${SCRIPT_NAME} --dry-run prod
EOF
}

#######################################
# Parse command line arguments
# Globals:
#   VERBOSE
#   DRY_RUN
# Arguments:
#   Command line args
# Returns:
#   0 on success, 1 on error
#######################################
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -*)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                ENVIRONMENT="$1"
                shift
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "${ENVIRONMENT:-}" ]]; then
        log_error "Environment is required"
        usage
        exit 1
    fi
}

#######################################
# Main function
# Globals:
#   ENVIRONMENT
#   VERBOSE
#   DRY_RUN
# Arguments:
#   None
# Returns:
#   0 on success, non-zero on error
#######################################
main() {
    parse_args "$@"

    log_info "Deploying to ${ENVIRONMENT}"

    if [[ "${DRY_RUN}" == true ]]; then
        log_info "[DRY RUN] Would deploy to ${ENVIRONMENT}"
        return 0
    fi

    # Deployment logic here
    deploy_application "${ENVIRONMENT}"

    log_info "Deployment complete"
}

# Run main function
main "$@"
```

## Logging Library

```bash
# lib/logging.sh

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_debug() {
    if [[ "${VERBOSE:-false}" == true ]]; then
        echo -e "[DEBUG] $*"
    fi
}
```

## Utilities Library

```bash
# lib/utils.sh

#######################################
# Check if a command exists
# Arguments:
#   Command name
# Returns:
#   0 if exists, 1 otherwise
#######################################
command_exists() {
    command -v "$1" &> /dev/null
}

#######################################
# Retry a command with exponential backoff
# Arguments:
#   max_retries
#   command to run
# Returns:
#   Exit code of command
#######################################
retry() {
    local max_retries="$1"
    shift
    local count=0
    local wait=1

    until "$@"; do
        exit_code=$?
        count=$((count + 1))

        if [[ ${count} -ge ${max_retries} ]]; then
            log_error "Command failed after ${count} attempts"
            return ${exit_code}
        fi

        log_warn "Attempt ${count}/${max_retries} failed. Retrying in ${wait}s..."
        sleep ${wait}
        wait=$((wait * 2))
    done
}

#######################################
# Confirm action with user
# Arguments:
#   Prompt message
# Returns:
#   0 if confirmed, 1 otherwise
#######################################
confirm() {
    local prompt="${1:-Are you sure?}"
    local response

    read -r -p "${prompt} [y/N] " response
    case "${response}" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}
```

## Commands

| Action | Command |
|--------|---------|
| Lint | `shellcheck script.sh` |
| Format | `shfmt -w script.sh` |
| Test | `bats tests/` |
| Debug | `bash -x script.sh` |

## Code Style

- Start with `#!/usr/bin/env bash`
- Use `set -euo pipefail` always
- Quote all variables: `"${var}"`
- Use `[[ ]]` over `[ ]`
- Use `$(command)` over backticks
- Document functions with comments
- Use `local` for function variables
- Use `readonly` for constants
- Handle errors explicitly
- Use meaningful exit codes
