# Contributing to Duplicate Finder

Thank you for your interest in contributing to Duplicate Finder! This document provides guidelines and instructions for contributing to the project.

## Table of Contents
1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Development Workflow](#development-workflow)
5. [Coding Standards](#coding-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation](#documentation)
8. [Submitting Changes](#submitting-changes)
9. [Code Review Process](#code-review-process)
10. [Release Process](#release-process)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of:
- Experience level
- Gender identity and expression
- Sexual orientation
- Disability
- Personal appearance
- Body size
- Race
- Ethnicity
- Age
- Religion
- Nationality

### Our Standards

**Examples of encouraged behavior:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Examples of unacceptable behavior:**
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

---

## Getting Started

### Finding Issues to Work On

1. **Good First Issues**: Look for issues labeled `good-first-issue`
2. **Help Wanted**: Issues labeled `help-wanted` need community support
3. **Bugs**: Issues labeled `bug` are confirmed bugs
4. **Features**: Issues labeled `enhancement` are feature requests

### Before You Start

1. **Check Existing Issues**: Search for existing issues/PRs
2. **Discuss Major Changes**: Open an issue first for significant changes
3. **Read Documentation**: Review ARCHITECTURE.md and API_REFERENCE.md
4. **Understand the Codebase**: Explore the code structure

---

## Development Setup

### Prerequisites

**Required:**
- Python 3.8 or higher
- pip (Python package manager)
- git

**Optional (for full features):**
- FFmpeg (video processing)
- Chromaprint/fpcalc (audio fingerprinting)
- PySceneDetect (scene detection)

### Setup Steps

1. **Fork the Repository**
   ```bash
   # Click "Fork" on GitHub
   ```

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/videoFlow.git
   cd videoFlow/src/plugins/duplicate_finder
   ```

3. **Set Upstream Remote**
   ```bash
   git remote add upstream https://github.com/ORIGINAL_REPO/videoFlow.git
   ```

4. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

5. **Install Dependencies**
   ```bash
   # Core dependencies
   pip install -r requirements.txt

   # Development dependencies
   pip install -r requirements-dev.txt

   # Optional dependencies
   pip install -r requirements-optional.txt
   ```

6. **Verify Installation**
   ```bash
   python3 -m pytest tests/ -v
   ```

### IDE Setup

**Recommended IDEs:**
- **VS Code** with Python extension
- **PyCharm** (Community or Professional)
- **Sublime Text** with Python package

**VS Code Settings:**
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true
}
```

---

## Development Workflow

### Branch Strategy

We use **Git Flow**:

- `main`: Stable releases
- `develop`: Development branch
- `feature/*`: New features
- `bugfix/*`: Bug fixes
- `hotfix/*`: Urgent fixes
- `release/*`: Release preparation

### Creating a Feature Branch

```bash
# Update develop
git checkout develop
git pull upstream develop

# Create feature branch
git checkout -b feature/my-new-feature

# Work on your feature
# ... make changes ...

# Commit changes
git add .
git commit -m "Add my new feature"

# Push to your fork
git push origin feature/my-new-feature
```

### Keeping Your Branch Updated

```bash
# Fetch latest changes
git fetch upstream

# Rebase on develop
git checkout feature/my-new-feature
git rebase upstream/develop

# Resolve conflicts if any
# ... fix conflicts ...
git add .
git rebase --continue

# Force push (your feature branch only!)
git push origin feature/my-new-feature --force-with-lease
```

---

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

**Line Length:**
- Maximum 100 characters (not 79)
- Maximum 120 for comments/docstrings

**Imports:**
```python
# Standard library
import os
import sys
from pathlib import Path

# Third-party
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

# Local
from managers.settings_manager import SettingsManager
from analysis.hash_methods import compute_phash
```

**Naming Conventions:**
```python
# Classes: PascalCase
class VideoAnalyzer:
    pass

# Functions/methods: snake_case
def compute_hash(video_path):
    pass

# Constants: UPPER_SNAKE_CASE
MAX_WORKERS = 8
DEFAULT_THRESHOLD = 85

# Private members: _leading_underscore
class MyClass:
    def __init__(self):
        self._private_var = 10

    def _private_method(self):
        pass
```

**Type Hints:**
```python
from typing import List, Dict, Optional

def process_videos(
    video_paths: List[str],
    threshold: int = 85,
    workers: Optional[int] = None
) -> Dict[str, float]:
    """
    Process videos and return hash values.

    Args:
        video_paths: List of paths to video files
        threshold: Similarity threshold (0-100)
        workers: Number of worker threads (None = auto)

    Returns:
        Dictionary mapping video paths to hash values
    """
    pass
```

### Code Formatting

**Use Black formatter:**
```bash
# Format all files
black src/plugins/duplicate_finder/

# Check formatting
black --check src/plugins/duplicate_finder/
```

**Configuration** (pyproject.toml):
```toml
[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310']
```

### Linting

**Use flake8:**
```bash
# Run linter
flake8 src/plugins/duplicate_finder/

# With custom config
flake8 --config=.flake8 src/plugins/duplicate_finder/
```

**Configuration** (.flake8):
```ini
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv,build
ignore = E203, W503
```

### Docstrings

**Use Google Style:**
```python
def complex_function(param1: str, param2: int, param3: bool = False) -> Dict[str, Any]:
    """
    One-line summary of function.

    More detailed description if needed. Can span multiple lines.
    Explain what the function does, not how it does it.

    Args:
        param1: Description of param1
        param2: Description of param2
        param3: Description of param3. Defaults to False.

    Returns:
        Dictionary containing:
            - key1: Description of value
            - key2: Description of value

    Raises:
        ValueError: If param2 is negative
        IOError: If file cannot be read

    Example:
        >>> result = complex_function("test", 42, True)
        >>> print(result['key1'])
        'value1'

    Note:
        Any additional notes or warnings
    """
    pass
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── __init__.py
├── test_core_managers.py      # Unit tests
├── test_integration.py         # Integration tests
├── test_functional.py          # Functional tests (TODO)
└── README.md
```

### Writing Unit Tests

**Template:**
```python
import pytest
from managers.settings_manager import SettingsManager

class TestSettingsManager:
    """Test suite for SettingsManager."""

    @pytest.fixture
    def settings_manager(self):
        """Create a settings manager instance."""
        return SettingsManager()

    def test_set_and_get(self, settings_manager):
        """Test setting and getting a value."""
        settings_manager.set('test_key', 'test_value')
        assert settings_manager.get('test_key') == 'test_value'

    def test_default_value(self, settings_manager):
        """Test getting with default value."""
        value = settings_manager.get('nonexistent', default='default')
        assert value == 'default'

    def test_invalid_key(self, settings_manager):
        """Test handling of invalid key."""
        with pytest.raises(ValueError):
            settings_manager.set('', 'value')
```

### Writing Integration Tests

**Template:**
```python
import pytest
import tempfile
from pathlib import Path
from database_manager import DatabaseManager
from managers.settings_manager import SettingsManager

class TestAnalysisWorkflow:
    """Integration tests for analysis workflow."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def db_manager(self, temp_dir):
        """Create database manager with temp database."""
        db_path = Path(temp_dir) / "test.db"
        return DatabaseManager(str(db_path))

    def test_full_workflow(self, temp_dir, db_manager):
        """Test complete analysis workflow."""
        # Setup
        settings = SettingsManager()
        settings.set('video_threshold', 85)

        # Execute workflow
        # ... perform analysis ...

        # Verify results
        duplicates = db_manager.get_duplicates(threshold=85)
        assert len(duplicates) > 0
```

### Test Coverage

**Run with coverage:**
```bash
# Run tests with coverage
pytest --cov=src/plugins/duplicate_finder --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Coverage Goals:**
- **Unit Tests**: 80%+ coverage for managers and core components
- **Integration Tests**: All major workflows covered
- **Critical Paths**: 100% coverage for security/data integrity code

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_core_managers.py -v

# Run specific test class
pytest tests/test_core_managers.py::TestSettingsManager -v

# Run specific test method
pytest tests/test_core_managers.py::TestSettingsManager::test_set_and_get -v

# Run with markers
pytest -m "not slow" -v  # Skip slow tests

# Run with output
pytest -v -s  # Show print statements
```

---

## Documentation

### Code Comments

**When to comment:**
- ✅ Complex algorithms
- ✅ Non-obvious optimizations
- ✅ Workarounds for bugs
- ✅ Important architectural decisions
- ❌ Obvious code (let code speak for itself)

**Example:**
```python
# Good comment: explains WHY
# Use LSH to reduce comparison from O(n²) to O(n) for large datasets
lsh_index = LSHIndex(bands=20, rows=5)

# Bad comment: explains WHAT (code is self-explanatory)
# Set threshold to 85
threshold = 85
```

### Docstring Coverage

**Required docstrings:**
- ✅ All public classes
- ✅ All public methods/functions
- ✅ All modules (\__init__.py)
- ❌ Private methods (optional but encouraged)
- ❌ Test methods (optional)

### Documentation Files

**Update when changing:**
- **USER_GUIDE.md**: User-facing features
- **FAQ.md**: New common questions
- **TROUBLESHOOTING.md**: New issues and solutions
- **ARCHITECTURE.md**: Architectural changes
- **API_REFERENCE.md**: API changes
- **CONTRIBUTING.md**: Development process changes

---

## Submitting Changes

### Pull Request Checklist

Before submitting, ensure:

- [ ] Code follows style guidelines (Black + flake8)
- [ ] All tests pass (`pytest tests/`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (if needed)
- [ ] Commit messages are clear and descriptive
- [ ] Branch is up to date with `develop`
- [ ] No merge conflicts
- [ ] PR description is complete

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Related Issue
Fixes #123

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
Describe testing performed:
- Unit tests added/updated
- Integration tests added/updated
- Manual testing performed

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] No new warnings
```

### Commit Message Guidelines

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Adding/updating tests
- `chore`: Build process, dependencies, etc.

**Examples:**
```
feat(analysis): add wHash hash method support

Implement Wavelet Hash (wHash) for better detection of cropped and
rotated videos. This hash method is more robust to transformations
than pHash.

Closes #42

---

fix(database): prevent duplicate entry errors

Add UNIQUE constraint to video_hashes table and handle conflicts
gracefully with INSERT OR REPLACE.

Fixes #55

---

docs(user-guide): add multi-resolution configuration example

Add step-by-step example for configuring multi-resolution analysis
in the USER_GUIDE.md.
```

---

## Code Review Process

### For Contributors

**After submitting PR:**
1. Wait for automated checks (CI/CD)
2. Address any failing checks
3. Respond to reviewer comments
4. Make requested changes
5. Request re-review when ready

**Responding to feedback:**
- Be respectful and professional
- Ask questions if feedback is unclear
- Explain your reasoning if you disagree
- Make changes promptly
- Thank reviewers for their time

### For Reviewers

**What to review:**
- [ ] Code correctness
- [ ] Test coverage
- [ ] Documentation completeness
- [ ] Performance implications
- [ ] Security considerations
- [ ] Code style compliance
- [ ] Architectural fit

**Review tone:**
- Be constructive and specific
- Suggest improvements, don't just criticize
- Acknowledge good work
- Ask questions rather than making demands
- Provide examples when possible

**Approval criteria:**
- All checklist items satisfied
- No unresolved comments
- CI/CD passes
- At least one approving review

---

## Release Process

### Version Numbering

We use **Semantic Versioning** (SemVer):

```
MAJOR.MINOR.PATCH

Example: 3.1.2
```

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. **Update Version Number**
   ```python
   # __init__.py
   __version__ = '3.1.0'
   ```

2. **Update CHANGELOG.md**
   ```markdown
   ## [3.1.0] - 2025-12-08

   ### Added
   - New feature 1
   - New feature 2

   ### Fixed
   - Bug fix 1
   - Bug fix 2

   ### Changed
   - Breaking change 1
   ```

3. **Run Full Test Suite**
   ```bash
   pytest tests/ -v
   pytest --cov=src/plugins/duplicate_finder
   ```

4. **Update Documentation**
   - Version numbers in docs
   - New features documented
   - Breaking changes highlighted

5. **Create Release Branch**
   ```bash
   git checkout develop
   git checkout -b release/3.1.0
   ```

6. **Final Testing**
   - Manual testing
   - User acceptance testing
   - Performance testing

7. **Merge to Main**
   ```bash
   git checkout main
   git merge release/3.1.0
   git tag -a v3.1.0 -m "Release version 3.1.0"
   git push origin main --tags
   ```

8. **Merge Back to Develop**
   ```bash
   git checkout develop
   git merge release/3.1.0
   git push origin develop
   ```

9. **Create GitHub Release**
   - Go to GitHub Releases
   - Draft new release
   - Tag: v3.1.0
   - Title: Version 3.1.0
   - Description: Copy from CHANGELOG.md
   - Attach binaries (if applicable)

---

## Getting Help

### Resources

- **Documentation**: Start with USER_GUIDE.md, FAQ.md, ARCHITECTURE.md
- **GitHub Issues**: Search existing issues
- **Discussions**: GitHub Discussions for questions
- **Code**: Read existing code and tests

### Asking Questions

**Good question template:**
```markdown
**Context**: What are you trying to do?
**Problem**: What's not working?
**Tried**: What have you tried?
**Code**: Minimal code sample
**Environment**: OS, Python version, etc.
```

**Before asking:**
1. Search documentation
2. Search existing issues
3. Try debugging yourself
4. Create minimal reproduction

---

## Recognition

### Contributors

All contributors are recognized in:
- CONTRIBUTORS.md (alphabetical)
- Release notes
- Commit history (Co-Authored-By)

### Hall of Fame

Outstanding contributors may be recognized as:
- **Core Contributors**: Significant ongoing contributions
- **Maintainers**: Trusted with merge permissions
- **Emeritus**: Past maintainers who stepped down

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

## Thank You!

Your contributions make Duplicate Finder better for everyone. Whether you're:
- Reporting a bug
- Suggesting a feature
- Writing code
- Improving documentation
- Helping other users

**Thank you for being part of the community!** 🎉

---

**Questions?** Open an issue or discussion on GitHub.

**Ready to contribute?** Pick an issue and get started!

**Version**: 1.0
**Last Updated**: December 2025
