#!/usr/bin/env python3
"""Quick test of Phase 6 features."""

import sys
sys.path.insert(0, '.')
from pathlib import Path
import logging

import duplicateflow.algorithms
from duplicateflow import Pipeline

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')

test_dir = Path.home() / 'Downloads' / 'tests'
excerpt = test_dir / 'Das Monster und die Schone_2.mp4'
long_video = test_dir / 'Das Monster und die Schone.mp4'

print('Testing pipeline with progress bar and logging\n')
print('='*60)

pipeline = Pipeline.from_preset('balanced', show_progress=True)

print(f'\nComparing: {excerpt.name} vs {long_video.name}\n')
result = pipeline.compare(str(excerpt), str(long_video), use_cache=True)

print('\n' + '='*60)
print('RESULTS')
print('='*60)
print(f'Global score: {result["global_score"]:.2f}%')
print(f'Accepted: {result["accepted"]}')
print(f'Algorithms run: {result["metadata"]["algorithms_run"]}/{result["metadata"]["total_algorithms"]}')

if result['metadata'].get('early_exit'):
    print('Early termination: Yes')
else:
    print('Early termination: No')

print('\nIndividual Results:')
for algo_result in result['individual_results']:
    print(f"  - {algo_result['algorithm']}: {algo_result['similarity']:.2f}% (weight={algo_result['weight']:.2f})")
