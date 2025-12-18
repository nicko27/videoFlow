"""
Utility modules for DuplicateFlow.

This package contains helper modules:
- hashing: MD5 utilities for file identification
- logger: Logging configuration (to be implemented)
- video: Video file utilities (to be implemented)
"""

from duplicateflow.utils.hashing import (
    compute_file_md5,
    compute_file_md5_fast,
    FileHashCache,
    get_video_hash_cached,
    compute_pair_hash,
    verify_file_hash,
)

__all__ = [
    "compute_file_md5",
    "compute_file_md5_fast",
    "FileHashCache",
    "get_video_hash_cached",
    "compute_pair_hash",
    "verify_file_hash",
]
