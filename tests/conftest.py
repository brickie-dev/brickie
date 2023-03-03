def pytest_addoption(parser):
    parser.addoption(
        '--test-client',
        action='store_true',
        dest='test_client',
        default=False,
        help='Enable client tests')

    parser.addoption(
        '--cache-dir',
        action='store',
        dest='cache_dir',
        default='.pytest_cache/build',
        help='Test build cache directory')

    parser.addoption(
        '--no-cache',
        action='store_true',
        dest='no_cache',
        default=False,
        help='Enable/disable build cache')
