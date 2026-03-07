## Tool Usage Standards Checker

This workflow ensures that test methods use tool wrappers instead of raw `node.execute()` calls when appropriate tools exist.

## What it Checks

The workflow analyzes Python test files changed in pull requests to detect usage of `node.execute()` or `node.execute_async()` with commands that have corresponding tool wrappers.

It specifically checks only within **test methods** (not in helper functions, setup/teardown methods, utilities, or Tool implementations).

## Why This Matters

Using tool wrappers instead of raw `node.execute()` provides numerous benefits:

### Better Abstraction
- Tools encapsulate command details and platform differences
- Cleaner, more readable test code
- Easier to understand intent

### Consistent Error Handling
- Tools provide standardized error messages
- Built-in retry logic where appropriate
- Graceful handling of missing commands

### Type Safety
- IDE auto-completion and type checking
- Catch errors at development time
- Better refactoring support

### Maintainability
- Changes to command syntax handled in one place
- Easier to mock for unit testing
- Reduced code duplication

### Capability Checking
- Tools can check if command is installed
- Automatic installation when possible
- Clear skip messages when unavailable

## Common Command → Tool Mappings

| Command | Tool Class | Import |
|---------|------------|--------|
| `ip` | `Ip` | `from lisa.tools import Ip` |
| `echo` | `Echo` | `from lisa.tools import Echo` |
| `cat` | `Cat` | `from lisa.base_tools import Cat` |
| `ls` | `Ls` | `from lisa.tools import Ls` |
| `mkdir` | `Mkdir` | `from lisa.tools import Mkdir` |
| `rm` | `Rm` | `from lisa.tools import Rm` |
| `cp` | `Cp` | `from lisa.tools import Cp` |
| `mv` | `Mv` | `from lisa.base_tools import Mv` |
| `grep` | `Grep` | `from lisa.tools import Grep` |
| `find` | `Find` | `from lisa.tools import Find` |
| `tar` | `Tar` | `from lisa.tools import Tar` |
| `git` | `Git` | `from lisa.tools import Git` |
| `curl` | `Curl` | `from lisa.tools import Curl` |
| `wget` | `Wget` | `from lisa.base_tools import Wget` |
| `ping` | `Ping` | `from lisa.tools import Ping` |
| `ssh` | `Ssh` | `from lisa.tools import Ssh` |
| `reboot` | `Reboot` | `from lisa.tools import Reboot` |
| `systemctl` | `Service` | `from lisa.base_tools import Service` |
| `uname` | `Uname` | `from lisa.base_tools import Uname` |
| `lscpu` | `Lscpu` | `from lisa.tools import Lscpu` |
| `lspci` | `Lspci` | `from lisa.tools import Lspci` |
| `lsblk` | `Lsblk` | `from lisa.tools import Lsblk` |
| `lsmod` | `Lsmod` | `from lisa.tools import Lsmod` |
| `modprobe` | `Modprobe` | `from lisa.tools import Modprobe` |
| `dmesg` | `Dmesg` | `from lisa.tools import Dmesg` |
| `mount` / `umount` | `Mount` | `from lisa.tools import Mount` |
| `df` | `Df` | `from lisa.tools import Df` |
| `fdisk` | `Fdisk` | `from lisa.tools import Fdisk` |
| `parted` | `Parted` | `from lisa.tools import Parted` |
| `mkfs` | `Mkfs` | `from lisa.tools import Mkfs` |
| `free` | `Free` | `from lisa.tools import Free` |
| `ethtool` | `Ethtool` | `from lisa.tools import Ethtool` |
| `iperf3` | `Iperf3` | `from lisa.tools import Iperf3` |
| `fio` | `Fio` | `from lisa.tools import Fio` |
| `stress-ng` | `StressNg` | `from lisa.tools import StressNg` |
| `docker` | `Docker` | `from lisa.tools import Docker` |
| `make` | `Make` | `from lisa.tools import Make` |
| `gcc` | `Gcc` | `from lisa.tools import Gcc` |
| `python` / `python3` | `Python` | `from lisa.tools import Python` |
| `pip` / `pip3` | `Pip` | `from lisa.tools import Pip` |

For a complete list, see `lisa/tools/__init__.py`.

## Example Violations

### ❌ Bad - Using raw execute for ip command

```python
def verify_network(self, log: Logger, node: Node) -> None:
    result = node.execute("ip addr show eth0")
    log.info(result.stdout)
```

### ✅ Good - Using Ip tool wrapper

