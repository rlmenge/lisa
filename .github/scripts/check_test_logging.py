#!/usr/bin/env python3
"""
Check for log.warning usage in LISA test methods.

This script analyzes Python test files to ensure test methods don't use
log.warning(), which creates ambiguity in test results. Tests should use
log.info() or log.debug() for informational logging, and proper assertions
for validation.
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


class LogWarningChecker(ast.NodeVisitor):
    """AST visitor to find log.warning calls within test methods."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Tuple[int, str, str]] = []
        self.in_test_method = False
        self.current_class = None
        self.current_method = None

    # pylint: disable=invalid-name
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track when we're inside a TestSuite class."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    # pylint: disable=invalid-name
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check if this is a test method and scan for log.warning."""
        old_method = self.current_method
        old_in_test = self.in_test_method

        self.current_method = node.name

        # Check if this is a test method (not before_case, after_case, or private)
        is_test_method = (
            self.current_class
            and not node.name.startswith("_")
            and node.name
            not in ["before_case", "after_case", "before_suite", "after_suite"]
        )

        # Also check for @TestCaseMetadata decorator
        has_test_decorator = any(
            isinstance(dec, ast.Call)
            and isinstance(dec.func, ast.Name)
            and dec.func.id == "TestCaseMetadata"
            for dec in node.decorator_list
        )

        self.in_test_method = is_test_method or has_test_decorator

        self.generic_visit(node)

        self.current_method = old_method
        self.in_test_method = old_in_test

    # pylint: disable=invalid-name
    def visit_Call(self, node: ast.Call) -> None:
        """Check for log.warning() or logger.warning() calls."""
        if self.in_test_method and isinstance(node.func, ast.Attribute):
            if (
                node.func.attr == "warning"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in ["log", "logger"]
            ):
                context = (
                    f"{self.current_class}.{self.current_method}"
                    if self.current_class
                    else self.current_method
                )
                self.violations.append(
                    (node.lineno, context or "unknown", "log.warning()")
                )

        self.generic_visit(node)


def check_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """Check a single Python file for log.warning usage in test methods."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))

        checker = LogWarningChecker(str(filepath))
        checker.visit(tree)
        return checker.violations
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {filepath}: {e}")
        return []
    except Exception as e:
        print(f"⚠️  Error analyzing {filepath}: {e}")
        return []


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: check_test_logging.py <file1.py> [file2.py ...]")
        sys.exit(1)

    all_violations = []

    for filepath_str in sys.argv[1:]:
        filepath = Path(filepath_str)
        if not filepath.exists():
            print(f"⚠️  File not found: {filepath}")
            continue

        violations = check_file(filepath)
        if violations:
            all_violations.extend(
                [(filepath, line, context, call) for line, context, call in violations]
            )

    if all_violations:
        print("\n❌ Found log.warning() usage in test methods:\n")
        for filepath, line, context, call in all_violations:
            print(f"  {filepath}:{line} in {context}")
            print(f"    → {call}")

        print("\n" + "=" * 70)
        print("Test files should not use log.warning() for test validation.")
        print("\nRecommended alternatives:")
        print("  • Use log.info() for informational messages")
        print("  • Use log.debug() for detailed diagnostic information")
        print(
            "  • Use assertions (assert_that, raise SkippedException, etc.) "
            "for validation"
        )
        print("  • Use log.error() only when catching and logging exceptions")
        print("\nWhy avoid log.warning():")
        print(
            "  • Creates ambiguity - is the test passing with issues or "
            "actually passing?"
        )
        print(
            "  • Makes it harder to distinguish real problems from expected "
            "conditions"
        )
        print("  • Tests should either pass, fail, or skip - not pass with warnings")
        print("  • CI systems may treat warnings as failures")
        print("=" * 70)
        sys.exit(1)
    else:
        print("✅ No log.warning usage found in test methods")
        sys.exit(0)


if __name__ == "__main__":
    main()
