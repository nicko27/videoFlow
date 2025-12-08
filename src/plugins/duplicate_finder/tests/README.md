# Duplicate Finder Test Suite

This directory contains comprehensive tests for the Duplicate Finder plugin.

## Test Structure

### Unit Tests (`test_core_managers.py`)
Tests for core manager components:
- **UnifiedConfigManager**: Configuration management
- **PipelineManager**: Verification pipeline management
- **TestSetManager**: Test set CRUD operations
- **BenchmarkManager**: Benchmark execution and results
- **ProgressManager**: Progress widget coordination
- **WidgetRegistry**: Widget registration and retrieval

### Integration Tests (TODO)
- Full analysis workflow
- Benchmark workflow
- Settings persistence
- Import/export functionality

### Functional Tests (`test_functional.py`)
End-to-end functionality tests.

## Running Tests

### Run all tests:
```bash
cd /Users/nico/Documents/videoFlow
python3 -m pytest src/plugins/duplicate_finder/tests/ -v
```

### Run specific test file:
```bash
python3 -m pytest src/plugins/duplicate_finder/tests/test_core_managers.py -v
```

### Run with coverage:
```bash
python3 -m pytest src/plugins/duplicate_finder/tests/ --cov=src/plugins/duplicate_finder --cov-report=html
```

## Test Coverage Goals

- **Unit Tests**: 80%+ coverage for managers and core components
- **Integration Tests**: All major workflows covered
- **Functional Tests**: Key user scenarios validated

## Notes

- Tests use pytest framework
- Mock objects used for Qt widgets to avoid GUI dependencies
- Database tests use in-memory SQLite databases
- File system tests use temporary directories

## Future Improvements

1. Add integration tests for complete workflows
2. Add performance benchmarks
3. Add regression tests for known bugs
4. Add GUI interaction tests using pytest-qt
5. Increase code coverage to 90%+
