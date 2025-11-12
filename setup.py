#!/usr/bin/env python3
"""
VideoFlow Setup Script

This script allows VideoFlow to be installed as a Python package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

# Development requirements
dev_requirements_file = Path(__file__).parent / "requirements-dev.txt"
dev_requirements = []
if dev_requirements_file.exists():
    dev_requirements = [
        line.strip()
        for line in dev_requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="videoflow",
    version="1.0.0",
    author="VideoFlow Team",
    author_email="contact@videoflow.example.com",
    description="Professional video file management and processing suite",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/YOUR_USERNAME/videoFlow",
    project_urls={
        "Bug Reports": "https://github.com/YOUR_USERNAME/videoFlow/issues",
        "Source": "https://github.com/YOUR_USERNAME/videoFlow",
        "Documentation": "https://github.com/YOUR_USERNAME/videoFlow/blob/main/DEVELOPER_GUIDE.md",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Video :: Conversion",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: MacOS :: MacOS X",
        "Environment :: MacOS X",
        "Natural Language :: English",
    ],
    keywords="video processing conversion duplicate-finder video-editor",
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "test": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-qt>=4.2.0",
            "pytest-xvfb>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "videoflow=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.txt", "*.md"],
    },
    zip_safe=False,
    platforms=["MacOS"],
)
