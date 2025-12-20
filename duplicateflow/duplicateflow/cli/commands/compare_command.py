"""
Compare command for comparing two videos.

Usage:
    duplicateflow compare video1.mp4 video2.mp4
    duplicateflow compare video1.mp4 video2.mp4 --preset thorough
    duplicateflow compare video1.mp4 video2.mp4 --output-json results.json --show-details
"""
import argparse
from pathlib import Path

from rich.console import Console

from duplicateflow.cli.adapters import RichProgressReporter, RichUIAdapter
from duplicateflow.core.services.comparison_service import ComparisonService
from duplicateflow.pipeline.pipeline import Pipeline

from .display_helpers import display_comparison_result


def create_compare_parser(subparsers) -> argparse.ArgumentParser:
    """
    Create argument parser for compare command.

    Args:
        subparsers: Subparsers object from main parser

    Returns:
        ArgumentParser for compare command

    Example:
        >>> parser = argparse.ArgumentParser()
        >>> subparsers = parser.add_subparsers()
        >>> compare_parser = create_compare_parser(subparsers)
    """
    parser = subparsers.add_parser(
        'compare',
        help='Compare two videos for similarity',
        description='Compare two videos using duplicate detection algorithms',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two videos with balanced preset
  duplicateflow compare movie1.mp4 movie2.mp4

  # Use thorough preset for higher accuracy
  duplicateflow compare movie1.mp4 movie2.mp4 --preset thorough

  # Show algorithm details
  duplicateflow compare movie1.mp4 movie2.mp4 --show-details

  # Export result to JSON
  duplicateflow compare movie1.mp4 movie2.mp4 --output-json result.json

Available presets: fast, balanced, thorough, multimodal
        """
    )

    parser.add_argument(
        'video1',
        type=str,
        help='Path to first video'
    )

    parser.add_argument(
        'video2',
        type=str,
        help='Path to second video'
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
        '--output-json',
        type=str,
        metavar='FILE',
        help='Export results to JSON file'
    )

    parser.add_argument(
        '--show-details',
        action='store_true',
        help='Show detailed algorithm results'
    )

    parser.set_defaults(func=run_compare_command)

    return parser


def run_compare_command(args) -> int:
    """
    Execute compare command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)

    Example:
        >>> args = argparse.Namespace(
        ...     video1='v1.mp4',
        ...     video2='v2.mp4',
        ...     preset='balanced',
        ...     threshold=70.0,
        ...     output_json=None,
        ...     show_details=False
        ... )
        >>> exit_code = run_compare_command(args)
    """
    console = Console()

    # Validate file paths
    video1_path = Path(args.video1)
    video2_path = Path(args.video2)

    if not video1_path.exists():
        console.print(f"[red]✗ Error:[/red] Video 1 not found: {args.video1}")
        return 1

    if not video2_path.exists():
        console.print(f"[red]✗ Error:[/red] Video 2 not found: {args.video2}")
        return 1

    # Display header
    console.print()
    console.print(f"[bold cyan]Comparing videos...[/bold cyan]")
    console.print(f"[dim]Preset: {args.preset}[/dim]")
    console.print(f"[dim]Threshold: {args.threshold}%[/dim]")
    console.print()

    # Create pipeline from preset
    try:
        pipeline = Pipeline.from_preset(args.preset)
    except Exception as e:
        console.print(f"[red]✗ Error loading preset:[/red] {str(e)}")
        return 1

    # Create service with Rich adapters
    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)

        try:
            service = ComparisonService(progress, ui, pipeline)

            # Compare videos
            result = service.compare_videos(
                video1_path,
                video2_path,
                args.threshold
            )

            # Display results
            display_comparison_result(console, result, args.show_details)

            # Export to JSON if requested
            if args.output_json:
                try:
                    with open(args.output_json, 'w') as f:
                        f.write(result.to_json(indent=2))
                    console.print()
                    console.print(f"[green]✓ Results exported to:[/green] {args.output_json}")
                except Exception as e:
                    console.print()
                    console.print(f"[red]✗ Error exporting to JSON:[/red] {str(e)}")
                    return 1

            console.print()

            # Return 0 if duplicate found, 1 if not (for scripting)
            return 0 if result.is_duplicate else 1

        except Exception as e:
            console.print()
            console.print(f"[red]✗ Error during comparison:[/red] {str(e)}")
            return 1
