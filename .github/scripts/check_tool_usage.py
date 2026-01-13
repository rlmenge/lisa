#!/usr/bin/env python3
"""
Check for node.execute() usage when tool wrappers exist.

This script analyzes Python test files to ensure tests use tool wrappers
instead of raw node.execute() calls when appropriate tools exist. Using
tool wrappers provides better abstraction, error handling, and maintainability.
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Mapping of common command patterns to their tool classes
# Format: command_pattern -> (ToolClass, description)
COMMAND_TO_TOOL: Dict[str, Tuple[str, str]] = {
    r"\bip\s+": ("Ip", "IP address and routing management"),
    r"\becho\s+": ("Echo", "echo command wrapper"),
    r"\bcat\s+": ("Cat", "concatenate and display files"),
    r"\bls\s+": ("Ls", "list directory contents"),
    r"\bmkdir\s+": ("Mkdir", "create directories"),
    r"\brm\s+": ("Rm", "remove files and directories"),
    r"\bcp\s+": ("Cp", "copy files and directories"),
    r"\bmv\s+": ("Mv", "move or rename files"),
    r"\bchmod\s+": ("Chmod", "change file permissions"),
    r"\bchown\s+": ("Chown", "change file ownership"),
    r"\bfind\s+": ("Find", "search for files"),
    r"\bgrep\s+": ("Grep", "search text patterns"),
    r"\btar\s+": ("Tar", "archive management"),
    r"\bgit\s+": ("Git", "version control"),
    r"\bwget\s+": ("Wget", "download files"),
    r"\bcurl\s+": ("Curl", "transfer data"),
    r"\bping\s+": ("Ping", "network connectivity test"),
    r"\bssh\s+": ("Ssh", "secure shell client"),
    r"\breboot\b": ("Reboot", "system reboot"),
    r"\bsystemctl\s+": ("Service", "systemd service management"),
    r"\bservice\s+": ("Service", "service management"),
    r"\buname\s+": ("Uname", "system information"),
    r"\blscpu\b": ("Lscpu", "CPU information"),
    r"\blspci\b": ("Lspci", "PCI device information"),
    r"\blsblk\b": ("Lsblk", "block device information"),
    r"\blsmod\b": ("Lsmod", "list loaded kernel modules"),
    r"\bmodprobe\s+": ("Modprobe", "kernel module management"),
    r"\bdmesg\b": ("Dmesg", "kernel ring buffer"),
    r"\bmount\s+": ("Mount", "mount filesystems"),
    r"\bumount\s+": ("Mount", "unmount filesystems"),
    r"\bdf\s+": ("Df", "disk space usage"),
    r"\bfdisk\s+": ("Fdisk", "partition table management"),
    r"\bparted\s+": ("Parted", "partition editor"),
    r"\bmkfs\s+": ("Mkfs", "create filesystem"),
    r"\bblkid\b": ("Blkid", "block device attributes"),
    r"\bfree\b": ("Free", "memory usage"),
    r"\bdate\s+": ("Date", "date and time"),
    r"\bhostname\b": ("Hostname", "system hostname"),
    r"\bwhoami\b": ("Whoami", "current user"),
    r"\bkill\s+": ("Kill", "terminate processes"),
    r"\bpgrep\s+": ("Pgrep", "find processes by name"),
    r"\bstat\s+": ("Stat", "file/filesystem statistics"),
    r"\bethtool\s+": ("Ethtool", "network device settings"),
    r"\biperf3\s+": ("Iperf3", "network performance testing"),
    r"\bntttcp\s+": ("Ntttcp", "network throughput testing"),
    r"\bfio\s+": ("Fio", "I/O workload simulation"),
    r"\bstress-ng\s+": ("StressNg", "stress testing"),
    r"\bjournalctl\s+": ("Journalctl", "systemd journal"),
    r"\bsysctl\s+": ("Sysctl", "kernel parameters"),
    r"\bdocker\s+": ("Docker", "container management"),
    r"\bmake\s+": ("Make", "build automation"),
    r"\bgcc\s+": ("Gcc", "GNU C compiler"),
    r"\bpython\s+": ("Python", "Python interpreter"),
    r"\bpython3\s+": ("Python", "Python 3 interpreter"),
    r"\bpip\s+": ("Pip", "Python package manager"),
    r"\bpip3\s+": ("Pip", "Python 3 package manager"),
}


class NodeExecuteChecker(ast.NodeVisitor):
    """AST visitor to find node.execute() calls in test methods."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Tuple[int, str, str, str, str]] = []
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
        """Check if this is a test method."""
        old_method = self.current_method
        old_in_test = self.in_test_method

        self.current_method = node.name

        # Check if this is a test method
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
        """Check for node.execute() or node.execute_async() calls."""
        if self.in_test_method and isinstance(node.func, ast.Attribute):
            # Check for node.execute() or node.execute_async()
            if node.func.attr in ["execute", "execute_async"] and isinstance(
                node.func.value, ast.Name
            ):
                # Get the command being executed (first argument)
                if node.args:
                    command = self._extract_command(node.args[0])
                    if command:
                        tool_info = self._find_matching_tool(command)
                        if tool_info:
                            tool_class, tool_desc = tool_info
                            context = (
                                f"{self.current_class}.{self.current_method}"
                                if self.current_class
                                else self.current_method
                            )
                            self.violations.append(
                                (
                                    node.lineno,
                                    context or "unknown",
                                    command[:80],  # Truncate long commands
                                    tool_class,
                                    tool_desc,
                                )
                            )

        self.generic_visit(node)

    def _extract_command(self, node: ast.AST) -> str:
        """Extract command string from AST node."""
        if isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.JoinedStr):
            # f-string - try to extract static parts
            parts = []
            for value in node.values:
                if isinstance(value, ast.Constant):
                    parts.append(str(value.value))
                else:
                    parts.append("{...}")
            return "".join(parts)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
            # String concatenation or formatting
            left = self._extract_command(node.left)
            right = self._extract_command(node.right)
            if left and right:
                return f"{left} {right}"
            return left or right
        elif isinstance(node, ast.Call):
            # Method call like .format()
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "format":
                    base = self._extract_command(node.func.value)
                    return base if base else ""
        return ""

    def _find_matching_tool(self, command: str) -> tuple[str, str] | None:
        """Find if command matches a known tool pattern."""
        for pattern, tool_info in COMMAND_TO_TOOL.items():
            if re.search(pattern, command, re.IGNORECASE):
                return tool_info
        return None


