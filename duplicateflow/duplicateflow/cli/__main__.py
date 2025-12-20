"""
CLI entry point for DuplicateFlow.

This module provides the main entry point for the command-line interface.
It can be run as: python -m duplicateflow.cli
"""

import sys
import argparse
from typing import Optional

from rich.console import Console

from duplicateflow.cli.commands import create_scan_parser, run_scan_command
from duplicateflow.cli.commands.compare_command import create_compare_parser, run_compare_command
from duplicateflow.cli.commands.find_command import create_find_parser, run_find_command


def create_main_parser() -> argparse.ArgumentParser:
    """
    Create the main argument parser with all subcommands.

    Returns:
        ArgumentParser with all commands configured
    """
    parser = argparse.ArgumentParser(
        prog='duplicateflow',
        description='DuplicateFlow - Find duplicate and similar videos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan for videos
  duplicateflow scan /path/to/videos

  # Find duplicates in a directory
  duplicateflow find /path/to/videos --recursive

  # Compare two videos
  duplicateflow compare video1.mp4 video2.mp4 --preset thorough

  # Export results
  duplicateflow find /videos --output-json duplicates.json

  # Get help for a command
  duplicateflow <command> --help

For more information, visit: https://github.com/yourusername/duplicateflow
        """
    )

    parser.add_argument(
        '--version',
        action='version',
        version='DuplicateFlow 0.2.0 (Phase 2 Complete - Duplicate Detection)'
    )

    # Create subcommands
    subparsers = parser.add_subparsers(
        dest='command',
        title='Available commands',
        description='Use "duplicateflow <command> --help" for command-specific help',
        required=False
    )

    # Add commands
    create_scan_parser(subparsers)
    create_compare_parser(subparsers)
    create_find_parser(subparsers)

    # Future commands:
    # create_benchmark_parser(subparsers)

    return parser


def main(argv: Optional[list] = None) -> int:
    """
    Main CLI entry point.

    Args:
        argv: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_main_parser()
    args = parser.parse_args(argv)

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return 0

    # Route to appropriate command
    if args.command == 'scan':
        return run_scan_command(args)
    elif args.command == 'compare':
        return run_compare_command(args)
    elif args.command == 'find':
        return run_find_command(args)

    # Future commands:
    # elif args.command == 'benchmark':
    #     return run_benchmark_command(args)

    # Unknown command (should not happen due to argparse validation)
    console = Console()
    console.print(f"[red]Error:[/red] Unknown command: {args.command}")
    return 1


if __name__ == '__main__':
    sys.exit(main())
