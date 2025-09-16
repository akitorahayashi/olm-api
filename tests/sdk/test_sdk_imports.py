"""
Test for import validation in the codebase.
This test ensures that all Python files have valid imports and no circular dependencies.
"""

import ast
from pathlib import Path
from typing import List

import pytest


def check_circular_imports(python_files: List[Path], extract_imports_func) -> List[str]:
    """Check for potential circular imports."""
    errors = []
    file_imports = {}

    # Build a map of file to its imports
    for file_path in python_files:
        file_imports[file_path] = extract_imports_func(file_path)

    # Simple circular import detection (this is a basic check)
    for file_path, imports in file_imports.items():
        module_name = file_path.stem
        for imported in imports:
            # Check if any imported module might be importing this module
            for other_file, other_imports in file_imports.items():
                if other_file != file_path and other_file.stem == imported:
                    # Check if the other file imports this module
                    if module_name in [imp.split(".")[0] for imp in other_imports]:
                        errors.append(
                            f"Potential circular import between {file_path} and {other_file}"
                        )

    return errors


class TestImportValidation:
    """Test class for import validation."""

    def test_imports_parseable(self, python_files: List[Path]):
        """Test that all Python files can be parsed (implicit syntax check)."""
        unparseable_files = []

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()
                ast.parse(source, filename=str(file_path))
            except (SyntaxError, UnicodeDecodeError, Exception) as e:
                unparseable_files.append(f"{file_path}: {e}")

        if unparseable_files:
            error_message = "\n".join(unparseable_files)
            pytest.fail(f"Unparseable files found:\n{error_message}")

    def test_no_circular_imports(
        self, python_files: List[Path], extract_imports_fixture
    ):
        """Test for circular imports."""
        errors = check_circular_imports(python_files, extract_imports_fixture)

        if errors:
            error_message = "\n".join(errors)
            pytest.fail(f"Circular import issues found:\n{error_message}")

    def test_all_files_found(self, python_files: List[Path]):
        """Test that we found some Python files to check."""
        assert len(python_files) > 0, "No Python files found in the project"

    def test_file_paths_valid(self, python_files: List[Path]):
        """Test that all file paths are valid and exist."""
        for file_path in python_files:
            assert file_path.exists(), f"File does not exist: {file_path}"
            assert file_path.is_file(), f"Path is not a file: {file_path}"