def check_file(filepath: Path) -> List[Tuple[int, str, str, str, str]]:
    """Check a single Python file for node.execute() usage."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))

        checker = NodeExecuteChecker(str(filepath))
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
        print("Usage: check_tool_usage.py <file1.py> [file2.py ...]")
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
                [
                    (filepath, line, context, cmd, tool, desc)
                    for line, context, cmd, tool, desc in violations
                ]
            )

    if all_violations:
        print("\n❌ Found node.execute() usage when tool wrappers exist:\n")
        for filepath, line, context, cmd, tool_class, tool_desc in all_violations:
            print(f"  {filepath}:{line} in {context}")
            print(f"    Command: {cmd}")
            print(f"    → Use node.tools[{tool_class}] instead ({tool_desc})")
            print()

        print("=" * 70)
        print("Tests should use tool wrappers instead of raw node.execute().")
        print("\nWhy use tool wrappers:")
        print("  • Better abstraction and maintainability")
        print("  • Consistent error handling and logging")
        print("  • Type safety and IDE auto-completion")
        print("  • Easier testing and mocking")
        print("  • Built-in installation and capability checks")
        print("\nExample conversion:")
        print("  ❌ result = node.execute('ip addr show')")
        print("  ✅ ip = node.tools[Ip]")
        print("     result = ip.run('addr show')")
        print("\nFor more info, see:")
        print("  • lisa/tools/ - Available tool wrappers")
        print(
            "  • docs/write_test/write_case.rst - Tool usage guidelines"  # noqa: E501
        )
        print("=" * 70)
        sys.exit(1)
    else:
        print("✅ No inappropriate node.execute() usage found")
        sys.exit(0)


if __name__ == "__main__":
    main()
