import os
import sys

import pytest

# Add the project root directory to the Python path
# This allows pytest to find the 'src' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """
    Set environment variables required for the tests before any modules are imported.
    This runs once per test session and is available to all tests.
    """
    os.environ["OLLAMA_MODEL"] = "test-model"
    # We can also set a test database URL if needed
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
