#!/usr/bin/env python3
"""
Script to clean up panels.py by removing obsolete non-DuplicateFlow sections.

Sections to remove:
- Multi-Resolution Comparison (lines ~424-480)
- Metadata Quick Filter (lines ~482-522)
- Video Hashing (lines ~524-585)
- Video Comparison (lines ~587-652)
"""

import re

def clean_panels_file(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern 1: Remove Multi-Resolution section
    pattern_mr = r'        # ═+\n        # COMPARAISON MULTI-RÉSOLUTION\n        # ═+\n.*?layout\.addWidget\(mr_group\)\n\n'
    content = re.sub(pattern_mr, '', content, flags=re.DOTALL)

    # Pattern 2: Remove Metadata Filter section
    pattern_metadata = r'        # ═+\n        # FILTRE MÉTADONNÉES.*?\n        # ═+\n.*?layout\.addWidget\(metadata_group\)\n\n'
    content = re.sub(pattern_metadata, '', content, flags=re.DOTALL)

    # Pattern 3: Remove Video Hashing section
    pattern_video_hash = r'        # ═+\n        # HACHAGE VIDÉO\n        # ═+\n.*?layout\.addWidget\(video_hash_group\)\n\n'
    content = re.sub(pattern_video_hash, '', content, flags=re.DOTALL)

    # Pattern 4: Remove Video Comparison section
    pattern_video_comp = r'        # ═+\n        # COMPARAISON VIDÉO\n        # ═+\n.*?layout\.addWidget\(video_comp_group\)\n\n'
    content = re.sub(pattern_video_comp, '', content, flags=re.DOTALL)

    # Remove obsolete widget references
    # Audio fingerprinting references
    content = re.sub(r'\n        # Audio fingerprinting\n.*?tab\.enable_no_audio_fallback = enable_no_audio_fallback\n', '', content, flags=re.DOTALL)

    # Multi-resolution references
    content = re.sub(r'\n        # Multi-resolution\n.*?tab\.mr_medium_threshold_spin = mr_medium_threshold_spin\n', '', content, flags=re.DOTALL)

    # Metadata filter references
    content = re.sub(r'\n        # Metadata filter\n.*?tab\.metadata_size_ratio_spin = metadata_size_ratio_spin\n', '', content, flags=re.DOTALL)

    # Video hashing references
    content = re.sub(r'\n        # Video hashing\n.*?tab\.video_cache_size_spin = video_cache_size_spin\n', '', content, flags=re.DOTALL)

    # Video comparison references
    content = re.sub(r'\n        # Video comparison\n.*?tab\.comparison_cache_size_spin = comparison_cache_size_spin\n', '', content, flags=re.DOTALL)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Cleaned panels.py written to {output_path}")

    # Count lines removed
    with open(input_path, 'r') as f:
        original_lines = len(f.readlines())
    with open(output_path, 'r') as f:
        cleaned_lines = len(f.readlines())

    print(f"📊 Original: {original_lines} lines")
    print(f"📊 Cleaned: {cleaned_lines} lines")
    print(f"📊 Removed: {original_lines - cleaned_lines} lines ({(original_lines - cleaned_lines) / original_lines * 100:.1f}%)")

if __name__ == "__main__":
    input_file = "/Users/nico/Documents/videoFlow/src/plugins/duplicate_finder/ui/panels.py"
    output_file = "/Users/nico/Documents/videoFlow/src/plugins/duplicate_finder/ui/panels_cleaned.py"
    clean_panels_file(input_file, output_file)
