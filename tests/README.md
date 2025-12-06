# VideoFlow Test Suite

This directory contains the test suite for the VideoFlow application.

## Structure

```
tests/
├── conftest.py                           # Shared fixtures and configuration
├── test_plugins/
│   └── test_duplicate_finder/
│       ├── test_database_manager.py      # Database operations tests
│       ├── test_video_hasher.py          # Video hashing tests
│       └── test_error_handling.py        # Error handling tests
└── README.md                             # This file
```

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install pytest pytest-cov pytest-mock
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run tests without coverage
pytest --no-cov

# Run tests verbosely
pytest -vv
```

### Run Specific Tests

```bash
# Run tests for a specific module
pytest tests/test_plugins/test_duplicate_finder/test_database_manager.py

# Run tests for a specific class
pytest tests/test_plugins/test_duplicate_finder/test_database_manager.py::TestDatabaseManagerInit

# Run a specific test
pytest tests/test_plugins/test_duplicate_finder/test_database_manager.py::TestDatabaseManagerInit::test_creates_database_file

# Run tests matching a pattern
pytest -k "cache"
pytest -k "test_hash"
```

### Run Tests by Marker

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run database tests only
pytest -m database
```

## Test Coverage

### Generate Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=src/plugins/duplicate_finder --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Generate terminal coverage report
pytest --cov=src/plugins/duplicate_finder --cov-report=term-missing

# Generate both
pytest --cov=src/plugins/duplicate_finder --cov-report=html --cov-report=term
```

### Coverage Goals

- **Core algorithms**: 90%+ coverage
- **UI code**: 60%+ coverage
- **Overall**: 75%+ coverage

Current coverage (2025-12-06): **~50%** baseline established

## Writing Tests

### Test File Naming

- Test files: `test_<module_name>.py`
- Test classes: `Test<FeatureName>`
- Test functions: `test_<what_it_tests>`

### Example Test

```python
import pytest
from src.plugins.duplicate_finder.video_hasher import VideoHasher

class TestVideoHasher:
    """Test video hashing functionality."""

    def test_compute_hash_returns_valid_hash(self, mock_database):
        """Test that compute_hash returns a valid perceptual hash."""
        hasher = VideoHasher(mock_database)

        hash_result, duration = hasher.compute_video_hash_fast("/tmp/test.mp4")

        assert hash_result is not None
        assert isinstance(hash_result, np.ndarray)
        assert duration > 0
```

### Using Fixtures

Common fixtures available from `conftest.py`:

```python
def test_with_fixtures(temp_dir, mock_database, sample_hash):
    """Example using shared fixtures."""
    # temp_dir: Temporary directory (Path object)
    # mock_database: Mock DatabaseManager instance
    # sample_hash: Sample perceptual hash (numpy array)

    test_file = temp_dir / "test.txt"
    test_file.write_text("test data")

    assert test_file.exists()
```

### Mocking

Use `unittest.mock` or `pytest-mock`:

```python
from unittest.mock import patch, Mock

def test_with_mocking(mock_database):
    """Example using mocks."""
    with patch('cv2.VideoCapture') as mock_cv2:
        mock_cv2.return_value.isOpened.return_value = True
        mock_cv2.return_value.read.return_value = (True, frame_data)

        # Test code here
```

### Parametrized Tests

Test multiple cases efficiently:

```python
@pytest.mark.parametrize("similarity,expected", [
    (1.0, "identical"),
    (0.9, "similar"),
    (0.5, "different"),
    (0.0, "completely_different"),
])
def test_similarity_classification(similarity, expected):
    """Test similarity classification logic."""
    result = classify_similarity(similarity)
    assert result == expected
```

## Test Categories

### Unit Tests (Fast)

- Test individual functions/methods in isolation
- Use mocks for external dependencies
- Should run in < 1 second total
- Mark with `@pytest.mark.unit`

### Integration Tests

- Test multiple components together
- May access filesystem, database
- Slower than unit tests
- Mark with `@pytest.mark.integration`

### Slow Tests

- Tests that take > 1 second
- Mark with `@pytest.mark.slow`
- Skip in CI: `pytest -m "not slow"`

## Continuous Integration

### Pre-commit Hook

Run tests before committing:

```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
pytest -m "not slow" --tb=short
```

### GitHub Actions

Example workflow (`.github/workflows/test.yml`):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`:

```bash
# Make sure you're in the project root
cd /path/to/videoFlow

# Run pytest (it automatically adds src to path via conftest.py)
pytest
```

### Database Lock Errors

If tests fail with "database is locked":

```bash
# Clean up test databases
rm -rf /tmp/test_*.db
```

### Fixture Not Found

If you see `fixture 'X' not found`:

- Check that `conftest.py` defines the fixture
- Make sure `conftest.py` is in the correct directory
- Fixtures are scoped to their directory and subdirectories

### Slow Tests

If tests are taking too long:

```bash
# Run with pytest-xdist for parallel execution
pip install pytest-xdist
pytest -n auto  # Use all CPU cores
```

## Next Steps

### Planned Test Additions

1. **Audio Fingerprinting Tests** (`test_audio_fingerprinting.py`)
   - Test MFCC extraction
   - Test fingerprint comparison
   - Test subsequence detection

2. **Strategy 3 Verification Tests** (`test_subsequence_verification.py`)
   - Test scene detection
   - Test DCT similarity
   - Test sequence consistency

3. **LSH Indexing Tests** (`test_lsh_audio.py`)
   - Test MinHash generation
   - Test LSH candidate finding
   - Test multi-resolution comparison

4. **Worker Tests** (`test_workers/`)
   - Test parallel hashing
   - Test comparison workers
   - Test graceful cancellation

5. **UI Tests** (`test_ui/`)
   - Test main window initialization
   - Test file selection
   - Test progress updates

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Aim for > 80% coverage for new code
3. Use descriptive test names
4. Add docstrings to test classes
5. Mark tests with appropriate markers
6. Keep tests fast (use mocks)

---

**Last Updated**: 2025-12-06
**Test Count**: 47 tests (3 test files)
**Coverage**: ~50% baseline
