"""
CLI scan command for DuplicateFlow.

This module provides the 'scan' command that discovers video files
in directories using ScanService with Rich progress reporting.
"""

import sys
from pathlib import Path
from typing import Optional
import argparse

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from duplicateflow.core.services import ScanService
from duplicateflow.core.models.scan import VideoFormat
from duplicateflow.cli.adapters import RichProgressReporter, RichUIAdapter


def create_scan_parser(subparsers) -> argparse.ArgumentParser:
    """
    Create argument parser for scan command.

    Args:
        subparsers: Subparser from argparse

    Returns:
        ArgumentParser for scan command
    """
    parser = subparsers.add_parser(
        'scan',
        help='Scan directory for video files',
        description='Discover video files in a directory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan current directory
  duplicateflow scan .

  # Scan specific directory recursively
  duplicateflow scan /path/to/videos

  # Scan without recursion
  duplicateflow scan /path/to/videos --no-recursive

  # Filter by formats
  duplicateflow scan /path/to/videos --formats mp4 mkv

  # Filter by size
  duplicateflow scan /path/to/videos --min-size 100 --max-size 5000

  # Export results to JSON
  duplicateflow scan /path/to/videos --output-json results.json

  # Export results to CSV
  duplicateflow scan /path/to/videos --output-csv results.csv

  # Export to both formats
  duplicateflow scan /path/to/videos --output-json results.json --output-csv results.csv
        """
    )

    # Positional arguments
    parser.add_argument(
        'directory',
        type=str,
        help='Directory to scan for videos'
    )

    # Optional arguments
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        default=True,
        help='Scan subdirectories recursively (default: True)'
    )

    parser.add_argument(
        '--no-recursive',
        action='store_false',
        dest='recursive',
        help='Do not scan subdirectories'
    )

    parser.add_argument(
        '--follow-symlinks',
        action='store_true',
        default=False,
        help='Follow symbolic links (default: False)'
    )

    parser.add_argument(
        '--formats',
        nargs='+',
        type=str,
        metavar='FORMAT',
        help='Filter by video formats (e.g., mp4 mkv avi)'
    )

    parser.add_argument(
        '--min-size',
        type=float,
        metavar='MB',
        help='Minimum file size in MB'
    )

    parser.add_argument(
        '--max-size',
        type=float,
        metavar='MB',
        help='Maximum file size in MB'
    )

    parser.add_argument(
        '--show-stats',
        action='store_true',
        default=True,
        help='Show statistics after scan (default: True)'
    )

    parser.add_argument(
        '--no-stats',
        action='store_false',
        dest='show_stats',
        help='Do not show statistics'
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

    return parser


def validate_arguments(args, console: Console) -> bool:
    """
    Validate command line arguments.

    Args:
        args: Parsed arguments
        console: Rich console for error messages

    Returns:
        True if valid, False otherwise
    """
    # Validate directory exists
    directory = Path(args.directory)
    if not directory.exists():
        console.print(
            f"[red]✗ Error:[/red] Directory does not exist: {args.directory}",
            style="bold"
        )
        console.print("\n[yellow]Suggestion:[/yellow] Check the path and try again")
        return False

    if not directory.is_dir():
        console.print(
            f"[red]✗ Error:[/red] Not a directory: {args.directory}",
            style="bold"
        )
        console.print("\n[yellow]Suggestion:[/yellow] Provide a directory path, not a file")
        return False

    # Validate size arguments
    if args.min_size is not None and args.min_size < 0:
        console.print(
            f"[red]✗ Error:[/red] Minimum size cannot be negative: {args.min_size}",
            style="bold"
        )
        return False

    if args.max_size is not None and args.max_size < 0:
        console.print(
            f"[red]✗ Error:[/red] Maximum size cannot be negative: {args.max_size}",
            style="bold"
        )
        return False

    if args.min_size is not None and args.max_size is not None:
        if args.min_size > args.max_size:
            console.print(
                f"[red]✗ Error:[/red] Minimum size ({args.min_size} MB) "
                f"cannot be greater than maximum size ({args.max_size} MB)",
                style="bold"
            )
            return False

    # Validate formats
    if args.formats:
        valid_formats = {fmt.value for fmt in VideoFormat if fmt != VideoFormat.UNKNOWN}
        invalid_formats = [fmt for fmt in args.formats if fmt.lower() not in valid_formats]

        if invalid_formats:
            console.print(
                f"[red]✗ Error:[/red] Invalid video formats: {', '.join(invalid_formats)}",
                style="bold"
            )
            console.print(
                f"\n[yellow]Valid formats:[/yellow] {', '.join(sorted(valid_formats))}"
            )
            return False

    return True


def display_results_table(console: Console, service: ScanService, result, args) -> None:
    """
    Display scan results in a Rich table.

    Args:
        console: Rich console
        service: ScanService instance
        result: ScanResult object
        args: Command arguments
    """
    # Apply filters if specified
    videos = result.videos

    if args.formats:
        formats = [VideoFormat.from_extension(fmt) for fmt in args.formats]
        videos = service.filter_by_format(result, formats)

    if args.min_size is not None or args.max_size is not None:
        videos = service.filter_by_size(result, args.min_size, args.max_size)

    # Create table
    table = Table(title=f"Videos Found: {len(videos)}", show_header=True, header_style="bold cyan")
    table.add_column("File", style="white", no_wrap=False)
    table.add_column("Size", justify="right", style="cyan")
    table.add_column("Format", justify="center", style="magenta")

    # Add rows (limit to first 20 for display)
    display_limit = 20
    for video in videos[:display_limit]:
        table.add_row(
            video.filename,
            f"{video.size_mb:.2f} MB",
            video.format.value.upper()
        )

    if len(videos) > display_limit:
        table.add_row(
            f"... and {len(videos) - display_limit} more",
            "",
            "",
            style="dim"
        )

    console.print(table)


def display_statistics(console: Console, service: ScanService, result) -> None:
    """
    Display statistics in a Rich panel.

    Args:
        console: Rich console
        service: ScanService instance
        result: ScanResult object
    """
    stats = service.get_statistics(result)

    # Format statistics
    stats_text = f"""
[cyan]Total Videos:[/cyan] {stats['total_videos']}
[cyan]Total Size:[/cyan] {stats['total_size_gb']:.2f} GB ({stats['total_size_mb']:.2f} MB)
[cyan]Directories Scanned:[/cyan] {stats['directories_scanned']}
[cyan]Files Checked:[/cyan] {stats['files_checked']}
[cyan]Scan Duration:[/cyan] {stats['scan_duration_seconds']:.2f}s
[cyan]Errors:[/cyan] {stats['errors']}

[yellow]By Format:[/yellow]
"""

    # Add format counts
    for format_name, count in sorted(stats['format_counts'].items()):
        stats_text += f"  {format_name.upper()}: {count}\n"

    panel = Panel(
        stats_text.strip(),
        title="[bold green]Scan Statistics[/bold green]",
        border_style="green"
    )

    console.print(panel)


def export_results(result, args, console: Console) -> None:
    """
    Export scan results to JSON and/or CSV files.

    Args:
        result: ScanResult object
        args: Command arguments
        console: Rich console for messages
    """
    # Export to JSON
    if args.output_json:
        try:
            json_content = result.to_json(indent=2)
            with open(args.output_json, 'w') as f:
                f.write(json_content)
            console.print(
                f"[green]✓ Results exported to JSON:[/green] {args.output_json}"
            )
        except Exception as e:
            console.print(
                f"[red]✗ Error exporting to JSON:[/red] {str(e)}",
                style="bold"
            )

    # Export to CSV
    if args.output_csv:
        try:
            import csv
            rows = result.to_csv_rows()
            if rows:
                with open(args.output_csv, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
                console.print(
                    f"[green]✓ Results exported to CSV:[/green] {args.output_csv}"
                )
            else:
                console.print(
                    "[yellow]⚠ Warning:[/yellow] No videos to export to CSV"
                )
        except Exception as e:
            console.print(
                f"[red]✗ Error exporting to CSV:[/red] {str(e)}",
                style="bold"
            )


def run_scan_command(args) -> int:
    """
    Execute the scan command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    console = Console()

    # Validate arguments
    if not validate_arguments(args, console):
        return 1

    # Display welcome message
    console.print(
        Panel(
            f"[bold cyan]Scanning:[/bold cyan] {args.directory}\n"
            f"[dim]Recursive: {args.recursive} | Follow symlinks: {args.follow_symlinks}[/dim]",
            title="[bold]DuplicateFlow Scanner[/bold]",
            border_style="cyan"
        )
    )

    # Create service with Rich adapters
    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)
        service = ScanService(progress=progress, ui=ui)

        try:
            # Run scan
            result = service.scan_directory(
                Path(args.directory),
                recursive=args.recursive,
                follow_symlinks=args.follow_symlinks
            )

            # Display results
            console.print()  # Empty line
            display_results_table(console, service, result, args)

            # Display statistics
            if args.show_stats:
                console.print()  # Empty line
                display_statistics(console, service, result)

            # Display errors if any
            if result.has_errors:
                console.print()  # Empty line
                console.print(
                    f"[yellow]⚠ Warning:[/yellow] {len(result.errors)} errors occurred during scan",
                    style="bold"
                )
                for error in result.errors[:5]:  # Show first 5 errors
                    console.print(f"  [dim]{error}[/dim]")
                if len(result.errors) > 5:
                    console.print(f"  [dim]... and {len(result.errors) - 5} more errors[/dim]")

            # Export results if requested
            if args.output_json or args.output_csv:
                console.print()  # Empty line
                export_results(result, args, console)

            return 0

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Scan cancelled by user[/yellow]")
            return 130  # Standard exit code for SIGINT

        except Exception as e:
            console.print(f"\n[red]✗ Error during scan:[/red] {str(e)}", style="bold")
            return 1
