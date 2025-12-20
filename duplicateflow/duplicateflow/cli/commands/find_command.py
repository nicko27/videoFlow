"""
Find command for detecting duplicate videos in a directory.

Usage:
    duplicateflow find /path/to/videos
    duplicateflow find /path/to/videos --preset thorough --recursive
    duplicateflow find /path/to/videos --output-json duplicates.json
"""
import argparse
import csv
from pathlib import Path

from rich.console import Console

from duplicateflow.cli.adapters import RichProgressReporter, RichUIAdapter
from duplicateflow.core.services.scan_service import ScanService
from duplicateflow.core.services.comparison_service import ComparisonService
from duplicateflow.core.services.duplicate_finder_service import DuplicateFinderService
from duplicateflow.pipeline.pipeline import Pipeline

from .display_helpers import display_detection_result


def create_find_parser(subparsers) -> argparse.ArgumentParser:
    """
    Create argument parser for find command.

    Args:
        subparsers: Subparsers object from main parser

    Returns:
        ArgumentParser for find command

    Example:
        >>> parser = argparse.ArgumentParser()
        >>> subparsers = parser.add_subparsers()
        >>> find_parser = create_find_parser(subparsers)
    """
    parser = subparsers.add_parser(
        'find',
        help='Find duplicate videos in a directory',
        description='Scan directory and detect duplicate videos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find duplicates in current directory
  duplicateflow find .

  # Scan recursively with thorough preset
  duplicateflow find /videos --recursive --preset thorough

  # Limit comparisons for large collections
  duplicateflow find /videos --max-comparisons 100

  # Export results to JSON and CSV
  duplicateflow find /videos --output-json dupes.json --output-csv dupes.csv

Available presets: fast, balanced, thorough, multimodal
        """
    )

    parser.add_argument(
        'directory',
        type=str,
        help='Directory to scan for videos'
    )

    parser.add_argument(
        '--preset',
        type=str,
        default='balanced',
        choices=['fast', 'balanced', 'thorough', 'multimodal',
                 'structural', 'hybrid', 'audio_advanced', 'motion_intense'],
        help='Pipeline preset to use (default: balanced)'
    )

    parser.add_argument(
        '--threshold',
        type=float,
        default=70.0,
        help='Similarity threshold for duplicate detection (0-100, default: 70.0)'
    )

    parser.add_argument(
        '--recursive',
        action='store_true',
        help='Scan subdirectories recursively'
    )

    parser.add_argument(
        '--max-comparisons',
        type=int,
        metavar='N',
        help='Limit total number of comparisons (useful for large collections)'
    )

    parser.add_argument(
        '--output-json',
        type=str,
        metavar='FILE',
        help='Export results to JSON file'
    )

    parser.add_argument(
        '--output-csv',
        type=str,
        metavar='FILE',
        help='Export results to CSV file'
    )

    parser.add_argument(
        '--formats',
        nargs='+',
        metavar='EXT',
        help='Filter by video formats (e.g., --formats mp4 mkv avi)'
    )

    parser.add_argument(
        '--min-size',
        type=float,
        metavar='MB',
        help='Minimum file size in MB'
    )

    parser.set_defaults(func=run_find_command)

    return parser


def run_find_command(args) -> int:
    """
    Execute find command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)

    Example:
        >>> args = argparse.Namespace(
        ...     directory='/videos',
        ...     preset='balanced',
        ...     threshold=70.0,
        ...     recursive=True,
        ...     max_comparisons=None,
        ...     output_json=None,
        ...     output_csv=None,
        ...     formats=None,
        ...     min_size=None
        ... )
        >>> exit_code = run_find_command(args)
    """
    console = Console()

    # Validate directory
    directory_path = Path(args.directory)

    if not directory_path.exists():
        console.print(f"[red]✗ Error:[/red] Directory not found: {args.directory}")
        return 1

    if not directory_path.is_dir():
        console.print(f"[red]✗ Error:[/red] Not a directory: {args.directory}")
        return 1

    # Display header
    console.print()
    console.print(f"[bold cyan]Finding duplicate videos...[/bold cyan]")
    console.print(f"[dim]Directory: {directory_path}[/dim]")
    console.print(f"[dim]Recursive: {args.recursive}[/dim]")
    console.print(f"[dim]Preset: {args.preset}[/dim]")
    console.print(f"[dim]Threshold: {args.threshold}%[/dim]")
    if args.max_comparisons:
        console.print(f"[dim]Max comparisons: {args.max_comparisons}[/dim]")
    console.print()

    # Create pipeline from preset
    try:
        pipeline = Pipeline.from_preset(args.preset)
    except Exception as e:
        console.print(f"[red]✗ Error loading preset:[/red] {str(e)}")
        return 1

    # Create services with Rich adapters
    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)

        try:
            # Step 1: Scan for videos
            console.print("[bold]Step 1:[/bold] Scanning for videos...")
            console.print()

            scan_service = ScanService(progress, ui)
            scan_result = scan_service.scan_directory(
                directory_path,
                recursive=args.recursive
            )

            # Apply filters
            videos = scan_result.videos

            if args.formats:
                formats_lower = [f.lower() for f in args.formats]
                videos = [v for v in videos if v.format.value.lower() in formats_lower]
                console.print(f"[dim]Filtered by formats {args.formats}: {len(videos)} videos[/dim]")

            if args.min_size:
                videos = [v for v in videos if v.size_mb >= args.min_size]
                console.print(f"[dim]Filtered by min size {args.min_size}MB: {len(videos)} videos[/dim]")

            console.print()
            console.print(f"[green]✓ Found {len(videos)} videos to analyze[/green]")

            if len(videos) < 2:
                console.print("[yellow]Need at least 2 videos to detect duplicates[/yellow]")
                return 0

            # Calculate total comparisons
            total_comparisons = len(videos) * (len(videos) - 1) // 2
            effective_comparisons = min(total_comparisons, args.max_comparisons) if args.max_comparisons else total_comparisons

            console.print(f"[dim]Total comparisons: {effective_comparisons}[/dim]")
            console.print()

            # Step 2: Find duplicates
            console.print("[bold]Step 2:[/bold] Detecting duplicates...")
            console.print()

            comparison_service = ComparisonService(progress, ui, pipeline)
            finder_service = DuplicateFinderService(progress, ui, comparison_service)

            video_paths = [v.path for v in videos]
            detection_result = finder_service.find_duplicates(
                video_paths,
                threshold=args.threshold,
                max_comparisons=args.max_comparisons
            )

            # Display results
            display_detection_result(console, detection_result)

            # Export to JSON if requested
            if args.output_json:
                try:
                    with open(args.output_json, 'w') as f:
                        f.write(detection_result.to_json(indent=2))
                    console.print()
                    console.print(f"[green]✓ Results exported to JSON:[/green] {args.output_json}")
                except Exception as e:
                    console.print()
                    console.print(f"[red]✗ Error exporting to JSON:[/red] {str(e)}")
                    return 1

            # Export to CSV if requested
            if args.output_csv:
                try:
                    rows = detection_result.to_csv_rows()
                    if rows:
                        with open(args.output_csv, 'w', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                            writer.writeheader()
                            writer.writerows(rows)
                        console.print(f"[green]✓ Results exported to CSV:[/green] {args.output_csv}")
                    else:
                        console.print(f"[yellow]No results to export to CSV[/yellow]")
                except Exception as e:
                    console.print()
                    console.print(f"[red]✗ Error exporting to CSV:[/red] {str(e)}")
                    return 1

            console.print()

            # Return 0 if duplicates found, 1 if not
            return 0 if len(detection_result.duplicate_groups) > 0 else 1

        except Exception as e:
            console.print()
            console.print(f"[red]✗ Error during detection:[/red] {str(e)}")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return 1
