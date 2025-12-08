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

### Integration Tests (`test_integration.py`)
Tests for complete end-to-end workflows:
- **TestAnalysisWorkflow**: Full analysis workflow with different configurations
  - Complete analysis from configuration to results storage
  - Audio fingerprinting integration
  - LSH optimization integration
- **TestBenchmarkWorkflow**: Benchmark creation and execution
  - Test set creation and management
  - Pipeline creation for benchmarks
  - Benchmark results storage
- **TestSettingsPersistence**: Settings save/load functionality
  - Settings persistence across sessions
  - Default value handling
  - UnifiedConfigManager integration
- **TestImportExport**: Import/export functionality
  - Pipeline export/import via JSON
  - Test set export/import
  - Settings export/import
- **TestEndToEndWorkflows**: Complete user workflows
  - Full benchmark workflow (configure -> test set -> pipeline -> benchmark)
  - Settings and pipeline integration

### Functional Tests (`test_functional.py`)
End-to-end functionality tests (TODO).

## Running Tests

### Run all tests:
```bash
cd /Users/nico/Documents/videoFlow
python3 -m pytest src/plugins/duplicate_finder/tests/ -v
```

### Run specific test file:
```bash
# Unit tests only
python3 -m pytest src/plugins/duplicate_finder/tests/test_core_managers.py -v

# Integration tests only
python3 -m pytest src/plugins/duplicate_finder/tests/test_integration.py -v
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

1. ✅ ~~Add integration tests for complete workflows~~ (COMPLETED)
2. Add performance benchmarks
3. Add regression tests for known bugs
4. Add GUI interaction tests using pytest-qt
5. Increase code coverage to 90%+
6. Resolve module import issues for test execution
