#!/usr/bin/env python3
"""
Docstring Coverage Checker for VideoFlow

This script checks Python files for missing docstrings.
"""

import ast
from pathlib import Path
from typing import List, Tuple


class DocstringChecker(ast.NodeVisitor):
    """AST visitor to check for missing docstrings."""

    def __init__(self):
        """Initialize checker."""
        self.missing = {
            'modules': [],
            'classes': [],
            'functions': [],
            'methods': []
        }
        self.total = {
            'modules': 0,
            'classes': 0,
            'functions': 0,
            'methods': 0
        }
        self.current_class = None

    def visit_Module(self, node):
        """Visit module node."""
        self.total['modules'] += 1
        if not ast.get_docstring(node):
            self.missing['modules'].append('Module')
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Visit class definition node."""
        self.total['classes'] += 1
        if not ast.get_docstring(node):
            self.missing['classes'].append(node.name)

        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Visit function definition node."""
        # Skip private functions starting with _
        if node.name.startswith('_') and node.name != '__init__':
            return

        if self.current_class:
            self.total['methods'] += 1
            if not ast.get_docstring(node):
                self.missing['methods'].append(f"{self.current_class}.{node.name}")
        else:
            self.total['functions'] += 1
            if not ast.get_docstring(node):
                self.missing['functions'].append(node.name)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Visit async function definition node."""
        self.visit_FunctionDef(node)


def check_file(file_path: Path) -> Tuple[DocstringChecker, bool]:
    """
    Check a Python file for missing docstrings.

    Args:
        file_path: Path to Python file

    Returns:
        Tuple of (checker, success)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        checker = DocstringChecker()
        checker.visit(tree)
        return checker, True

    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return None, False
    except Exception as e:
        print(f"Error checking {file_path}: {e}")
        return None, False


def calculate_coverage(checker: DocstringChecker) -> float:
    """
    Calculate docstring coverage percentage.

    Args:
        checker: DocstringChecker instance

    Returns:
        Coverage percentage (0-100)
    """
    total_items = sum(checker.total.values())
    missing_items = sum(len(v) for v in checker.missing.values())

    if total_items == 0:
        return 100.0

    return ((total_items - missing_items) / total_items) * 100.0


def main():
    """Main function."""
    print("VideoFlow - Docstring Coverage Check")
    print("=" * 70)

    src_dir = Path("src")
    if not src_dir.exists():
        print(f"Error: {src_dir} not found")
        return

    # Find all Python files
    python_files = list(src_dir.rglob("*.py"))
    print(f"Checking {len(python_files)} Python files\n")

    total_coverage = 0.0
    files_with_issues = []

    all_totals = {'modules': 0, 'classes': 0, 'functions': 0, 'methods': 0}
    all_missing = {'modules': [], 'classes': [], 'functions': [], 'methods': []}

    # Check each file
    for file_path in sorted(python_files):
        checker, success = check_file(file_path)

        if not success:
            continue

        # Aggregate statistics
        for key in all_totals:
            all_totals[key] += checker.total[key]
            all_missing[key].extend(checker.missing[key])

        coverage = calculate_coverage(checker)
        total_coverage += coverage

        if coverage < 100.0:
            relative_path = file_path.relative_to(src_dir)
            missing_count = sum(len(v) for v in checker.missing.values())
            total_count = sum(checker.total.values())
            files_with_issues.append((relative_path, coverage, missing_count, total_count))

    # Calculate overall statistics
    overall_coverage = total_coverage / len(python_files) if python_files else 0
    total_items = sum(all_totals.values())
    missing_items = sum(len(v) for v in all_missing.values())

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nOverall Statistics:")
    print(f"  Total modules:   {all_totals['modules']:4d}")
    print(f"  Total classes:   {all_totals['classes']:4d}")
    print(f"  Total functions: {all_totals['functions']:4d}")
    print(f"  Total methods:   {all_totals['methods']:4d}")
    print(f"  Total items:     {total_items:4d}")
    print()
    print(f"  Missing module docstrings:   {len(all_missing['modules']):4d}")
    print(f"  Missing class docstrings:    {len(all_missing['classes']):4d}")
    print(f"  Missing function docstrings: {len(all_missing['functions']):4d}")
    print(f"  Missing method docstrings:   {len(all_missing['methods']):4d}")
    print(f"  Total missing:               {missing_items:4d}")
    print()
    print(f"  Overall Coverage: {((total_items - missing_items) / total_items * 100):.1f}%")
    print()

    if files_with_issues:
        print(f"\nFiles with Missing Docstrings ({len(files_with_issues)} files):")
        print("-" * 70)
        for path, cov, missing, total in sorted(files_with_issues, key=lambda x: x[1]):
            print(f"  {str(path):50s} {cov:5.1f}% ({total-missing}/{total})")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
