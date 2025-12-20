"""
Benchmark command for testing pipeline performance and accuracy.

Usage:
    duplicateflow benchmark video1.mp4 video2.mp4 --preset balanced
    duplicateflow benchmark video1.mp4 video2.mp4 --presets fast balanced thorough
    duplicateflow benchmark --testset testdata/ground_truth.json --preset balanced
"""
import argparse
import csv
import json
from pathlib import Path

from rich.console import Console

from duplicateflow.cli.adapters import RichProgressReporter, RichUIAdapter
from duplicateflow.core.services.benchmark_service import BenchmarkService

from .display_helpers import (
    display_comparison_benchmark,
    display_testset_benchmark,
)


def create_benchmark_parser(subparsers) -> argparse.ArgumentParser:
    """
    Create argument parser for benchmark command.

    Args:
        subparsers: Subparsers object from main parser

    Returns:
        ArgumentParser for benchmark command

    Example:
        >>> parser = argparse.ArgumentParser()
        >>> subparsers = parser.add_subparsers()
        >>> benchmark_parser = create_benchmark_parser(subparsers)
    """
    parser = subparsers.add_parser(
        'benchmark',
        help='Benchmark pipeline performance and accuracy',
        description='Test and compare pipeline presets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Benchmark single preset
  duplicateflow benchmark video1.mp4 video2.mp4 --preset balanced

  # Compare multiple presets
  duplicateflow benchmark video1.mp4 video2.mp4 \\
    --presets fast balanced thorough multimodal

  # Test accuracy on test set
  duplicateflow benchmark --testset testdata/ground_truth.json \\
    --preset balanced

  # Profile algorithms
  duplicateflow benchmark video1.mp4 video2.mp4 \\
    --preset thorough \\
    --profile-algorithms

  # Export results
  duplicateflow benchmark video1.mp4 video2.mp4 \\
    --presets fast balanced thorough \\
    --output-json benchmark.json \\
    --output-csv benchmark.csv

Available presets: fast, balanced, thorough, multimodal,
                   structural, hybrid, audio_advanced, motion_intense
        """
    )

    # Videos (optional - mutually exclusive with testset)
    parser.add_argument(
        'videos',
        nargs='*',
        metavar='VIDEO',
        help='Two videos to compare (video1 video2)'
    )

    # Test set mode
    parser.add_argument(
        '--testset',
        type=str,
        metavar='FILE',
        help='Test set JSON file with ground truth'
    )

    # Pipeline selection
    parser.add_argument(
        '--preset',
        type=str,
        help='Single preset to benchmark'
    )
    parser.add_argument(
        '--presets',
        nargs='+',
        metavar='PRESET',
        help='Multiple presets to compare'
    )

    # Options
    parser.add_argument(
        '--threshold',
        type=float,
        default=70.0,
        help='Similarity threshold (0-100, default: 70.0)'
    )
    parser.add_argument(
        '--profile-algorithms',
        action='store_true',
        help='Show detailed algorithm profiling'
    )
    parser.add_argument(
        '--ground-truth',
        type=str,
        choices=['duplicate', 'not-duplicate'],
        help='Specify ground truth for accuracy calculation'
    )

    # Output
    parser.add_argument(
        '--output-json',
        type=str,
        metavar='FILE',
        help='Export results to JSON'
    )
    parser.add_argument(
        '--output-csv',
        type=str,
        metavar='FILE',
        help='Export results to CSV'
    )

    parser.set_defaults(func=run_benchmark_command)

    return parser


def run_benchmark_command(args) -> int:
    """
    Execute benchmark command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)

    Example:
        >>> args = argparse.Namespace(
        ...     videos=['/v1.mp4', '/v2.mp4'],
        ...     testset=None,
        ...     preset='balanced',
        ...     presets=None,
        ...     threshold=70.0,
        ...     profile_algorithms=False,
        ...     ground_truth=None,
        ...     output_json=None,
        ...     output_csv=None
        ... )
        >>> exit_code = run_benchmark_command(args)
    """
    console = Console()

    # Validate input mode
    if args.testset and args.videos:
        console.print("[red]✗ Error:[/red] Cannot use both --testset and video arguments")
        return 1

    if not args.testset and not args.videos:
        console.print("[red]✗ Error:[/red] Provide either --testset or two videos")
        return 1

    # Validate videos mode
    if args.videos:
        if len(args.videos) != 2:
            console.print("[red]✗ Error:[/red] Provide exactly 2 videos to compare")
            return 1

        video1, video2 = Path(args.videos[0]), Path(args.videos[1])

        if not video1.exists():
            console.print(f"[red]✗ Error:[/red] Video not found: {video1}")
            return 1
        if not video2.exists():
            console.print(f"[red]✗ Error:[/red] Video not found: {video2}")
            return 1

    # Validate testset mode
    if args.testset:
        testset_path = Path(args.testset)
        if not testset_path.exists():
            console.print(f"[red]✗ Error:[/red] Test set not found: {testset_path}")
            return 1

    # Determine presets to test
    if args.presets:
        presets = args.presets
    elif args.preset:
        presets = [args.preset]
    else:
        presets = ['balanced']  # Default

    # Display header
    console.print()
    console.print(f"[bold cyan]Benchmarking DuplicateFlow Pipelines[/bold cyan]")
    console.print()

    # Create service
    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)
        service = BenchmarkService(progress, ui)

        try:
            if args.testset:
                # Test set benchmark mode
                testset_path = Path(args.testset)

                console.print(f"[bold]Mode:[/bold] Test Set Evaluation")
                console.print(f"[bold]Test Set:[/bold] {testset_path}")
                console.print(f"[bold]Pipeline:[/bold] {presets[0]}")
                console.print(f"[bold]Threshold:[/bold] {args.threshold}%")
                console.print()

                preset = presets[0]  # Use first preset for testset
                result = service.benchmark_testset(
                    testset_path,
                    preset,
                    args.threshold
                )

                # Display testset results
                display_testset_benchmark(console, result)

                # Export if requested
                if args.output_json:
                    try:
                        with open(args.output_json, 'w') as f:
                            f.write(result.to_json(indent=2))
                        console.print()
                        console.print(f"[green]✓ Results exported to JSON:[/green] {args.output_json}")
                    except Exception as e:
                        console.print()
                        console.print(f"[red]✗ Error exporting to JSON:[/red] {str(e)}")
                        return 1

                if args.output_csv:
                    try:
                        rows = result.to_csv_rows()
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

            else:
                # Video comparison benchmark mode
                console.print(f"[bold]Mode:[/bold] Pipeline Comparison")
                console.print(f"[bold]Video 1:[/bold] {video1.name}")
                console.print(f"[bold]Video 2:[/bold] {video2.name}")
                console.print(f"[bold]Pipelines:[/bold] {', '.join(presets)}")
                console.print(f"[bold]Threshold:[/bold] {args.threshold}%")
                console.print()

                ground_truth = None
                if args.ground_truth:
                    ground_truth = args.ground_truth == 'duplicate'

                result = service.compare_pipelines(
                    video1,
                    video2,
                    presets,
                    args.threshold,
                    ground_truth
                )

                # Display comparison results
                display_comparison_benchmark(console, result, args.profile_algorithms)

                # Export if requested
                if args.output_json:
                    try:
                        with open(args.output_json, 'w') as f:
                            json.dump(result.to_dict(), f, indent=2)
                        console.print()
                        console.print(f"[green]✓ Results exported to JSON:[/green] {args.output_json}")
                    except Exception as e:
                        console.print()
                        console.print(f"[red]✗ Error exporting to JSON:[/red] {str(e)}")
                        return 1

                if args.output_csv:
                    try:
                        # Create CSV rows from pipeline benchmarks
                        rows = []
                        for pb in result.pipeline_benchmarks:
                            rows.append({
                                'pipeline': pb.pipeline_name,
                                'time_ms': round(pb.total_time_ms, 2),
                                'time_seconds': round(pb.total_time_ms / 1000, 2),
                                'similarity': round(pb.similarity_score, 2),
                                'is_duplicate': pb.is_duplicate,
                                'memory_mb': round(pb.memory_peak_mb, 2),
                                'algorithms': len(pb.algorithm_benchmarks)
                            })

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
            return 0

        except Exception as e:
            console.print()
            console.print(f"[red]✗ Error during benchmark:[/red] {str(e)}")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return 1
