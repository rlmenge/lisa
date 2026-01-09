# Test Logging Standards Checker

This workflow ensures that test methods in LISA don't use `log.warning()`, which creates ambiguity in test results.

## What it Checks

The workflow analyzes Python test files changed in pull requests to detect usage of:
- `log.warning()`
- `logger.warning()`

It specifically checks only within **test methods** (not in helper functions, setup/teardown methods, or utilities).

## Why This Matters

Tests should have clear, unambiguous outcomes:
- ✅ **PASSED** - The test validated the expected behavior successfully
- ❌ **FAILED** - The test found a problem or assertion failed  
- ⏭️ **SKIPPED** - The test cannot run in this environment/configuration

Using `log.warning()` creates a confusing fourth state: "passed but with warnings" which makes it unclear whether:
- The test truly passed and the warning is informational
- The test passed but something concerning happened
- The test should have failed or been skipped

## What to Use Instead

| Instead of... | Use... | When... |
|--------------|--------|---------|
| `log.warning()` | `log.info()` | Providing informational messages about test progress |
| `log.warning()` | `log.debug()` | Logging detailed diagnostic information |
| `log.warning()` | `raise SkippedException()` | Test cannot run due to missing requirements |
| `log.warning()` | `assert_that()` or assertions | Validating test expectations |
| `log.warning()` | `log.error()` + raise | Catching and logging exceptions |

## Example Violations

❌ **Bad** - Using warning for test validation:
```python
def verify_feature(self, log: Logger, node: Node) -> None:
    result = node.tools[MyTool].check_feature()
    if not result.success:
        log.warning(f"Feature check failed: {result.message}")
```

✅ **Good** - Use proper assertions:
```python
def verify_feature(self, log: Logger, node: Node) -> None:
    result = node.tools[MyTool].check_feature()
    assert_that(result.success).described_as(
        f"Feature check should succeed: {result.message}"
    ).is_true()
```

❌ **Bad** - Using warning for missing requirements:
```python
def verify_advanced_feature(self, log: Logger, node: Node) -> None:
    if not node.tools[MyTool].has_advanced_support():
        log.warning("Advanced feature not supported, skipping...")
        return
```

✅ **Good** - Use SkippedException:
```python
def verify_advanced_feature(self, log: Logger, node: Node) -> None:
    if not node.tools[MyTool].has_advanced_support():
        raise SkippedException("Advanced feature not supported on this system")
```

## When log.warning() IS Acceptable

The checker allows `log.warning()` in:
- Helper functions and utilities (non-test methods)
- `before_case` and `after_case` methods
- Private methods (starting with `_`)
- Tool implementations (in `lisa/tools/`)
- Platform/orchestrator code

## Files Checked

- `lisa/microsoft/testsuites/**/*.py` - Microsoft test suites
- `lisa/examples/testsuites/**/*.py` - Example test suites
- `selftests/**/*.py` - LISA self-tests

## How It Works

1. **Pull Request Trigger**: Runs when PR modifies Python files in test directories
2. **File Collection**: Identifies changed test files using git diff
3. **AST Analysis**: Uses Python's AST parser to find `log.warning()` calls within test methods
4. **Report**: Fails the check if violations found, providing line numbers and context

## Local Testing

Test your changes before pushing:

```bash
# Check specific files
python3 .github/scripts/check_test_logging.py \
    lisa/microsoft/testsuites/network/xfrm.py

# Check multiple files
python3 .github/scripts/check_test_logging.py \
    lisa/microsoft/testsuites/**/*.py

# Check files changed in your branch
git diff --name-only --diff-filter=AM origin/main...HEAD | \
  grep -E '^(lisa/microsoft/testsuites|selftests)/.*\.py$' | \
  xargs python3 .github/scripts/check_test_logging.py
```

## Workflow Files

- `.github/workflows/check-test-logging.yml` - GitHub Actions workflow definition
- `.github/scripts/check_test_logging.py` - Python AST-based checker script

## Contributing

If you believe a specific use of `log.warning()` in a test method is justified, please:
1. Document why in the PR description
2. Consider if there's a better pattern (skip, assertion, etc.)
3. Discuss with reviewers
