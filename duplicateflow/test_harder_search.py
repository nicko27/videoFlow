#!/usr/bin/env python3
"""Test search with harder video match."""

import sys
sys.path.insert(0, '.')
from pathlib import Path
import time

import duplicateflow.algorithms
from duplicateflow.processing.parallel_search import AdaptiveStepSearch
from duplicateflow.core import get_algorithm

test_dir = Path.home() / 'Downloads' / 'tests'
short_video = test_dir / 'Das Monster und die Schone_2.mp4'
long_video = test_dir / 'Das Monster und die Schone.mp4'

print('='*60)
print('ADAPTIVE SEARCH TEST (Harder Match)')
print('='*60)

# Test: Adaptive search
print('\nTest: Adaptive two-phase search')
print('-'*60)

AlgoClass = get_algorithm('frame_hash')
algo = AlgoClass()
algo.configure(threshold=60)  # Lower threshold for harder match

start = time.time()
searcher = AdaptiveStepSearch(num_workers=8)
result = searcher.search(
    str(short_video), str(long_video), 'frame_hash', algo,
    initial_step=30.0, fine_step=2.0, coarse_threshold=40.0,
    show_progress=True
)
elapsed = time.time() - start

print(f'\nResults:')
print(f'  Best match at: {result["offset"]:.1f}s')
print(f'  Score: {result["score"]:.2f}%')
print(f'  Windows tested: {result["windows_tested"]}')
print(f'  Time: {elapsed:.2f}s')

print('\n' + '='*60)
print('TEST COMPLETE')
print('='*60)
