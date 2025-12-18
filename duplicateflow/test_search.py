#!/usr/bin/env python3
"""Test the optimized search functionality."""

import sys
sys.path.insert(0, '.')
from pathlib import Path
import time

import duplicateflow.algorithms
from duplicateflow.processing.parallel_search import ParallelWindowSearch
from duplicateflow.core import get_algorithm

test_dir = Path.home() / 'Downloads' / 'tests'
short_video = test_dir / 'Das Monster und die Schone_1.mp4'
long_video = test_dir / 'Das Monster und die Schone.mp4'

print('='*60)
print('OPTIMIZED SEARCH TEST')
print('='*60)

# Test 1: Parallel search with frame_hash
print('\nTest 1: Parallel search (8 workers)')
print('-'*60)

AlgoClass = get_algorithm('frame_hash')
algo = AlgoClass()
algo.configure(threshold=80)

start = time.time()
searcher = ParallelWindowSearch(num_workers=8)
result = searcher.search(
    str(short_video), str(long_video), 'frame_hash', algo,
    step_size=5.0, show_progress=True, early_stop_threshold=95.0
)
elapsed = time.time() - start

print(f'\nResults:')
print(f'  Best match at: {result["offset"]:.1f}s')
print(f'  Score: {result["score"]:.2f}%')
print(f'  Windows tested: {result["windows_tested"]}/{result["total_windows"]}')
elimination = (1 - result["windows_tested"] / result["total_windows"]) * 100
print(f'  Elimination rate: {elimination:.1f}%')
print(f'  Time: {elapsed:.2f}s')

# Calculate speedup vs linear
expected_linear_time = result["total_windows"] * 0.1  # ~0.1s per window
speedup = expected_linear_time / elapsed
print(f'  Estimated speedup vs linear: {speedup:.0f}x')

print('\n' + '='*60)
print('TEST COMPLETE')
print('='*60)
