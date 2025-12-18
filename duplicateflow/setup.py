"""
DuplicateFlow setup script.

Installation:
    # Minimal (9 core algorithms)
    pip install .

    # With audio (12 algorithms)
    pip install .[audio]

    # With ML (16 algorithms)
    pip install .[audio,ml]

    # With deep learning (19 algorithms)
    pip install .[audio,ml,dl]

    # Development mode
    pip install -e .[audio,ml,dev]
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
if readme_file.exists():
    with open(readme_file, "r", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "DuplicateFlow - Video Duplicate Detection CLI"

# Read requirements
def read_requirements(filename):
    """Read requirements from file."""
    req_file = Path(__file__).parent / filename
    if req_file.exists():
        with open(req_file, "r", encoding="utf-8") as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]
    return []

# Core requirements
install_requires = read_requirements("requirements.txt")

# Extra requirements
extras_require = {
    "audio": read_requirements("requirements-audio.txt"),
    "ml": read_requirements("requirements-ml.txt"),
    "dl": read_requirements("requirements-dl.txt"),
    "dev": read_requirements("requirements-dev.txt"),
}

# Convenience meta-packages
extras_require["full"] = (
    extras_require["audio"] +
    extras_require["ml"] +
    extras_require["dl"]
)

setup(
    name="duplicateflow",
    version="1.0.0",
    author="DuplicateFlow Team",
    author_email="duplicateflow@example.com",
    description="CLI tool for detecting video subsequences using 13 free algorithms",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/duplicateflow",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/duplicateflow/issues",
        "Documentation": "https://github.com/yourusername/duplicateflow/docs",
        "Source Code": "https://github.com/yourusername/duplicateflow",
    },
    packages=find_packages(exclude=["tests", "tests.*", "docs", "scripts"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Multimedia :: Video",
        "Topic :: Scientific/Engineering :: Image Recognition",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "duplicateflow=duplicateflow.cli.main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "duplicateflow": [
            "config/templates/*.yaml",
            "config/templates/pipelines/*.yaml",
        ],
    },
    keywords=[
        "video",
        "duplicate",
        "detection",
        "similarity",
        "scene",
        "comparison",
        "opencv",
        "computer-vision",
        "machine-learning",
    ],
    zip_safe=False,
)
