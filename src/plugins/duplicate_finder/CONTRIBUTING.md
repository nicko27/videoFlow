# Contributing to Duplicate Finder

Thank you for your interest in contributing to Duplicate Finder! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Environment](#development-environment)
4. [Project Structure](#project-structure)
5. [Coding Standards](#coding-standards)
6. [Documentation Standards](#documentation-standards)
7. [Testing Guidelines](#testing-guidelines)
8. [Contribution Workflow](#contribution-workflow)
9. [Areas Needing Help](#areas-needing-help)
10. [Reporting Bugs](#reporting-bugs)
11. [Feature Requests](#feature-requests)

---

## Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in all interactions.

**Expected Behavior**:
- Be respectful of differing viewpoints
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

**Unacceptable Behavior**:
- Harassment or discrimination
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information

---

## Getting Started

### Prerequisites

- **Python**: 3.8 or higher
- **Git**: For version control
- **FFmpeg**: For video/audio processing
- **Operating System**: macOS, Linux, or Windows

### Quick Setup

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/videoFlow.git
cd videoFlow/src/plugins/duplicate_finder

# 3. Install dependencies
pip install -r ../../../requirements.txt

# 4. Install development dependencies
pip install pytest pytest-cov black flake8 mypy

# 5. Run tests to verify setup
pytest

# 6. You're ready to contribute!
```

---

## Development Environment

### Recommended Tools

**IDE/Editor**:
- **PyCharm** (recommended for Python development)
- **VS Code** with Python extension
- **Vim/Emacs** with Python plugins

**Essential Extensions** (for VS Code):
- Python (Microsoft)
- Pylance (type checking)
- autoDocstring (docstring generation)
- GitLens (Git visualization)

### Virtual Environment

We **strongly recommend** using a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black flake8
```

### Running the Application

```bash
# From the project root
python main.py

# The plugin should appear in the Plugins menu
```

---

## Project Structure

```
duplicate_finder/
├── main_window.py              # Main UI window
├── comparison_dialog.py        # Video comparison UI
├── video_hasher.py             # Perceptual hashing
├── audio_fingerprinting.py     # Audio analysis
├── subsequence_detector.py     # Scene detection
├── database_manager.py         # SQLite operations
│
├── handlers/                   # Business logic handlers
│   ├── file_handler.py         # File operations
│   ├── analysis_handler.py     # Analysis orchestration
│   ├── duplicate_handler.py    # Duplicate management
│   └── audio_first_handler.py  # Audio-first workflow
│
├── workers/                    # Background workers (QThread)
│   ├── hash_worker.py          # Parallel hashing
│   ├── comparison_worker.py    # Parallel comparison
│   ├── audio_worker.py         # Audio extraction
│   └── scene_worker.py         # Scene detection
│
├── analysis/                   # Analysis algorithms
│   ├── lsh_index.py            # LSH filtering
│   └── multi_resolution.py     # Multi-resolution analysis
│
├── validators/                 # Security & validation
│   └── file_validator.py       # 8-layer file validation
│
├── ui/                         # UI components
│   └── panels.py               # UI panels
│
├── managers/                   # Managers
│   └── settings_manager.py     # Settings persistence
│
└── config/                     # Configuration
    └── constants.py            # Constants & defaults
```

### Key Files to Know

**Entry Points**:
- `main_window.py` - Main application window
- `handlers/analysis_handler.py` - Analysis workflow orchestration

**Core Algorithms**:
- `video_hasher.py` - Video hashing (pHash, DCT)
- `audio_fingerprinting.py` - Audio fingerprinting (like Shazam)
- `analysis/lsh_index.py` - LSH for fast filtering

**UI Components**:
- `comparison_dialog.py` - Side-by-side comparison
- `progress_widgets.py` - Progress bars & file lists
- `video_preview_widget.py` - Video player widget

---

## Coding Standards

### Python Style Guide

We follow **PEP 8** with minor modifications:

**Line Length**:
- **Preferred**: 100 characters
- **Maximum**: 120 characters (for complex lines)

**Naming Conventions**:
```python
# Classes: PascalCase
class VideoHasher:
    pass

# Functions/methods: snake_case
def compute_video_hash():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_WORKERS = 8

# Private methods: _leading_underscore
def _internal_method():
    pass
```

**Imports**:
```python
# Standard library
import os
import sys
from typing import List, Dict, Optional

# Third-party
import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget

# Local
from src.core.logger import Logger
from ..validators import FileValidator
```

### Type Hints

**Always use type hints** for function signatures:

```python
def process_video(
    file_path: str,
    threshold: float = 0.85,
    workers: int = 4
) -> Dict[str, Any]:
    """Process video and return results."""
    pass
```

### Error Handling

**Use specific exceptions**:
```python
# Good
try:
    with open(file_path, 'r') as f:
        data = f.read()
except FileNotFoundError:
    logger.error(f"File not found: {file_path}")
except PermissionError:
    logger.error(f"Permission denied: {file_path}")

# Bad - avoid bare except
try:
    risky_operation()
except:  # Too broad!
    pass
```

**Use context managers** for resources:
```python
# Good
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    # ... operations

# Also good for our decorators
@handle_errors(default_return=[])
def process_files(files: List[str]) -> List[str]:
    # Errors handled automatically
    pass
```

---

## Documentation Standards

### Docstring Format

We use **Google-style** docstrings:

```python
def compare_videos(
    file1: str,
    file2: str,
    threshold: float = 0.85
) -> Dict[str, Any]:
    """Compare two videos for similarity.

    This function uses perceptual hashing to compare two videos
    and determine their similarity percentage.

    Args:
        file1: Path to the first video file
        file2: Path to the second video file
        threshold: Minimum similarity threshold (0.0-1.0)

    Returns:
        Dictionary containing:
            - similarity: Float (0.0-1.0)
            - is_duplicate: Boolean
            - hash1: First video hash
            - hash2: Second video hash

    Raises:
        FileNotFoundError: If either video file doesn't exist
        ValueError: If threshold is not in range [0.0, 1.0]

    Example:
        >>> result = compare_videos('video1.mp4', 'video2.mp4', 0.90)
        >>> print(result['similarity'])
        0.95
        >>> print(result['is_duplicate'])
        True

    Note:
        This function caches hashes for better performance on
        repeated comparisons.
    """
    pass
```

### Class Docstrings

```python
class VideoHasher:
    """Compute perceptual hashes for video files.

    This class provides methods for computing perceptual hashes (pHash)
    of video files for similarity comparison. It supports caching for
    improved performance.

    The hasher uses DCT (Discrete Cosine Transform) on video frames to
    create a hash that is robust to minor changes like compression or
    resizing.

    Attributes:
        cache_dir: Directory for storing cached hashes
        frame_count: Number of frames to sample per video
        hash_size: Size of the hash in bits (default: 8)

    Example:
        >>> hasher = VideoHasher(cache_dir='/tmp/cache')
        >>> hash1 = hasher.compute_hash('video1.mp4')
        >>> hash2 = hasher.compute_hash('video2.mp4')
        >>> similarity = hasher.compare_hashes(hash1, hash2)
    """
```

### Module Docstrings

```python
"""Video hashing module for perceptual hash computation.

This module provides the VideoHasher class for computing perceptual hashes
of video files. It supports multiple hashing algorithms and caching for
improved performance.

The module uses OpenCV for video processing and imagehash for hash computation.

Example:
    from duplicate_finder.video_hasher import VideoHasher

    hasher = VideoHasher()
    hash = hasher.compute_hash('video.mp4')
"""
```

### Comments

**Use comments for complex logic**:
```python
# Good - explains WHY
# Use LSH for fast filtering to eliminate 95% of non-duplicates
# before expensive video comparison
candidates = self.lsh_index.query(audio_hash, num_results=100)

# Bad - explains WHAT (obvious from code)
# Set x to 10
x = 10
```

---

## Testing Guidelines

### Writing Tests

**Test file location**:
```
tests/
├── test_video_hasher.py
├── test_audio_fingerprinting.py
└── test_database_manager.py
```

**Test structure**:
```python
import pytest
from duplicate_finder.video_hasher import VideoHasher

class TestVideoHasher:
    """Tests for VideoHasher class."""

    @pytest.fixture
    def hasher(self):
        """Create a VideoHasher instance for testing."""
        return VideoHasher(cache_dir='/tmp/test_cache')

    def test_compute_hash_basic(self, hasher, tmp_path):
        """Test basic hash computation."""
        # Arrange
        video_path = create_test_video(tmp_path)

        # Act
        hash_result = hasher.compute_hash(video_path)

        # Assert
        assert hash_result is not None
        assert len(hash_result) == hasher.hash_size ** 2

    def test_compare_identical_videos(self, hasher):
        """Test that identical videos have 100% similarity."""
        hash1 = hasher.compute_hash('test_video.mp4')
        hash2 = hasher.compute_hash('test_video.mp4')

        similarity = hasher.compare_hashes(hash1, hash2)

        assert similarity == 1.0

    def test_invalid_file_raises_error(self, hasher):
        """Test that non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            hasher.compute_hash('nonexistent.mp4')
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=duplicate_finder --cov-report=html

# Run specific test file
pytest tests/test_video_hasher.py

# Run with verbose output
pytest -v

# Run with logging
pytest -s --log-cli-level=DEBUG
```

### Test Coverage Goals

- **New code**: 80% minimum coverage
- **Bug fixes**: Add test case for the bug
- **Critical paths**: 100% coverage (security, data integrity)

---

## Contribution Workflow

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/videoFlow.git
cd videoFlow/src/plugins/duplicate_finder
```

### 2. Create a Branch

```bash
# Feature branch
git checkout -b feature/add-new-algorithm

# Bug fix branch
git checkout -b fix/issue-123-memory-leak

# Documentation branch
git checkout -b docs/improve-readme
```

**Branch naming**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Test improvements

### 3. Make Changes

- Write clean, well-documented code
- Follow coding standards
- Add tests for new functionality
- Update documentation

### 4. Test Your Changes

```bash
# Run tests
pytest

# Check code style
black .
flake8 .

# Type checking (optional but recommended)
mypy duplicate_finder/
```

### 5. Commit

```bash
git add .
git commit -m "Add new LSH algorithm for faster filtering

- Implement MinHash LSH for audio fingerprints
- Add tests for LSH indexing
- Update documentation

Fixes #123"
```

**Commit message format**:
```
<type>: <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

### 6. Push and Create PR

```bash
git push origin feature/add-new-algorithm
```

Then create a Pull Request on GitHub with:
- **Clear title**: What does this PR do?
- **Description**: Why is this change needed?
- **Testing**: How was this tested?
- **Screenshots**: If UI changes

### 7. Code Review

- Address review comments
- Update PR as needed
- Be responsive to feedback

---

## Areas Needing Help

### High Priority

**1. Internationalization (i18n)** - ISSUE #11
- **Task**: Translate 200+ French strings to English
- **Skills**: Python, translation
- **Effort**: Large (~8-10 hours)
- **Impact**: High (makes app accessible to non-French users)
- **Files**: Most `.py` files with UI strings

**2. Documentation Screenshots**
- **Task**: Add screenshots to USER_MANUAL.md
- **Skills**: Using the application
- **Effort**: Medium (~2-3 hours)
- **Impact**: Medium (improves user manual)

### Medium Priority

**3. Test Coverage** - ISSUE #17 (partial)
- **Task**: Increase test coverage to 80%+
- **Skills**: Python, pytest
- **Effort**: Large (~10-15 hours)
- **Impact**: High (prevents regressions)
- **Files**: All untested modules

**4. Docstring Enhancement** - ISSUE #20 (partial)
- **Task**: Add docstrings to remaining functions
- **Skills**: Python, technical writing
- **Effort**: Medium (~6-8 hours)
- **Impact**: Medium (improves maintainability)
- **Files**: `main_window.py`, `workers/*.py`

### Low Priority

**5. Code Refactoring** - ISSUE #21
- **Task**: Break down long functions (>100 lines)
- **Skills**: Python, refactoring
- **Effort**: Medium (~4-6 hours)
- **Impact**: Low (code quality)
- **Files**: `database_manager.py:init_database()`, others

**6. Performance Optimization**
- **Task**: Optimize slow operations
- **Skills**: Python, profiling
- **Effort**: Variable
- **Impact**: Medium

---

## Reporting Bugs

### Before Reporting

1. **Check existing issues** on GitHub
2. **Search documentation** for solutions
3. **Try latest version** - bug may be fixed

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- OS: [e.g., macOS 12.0]
- Python version: [e.g., 3.9.7]
- Application version: [e.g., 1.0]

**Logs**
Attach relevant logs from `~/.duplicate_finder/logs/`

**Additional context**
Any other context about the problem.
```

### Priority Levels

- **Critical**: App crashes, data loss
- **High**: Major feature broken
- **Medium**: Minor feature broken
- **Low**: Cosmetic issues

---

## Feature Requests

### Before Requesting

1. **Check existing issues** - may already be planned
2. **Consider scope** - fits project goals?
3. **Think about implementation** - is it feasible?

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives**
Other solutions you've considered.

**Additional context**
Mockups, examples, or other context.

**Would you be willing to implement this?**
Yes/No - and what help you'd need.
```

---

## Code Review Checklist

Before submitting your PR, verify:

**Code Quality**:
- [ ] Code follows PEP 8 style guide
- [ ] No unnecessary comments (code is self-documenting)
- [ ] No debug print statements left in code
- [ ] No hardcoded paths or credentials

**Documentation**:
- [ ] All public functions have docstrings
- [ ] Docstrings follow Google style
- [ ] README updated if needed
- [ ] CHANGELOG updated if applicable

**Testing**:
- [ ] Tests added for new functionality
- [ ] All tests pass (`pytest`)
- [ ] Coverage increased or maintained
- [ ] Manual testing performed

**Security**:
- [ ] No SQL injection vulnerabilities
- [ ] File paths validated
- [ ] User input sanitized
- [ ] No sensitive data in logs

**Performance**:
- [ ] No obvious performance issues
- [ ] Large files handled efficiently
- [ ] Memory leaks checked

---

## Getting Help

### Resources

- **Documentation**: See [README.md](README.md) for links
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **User Manual**: See [USER_MANUAL.md](USER_MANUAL.md)
- **API Reference**: See [FUNCTIONS_COMPLETE_REFERENCE.md](FUNCTIONS_COMPLETE_REFERENCE.md)

### Community

- **GitHub Issues**: For bugs and features
- **Discussions**: For questions and ideas
- **Email**: For private concerns

### Response Time

- **Bug reports**: 1-3 days
- **Feature requests**: 1-2 weeks
- **Pull requests**: 3-7 days

---

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md (to be created)
- Credited in release notes
- Mentioned in commit messages

Significant contributors may receive:
- Maintainer status
- Direct commit access
- Project decision-making input

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

## Questions?

If you have questions not covered here:
1. Check the documentation
2. Search existing issues
3. Open a new issue with the "question" label

---

**Thank you for contributing to Duplicate Finder!** 🎉

Every contribution, no matter how small, makes a difference.
