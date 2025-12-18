#!/usr/bin/env python3
"""
One-command duplicate finder for a directory of videos.

This script:
1. Indexes all videos in directory (if not already indexed)
2. Finds all matching pairs
3. Exports results
"""

import click
import logging
from pathlib import Path

from duplicateflow.core import get_algorithm
from duplicateflow.processing.fingerprint_index import FingerprintIndex

logger = logging.getLogger('duplicateflow.find_duplicates')


@click.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), required=True, help='Output file (JSON or CSV)')
@click.option('--db', type=click.Path(), default=None, help='Database path (default: input_dir/fingerprints.db)')
@click.option('--algorithm', '-a', default='audio_fingerprint', help='Algorithm to use')
@click.option('--min-votes', default=200, help='Minimum votes for match')
@click.option('--max-pairs', default=10000, help='Maximum pairs to return')
@click.option('--format', type=click.Choice(['json', 'csv']), default='json', help='Output format')
@click.option('--force-reindex', is_flag=True, help='Re-index all videos')
@click.option('--verbose', '-v', count=True, help='Increase verbosity')
def find_duplicates(input_dir, output, db, algorithm, min_votes, max_pairs, format, force_reindex, verbose):
    """
    Find all duplicate videos in a directory with a single command.

    This command automatically:
    1. Indexes all videos (or uses existing index)
    2. Finds all matching pairs
    3. Exports results to file

    Example:
        python3 -m duplicateflow.cli.find_duplicates ~/Downloads/tests -o matches.json
    """
    # Configure logging
    if verbose >= 2:
        log_level = logging.DEBUG
    elif verbose == 1:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Default DB path in input directory
    if db is None:
        db = Path(input_dir) / 'fingerprints.db'

    click.echo(f"Processing videos in: {input_dir}")
    click.echo(f"Database: {db}")
    click.echo(f"Output: {output}\n")

    # Initialize index
    index_obj = FingerprintIndex(db_path=str(db))

    # Check if we need to index
    stats = index_obj.get_stats()
    needs_indexing = stats['video_count'] == 0 or force_reindex

    if needs_indexing or force_reindex:
        click.echo("=" * 60)
        click.echo("STEP 1: Indexing videos")
        click.echo("=" * 60)

        # Get algorithm
        AlgoClass = get_algorithm(algorithm)
        algo = AlgoClass()
        algo.configure()

        # Index directory
        index_obj.index_directory(
            directory=input_dir,
            algorithm=algo,
            force=force_reindex
        )

        # Show updated stats
        stats = index_obj.get_stats()
        click.echo(f"\nIndexing complete:")
        click.echo(f"  Videos: {stats['video_count']}")
        click.echo(f"  Fingerprints: {stats['fingerprint_count']:,}")
        click.echo(f"  Database size: {stats['db_size_mb']:.2f} MB\n")
    else:
        click.echo(f"Using existing index with {stats['video_count']} videos\n")

    # Find matches
    click.echo("=" * 60)
    click.echo("STEP 2: Finding all matching pairs")
    click.echo("=" * 60)

    matches = index_obj.find_all_matches(
        min_votes=min_votes,
        max_pairs=max_pairs
    )

    if not matches:
        click.echo("\nNo matches found.")
        return

    click.echo(f"\nFound {len(matches)} matching pairs!\n")

    # Show top 10 matches
    click.echo("Top 10 matches:")
    click.echo("-" * 60)
    for i, match in enumerate(matches[:10], 1):
        v1_name = Path(match.video1_path).name
        v2_name = Path(match.video2_path).name
        click.echo(f"{i:2d}. {v1_name}")
        click.echo(f"    <-> {v2_name}")
        click.echo(f"    Offset: {match.offset_seconds:.1f}s | Votes: {match.votes} | Confidence: {match.confidence:.1f}%\n")

    if len(matches) > 10:
        click.echo(f"... and {len(matches) - 10} more matches\n")

    # Export
    click.echo("=" * 60)
    click.echo("STEP 3: Exporting results")
    click.echo("=" * 60)

    index_obj.export_matches(matches, output, format=format)
    click.echo(f"\nResults exported to: {output}")
    click.echo("\nDone!")


if __name__ == '__main__':
    find_duplicates()
