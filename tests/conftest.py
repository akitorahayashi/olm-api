def pytest_addoption(parser):
    """Add a command line option to pytest to run database-dependent tests."""
    parser.addoption(
        "--db",
        action="store_true",
        default=False,
        help="run database-dependent tests",
    )
