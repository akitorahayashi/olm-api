"""
Common fixtures for SDK tests.
This file contains fixtures shared across SDK test modules.
"""

import ast
import os
from pathlib import Path
from typing import List, Set

import pytest
from olm_api_sdk.v1.mock_client import MockOlmClientV1
from olm_api_sdk.v2.mock_client import MockOlmClientV2

# =============================================================================
# File System Fixtures
# =============================================================================


def get_python_files(root_path: str) -> List[Path]:
    """Get all Python files in the project, excluding certain directories."""
    python_files = []
    exclude_dirs = {
        "__pycache__",
        ".venv",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        ".git",
    }

    for root, dirs, files in os.walk(root_path):
        # Remove excluded directories from dirs to prevent walking into them
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    return python_files


@pytest.fixture(scope="class")
def python_files() -> List[Path]:
    """Get all Python files in the project."""
    project_root = Path(__file__).parent.parent.parent
    return get_python_files(str(project_root))


# =============================================================================
# Mock Client Fixtures
# =============================================================================


@pytest.fixture
def mock_client_v1():
    """
    Provides a MockOlmClientV1 with zero delay and predictable responses for fast testing.
    """
    predictable_responses = [
        "Test response 1",
        "Test response 2",
        "Test response 3",
        "Test response 4",
        "Test response 5",
    ]
    return MockOlmClientV1(token_delay=0, responses=predictable_responses)


@pytest.fixture
def slow_mock_client_v1():
    """
    Provides a MockOlmClientV1 with realistic delay and predictable responses for testing streaming behavior.
    """
    predictable_responses = [
        "Slow test response 1",
        "Slow test response 2",
        "Slow test response 3",
    ]
    return MockOlmClientV1(token_delay=0.01, responses=predictable_responses)


@pytest.fixture
def fast_mock_client_v1():
    """
    Provides a fast MockOlmClientV1 with zero delay for unit testing.
    """
    return MockOlmClientV1(token_delay=0)


@pytest.fixture
def custom_response_client_v1():
    """
    Provides a MockOlmClientV1 with custom responses for specific test scenarios.
    """

    def _create_client(responses):
        return MockOlmClientV1(token_delay=0, responses=responses)

    return _create_client


@pytest.fixture
def mock_client_v2():
    """
    Provides a MockOlmClientV2 with zero delay and predictable responses for fast testing.
    """
    predictable_responses = [
        "Test response 1",
        "Test response 2",
        "Test response 3",
        "Test response 4",
        "Test response 5",
    ]
    return MockOlmClientV2(token_delay=0, responses=predictable_responses)


@pytest.fixture
def slow_mock_client_v2():
    """
    Provides a MockOlmClientV2 with realistic delay and predictable responses for testing streaming behavior.
    """
    predictable_responses = [
        "Slow test response 1",
        "Slow test response 2",
        "Slow test response 3",
    ]
    return MockOlmClientV2(token_delay=0.01, responses=predictable_responses)


@pytest.fixture
def fast_mock_client_v2():
    """
    Provides a fast MockOlmClientV2 with zero delay for unit testing.
    """
    return MockOlmClientV2(token_delay=0)


@pytest.fixture
def custom_response_client_v2():
    """
    Provides a MockOlmClientV2 with custom responses for specific test scenarios.
    """

    def _create_client(responses):
        return MockOlmClientV2(token_delay=0, responses=responses)

    return _create_client


# =============================================================================
# Import Validation Fixtures
# =============================================================================


def extract_imports(file_path: Path) -> Set[str]:
    """Extract all import statements from a Python file."""
    imports = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
    except Exception:
        # If we can't parse the file, skip it
        pass

    return imports


@pytest.fixture
def extract_imports_fixture():
    """Fixture to provide the extract_imports function for tests."""
    return extract_imports