```python
from lisa.tools import Ip

def verify_network(self, log: Logger, node: Node) -> None:
    ip = node.tools[Ip]
    result = ip.run("addr show eth0")
    log.info(result.stdout)
```

### ❌ Bad - Using raw execute for echo

```python
def test_file_write(self, node: Node) -> None:
    node.execute("echo 'test' > /tmp/test.txt", shell=True, sudo=True)
```

### ✅ Good - Using Echo tool wrapper

```python
from lisa.tools import Echo

def test_file_write(self, node: Node) -> None:
    echo = node.tools[Echo]
    echo.write_to_file("test", node.get_pure_path("/tmp/test.txt"), sudo=True)
```

### ❌ Bad - Multiple commands in one execute

```python
def setup_environment(self, node: Node) -> None:
    node.execute("mkdir -p /tmp/test && cd /tmp/test && git clone https://example.com/repo.git", shell=True)
```

### ✅ Good - Using multiple tools

```python
from lisa.tools import Mkdir, Git

def setup_environment(self, node: Node) -> None:
    mkdir = node.tools[Mkdir]
    mkdir.create_directory("/tmp/test", sudo=False)
    
    git = node.tools[Git]
    git.clone("https://example.com/repo.git", cwd="/tmp/test")
```

## When node.execute() IS Acceptable

The checker allows `node.execute()` in:

1. **Helper functions and utilities** (non-test methods)
2. **`before_case` and `after_case` methods**
3. **Private methods** (starting with `_`)
4. **Tool implementations** (files in `lisa/tools/` or `lisa/base_tools/`)
5. **Complex shell scripts** where no tool exists
6. **One-off commands** during development (but should be refactored to use tools before merging)

If you're executing a command for which no tool exists, consider creating a new tool!

## Creating a New Tool

If you need to run a command repeatedly and no tool exists:

1. Check `lisa/tools/` to verify the tool doesn't exist
2. Create a new file in `lisa/tools/` (e.g., `mytool.py`)
3. Inherit from `Tool` base class
4. Implement required methods:
   - `command` property (returns command name)
   - `can_install()` if the tool can be installed
   - `_install()` if installation is supported
5. Add convenience methods for common operations
6. Export the tool in `lisa/tools/__init__.py`

Example minimal tool:

```python
from lisa.executable import Tool

class MyTool(Tool):
    @property
    def command(self) -> str:
        return "mytool"
    
    def can_install(self) -> bool:
        return True
    
    def _install(self) -> bool:
        self.node.os.install_packages("mytool")
        return self._check_exists()
    
    def do_something(self, param: str) -> str:
        result = self.run(f"--option {param}", force_run=True)
        return result.stdout
```

## Files Checked

- `lisa/microsoft/testsuites/**/*.py` - Microsoft test suites
- `lisa/examples/testsuites/**/*.py` - Example test suites
- `selftests/**/*.py` - LISA self-tests

## How It Works

1. **Pull Request Trigger**: Runs when PR modifies Python files in test directories
2. **File Collection**: Identifies changed test files using git diff
3. **AST Analysis**: Uses Python's AST parser to find `node.execute()` calls within test methods
4. **Command Pattern Matching**: Checks if commands match known tool patterns
5. **Report**: Fails the check if violations found, suggesting the appropriate tool

## Local Testing

Test your changes before pushing:

```bash
# Check specific files
python3 .github/scripts/check_tool_usage.py \
    lisa/microsoft/testsuites/network/xfrm.py

# Check multiple files
python3 .github/scripts/check_tool_usage.py \
    lisa/microsoft/testsuites/**/*.py

# Check files changed in your branch
git diff --name-only --diff-filter=AM origin/main...HEAD | \
  grep -E '^(lisa/microsoft/testsuites|selftests)/.*\.py$' | \
  xargs python3 .github/scripts/check_tool_usage.py
```

## Workflow Files

- `.github/workflows/check-tool-usage.yml` - GitHub Actions workflow definition
- `.github/scripts/check_tool_usage.py` - Python AST-based checker script

## Finding Available Tools

To discover available tools:

```bash
# List all tool files
ls lisa/tools/

# See all exported tools
grep "^class " lisa/tools/*.py

# Check imports in __init__.py
cat lisa/tools/__init__.py

# Search for tool usage in tests
grep -r "node.tools\[" lisa/microsoft/testsuites/
```

## Contributing

If you need to use `node.execute()` in a test method:

1. First, check if an appropriate tool exists
2. If no tool exists, consider creating one
3. If creating a tool is not feasible, document why in the PR
4. Discuss with reviewers whether an exception is warranted

Remember: Tool wrappers make tests more maintainable and reliable!
