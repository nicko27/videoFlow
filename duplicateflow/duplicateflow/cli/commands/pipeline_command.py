"""
Pipeline management command for DuplicateFlow.

Usage:
    duplicateflow pipeline list
    duplicateflow pipeline show my_preset
    duplicateflow pipeline create my_preset --algorithms frame_hash ssim
    duplicateflow pipeline export my_preset output.yaml
    duplicateflow pipeline import custom.yaml
    duplicateflow pipeline validate my_preset
    duplicateflow pipeline delete my_preset
"""

import argparse
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from duplicateflow.cli.adapters import RichProgressReporter, RichUIAdapter
from duplicateflow.core.services.pipeline_management_service import PipelineManagementService
from duplicateflow.core.models.pipeline_config import AlgorithmConfig


def create_pipeline_parser(subparsers) -> argparse.ArgumentParser:
    """
    Create argument parser for pipeline command.

    Args:
        subparsers: Subparsers object from main parser

    Returns:
        ArgumentParser for pipeline command
    """
    parser = subparsers.add_parser(
        'pipeline',
        help='Manage custom pipeline configurations',
        description='Create, manage, and customize detection pipelines',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all saved pipelines
  duplicateflow pipeline list

  # Show details of a pipeline
  duplicateflow pipeline show my_preset

  # Create a new pipeline
  duplicateflow pipeline create my_preset \\
    --description "Custom fast preset" \\
    --algorithms frame_hash ssim \\
    --weights 0.6 0.4 \\
    --thresholds 70 75 \\
    --global-threshold 72

  # Export pipeline to file
  duplicateflow pipeline export my_preset output.yaml

  # Import pipeline from file
  duplicateflow pipeline import custom.yaml --name imported_preset

  # Validate pipeline configuration
  duplicateflow pipeline validate my_preset

  # Delete a pipeline
  duplicateflow pipeline delete my_preset
        """
    )

    # Create subcommands
    subparsers_pipeline = parser.add_subparsers(
        dest='subcommand',
        title='Pipeline commands',
        description='Available pipeline management commands',
        required=True
    )

    # List command
    parser_list = subparsers_pipeline.add_parser(
        'list',
        help='List all saved pipelines'
    )
    parser_list.set_defaults(func=run_list_command)

    # Show command
    parser_show = subparsers_pipeline.add_parser(
        'show',
        help='Show pipeline details'
    )
    parser_show.add_argument('name', type=str, help='Pipeline name')
    parser_show.add_argument('--format', choices=['yaml', 'json'], default='yaml',
                            help='Display format (default: yaml)')
    parser_show.set_defaults(func=run_show_command)

    # Create command
    parser_create = subparsers_pipeline.add_parser(
        'create',
        help='Create a new pipeline'
    )
    parser_create.add_argument('name', type=str, help='Pipeline name')
    parser_create.add_argument('--description', type=str, required=True,
                              help='Pipeline description')
    parser_create.add_argument('--algorithms', nargs='+', required=True,
                              help='Algorithm names (space-separated)')
    parser_create.add_argument('--weights', nargs='+', type=float,
                              help='Algorithm weights (default: equal weights)')
    parser_create.add_argument('--thresholds', nargs='+', type=float,
                              help='Algorithm thresholds (default: 70.0 for all)')
    parser_create.add_argument('--global-threshold', type=float, default=70.0,
                              help='Global similarity threshold (default: 70.0)')
    parser_create.add_argument('--format', choices=['yaml', 'json'], default='yaml',
                              help='Save format (default: yaml)')
    parser_create.add_argument('--no-normalize', action='store_true',
                              help='Skip weight normalization')
    parser_create.set_defaults(func=run_create_command)

    # Export command
    parser_export = subparsers_pipeline.add_parser(
        'export',
        help='Export pipeline to file'
    )
    parser_export.add_argument('name', type=str, help='Pipeline name')
    parser_export.add_argument('destination', type=str, help='Output file path')
    parser_export.add_argument('--format', choices=['yaml', 'json'], default='yaml',
                               help='Export format (default: yaml)')
    parser_export.set_defaults(func=run_export_command)

    # Import command
    parser_import = subparsers_pipeline.add_parser(
        'import',
        help='Import pipeline from file'
    )
    parser_import.add_argument('source', type=str, help='Source file path')
    parser_import.add_argument('--name', type=str, help='New name for imported pipeline')
    parser_import.add_argument('--overwrite', action='store_true',
                              help='Overwrite if pipeline already exists')
    parser_import.set_defaults(func=run_import_command)

    # Validate command
    parser_validate = subparsers_pipeline.add_parser(
        'validate',
        help='Validate pipeline configuration'
    )
    parser_validate.add_argument('name', type=str, help='Pipeline name')
    parser_validate.set_defaults(func=run_validate_command)

    # Delete command
    parser_delete = subparsers_pipeline.add_parser(
        'delete',
        help='Delete a pipeline'
    )
    parser_delete.add_argument('name', type=str, help='Pipeline name')
    parser_delete.add_argument('--yes', action='store_true',
                              help='Skip confirmation prompt')
    parser_delete.set_defaults(func=run_delete_command)

    return parser


def run_pipeline_command(args) -> int:
    """
    Main entry point for pipeline command (delegates to subcommands).

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # This is handled by subcommand dispatching
    return args.func(args)


def run_list_command(args) -> int:
    """List all saved pipelines."""
    console = Console()

    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)
        service = PipelineManagementService(progress, ui)

        try:
            pipelines = service.list_pipelines()

            if not pipelines:
                console.print("\n[yellow]No pipelines found.[/yellow]")
                console.print(f"[dim]Pipelines directory: {service.pipelines_dir}[/dim]")
                return 0

            # Create table
            table = Table(title=f"Saved Pipelines ({len(pipelines)})")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Description", style="white")
            table.add_column("Algorithms", justify="center")
            table.add_column("Format", justify="center")
            table.add_column("Created", style="dim")

            for pipeline in pipelines:
                table.add_row(
                    pipeline['name'],
                    pipeline['description'][:50] + "..." if len(pipeline['description']) > 50 else pipeline['description'],
                    str(pipeline['algorithms_count']),
                    pipeline['format'],
                    pipeline['created_at'].split('T')[0] if 'T' in pipeline['created_at'] else pipeline['created_at']
                )

            console.print()
            console.print(table)
            console.print()
            console.print(f"[dim]Pipelines directory: {service.pipelines_dir}[/dim]")

            return 0

        except Exception as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            return 1


def run_show_command(args) -> int:
    """Show pipeline details."""
    console = Console()

    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)
        service = PipelineManagementService(progress, ui)

        try:
            info = service.get_pipeline_info(args.name)

            # Display basic info
            panel_content = f"""
[bold]Name:[/bold] {info['name']}
[bold]Description:[/bold] {info['description']}
[bold]Global Threshold:[/bold] {info['global_threshold']}%
[bold]Algorithms:[/bold] {info['algorithms_enabled']} enabled / {info['algorithms_total']} total
[bold]Total Weight:[/bold] {info['total_weight']:.3f} {'✓' if info['weight_normalized'] else '✗ (not normalized)'}
"""
            console.print()
            console.print(Panel(panel_content, title="Pipeline Info", border_style="cyan"))

            # Algorithms table
            if info['algorithms']:
                table = Table(title="Algorithms")
                table.add_column("Algorithm", style="cyan")
                table.add_column("Weight", justify="right")
                table.add_column("Threshold", justify="right")
                table.add_column("Enabled", justify="center")
                table.add_column("Params", justify="center")

                for algo in info['algorithms']:
                    table.add_row(
                        algo['name'],
                        f"{algo['weight']:.3f}",
                        f"{algo['threshold']:.1f}%",
                        "✓" if algo['enabled'] else "✗",
                        str(algo['params_count'])
                    )

                console.print()
                console.print(table)

            # Validation status
            if info['validation_errors']:
                console.print()
                console.print("[red]Validation Errors:[/red]")
                for error in info['validation_errors']:
                    console.print(f"  [red]✗[/red] {error}")
            else:
                console.print()
                console.print("[green]✓ Pipeline is valid[/green]")

            # Show configuration
            config = service.load_pipeline(args.name)
            console.print()
            console.print("[bold]Configuration:[/bold]")

            if args.format == 'yaml':
                syntax = Syntax(config.to_yaml(), "yaml", theme="monokai", line_numbers=True)
            else:
                syntax = Syntax(config.to_json(), "json", theme="monokai", line_numbers=True)

            console.print(syntax)

            return 0

        except FileNotFoundError as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            return 1
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return 1


def run_create_command(args) -> int:
    """Create a new pipeline."""
    console = Console()

    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)
        service = PipelineManagementService(progress, ui)

        try:
            # Parse algorithms
            num_algos = len(args.algorithms)

            # Parse weights
            if args.weights:
                if len(args.weights) != num_algos:
                    console.print(f"[red]✗ Error:[/red] Number of weights ({len(args.weights)}) must match number of algorithms ({num_algos})")
                    return 1
                weights = args.weights
            else:
                # Equal weights
                weights = [1.0 / num_algos] * num_algos

            # Parse thresholds
            if args.thresholds:
                if len(args.thresholds) != num_algos:
                    console.print(f"[red]✗ Error:[/red] Number of thresholds ({len(args.thresholds)}) must match number of algorithms ({num_algos})")
                    return 1
                thresholds = args.thresholds
            else:
                # Default threshold
                thresholds = [70.0] * num_algos

            # Create algorithm configs
            algorithms = [
                AlgorithmConfig(
                    name=name,
                    weight=weight,
                    threshold=threshold,
                    enabled=True
                )
                for name, weight, threshold in zip(args.algorithms, weights, thresholds)
            ]

            # Create pipeline
            console.print()
            config = service.create_pipeline(
                name=args.name,
                description=args.description,
                algorithms=algorithms,
                global_threshold=args.global_threshold,
                auto_normalize=not args.no_normalize
            )

            # Save pipeline
            path = service.save_pipeline(config, format=args.format, overwrite=False)

            console.print()
            console.print(f"[green]✓ Pipeline created:[/green] {args.name}")
            console.print(f"[dim]Saved to: {path}[/dim]")

            # Show summary
            table = Table(title="Algorithm Summary")
            table.add_column("Algorithm", style="cyan")
            table.add_column("Weight", justify="right")
            table.add_column("Threshold", justify="right")

            for algo in config.algorithms:
                table.add_row(
                    algo.name,
                    f"{algo.weight:.3f}",
                    f"{algo.threshold:.1f}%"
                )

            console.print()
            console.print(table)

            return 0

        except (ValueError, FileExistsError) as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            return 1
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return 1


def run_export_command(args) -> int:
    """Export pipeline to file."""
    console = Console()

    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)
        service = PipelineManagementService(progress, ui)

        try:
            destination = Path(args.destination)

            console.print()
            path = service.export_pipeline(
                args.name,
                destination,
                format=args.format
            )

            console.print()
            console.print(f"[green]✓ Pipeline exported:[/green] {path}")

            return 0

        except FileNotFoundError as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            return 1
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return 1


def run_import_command(args) -> int:
    """Import pipeline from file."""
    console = Console()

    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)
        service = PipelineManagementService(progress, ui)

        try:
            source = Path(args.source)

            console.print()
            config = service.import_pipeline(
                source,
                new_name=args.name,
                overwrite=args.overwrite
            )

            console.print()
            console.print(f"[green]✓ Pipeline imported:[/green] {config.name}")
            console.print(f"[dim]Algorithms: {len(config.get_enabled_algorithms())}[/dim]")

            return 0

        except (FileNotFoundError, FileExistsError, ValueError) as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            return 1
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return 1


def run_validate_command(args) -> int:
    """Validate pipeline configuration."""
    console = Console()

    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)
        service = PipelineManagementService(progress, ui)

        try:
            console.print()
            config = service.load_pipeline(args.name)
            errors = service.validate_pipeline(config)

            if not errors:
                console.print()
                console.print(f"[green]✓ Pipeline '{args.name}' is valid[/green]")

                # Show summary
                enabled = config.get_enabled_algorithms()
                total_weight = config.get_total_weight()

                console.print(f"  [dim]Algorithms: {len(enabled)} enabled[/dim]")
                console.print(f"  [dim]Total Weight: {total_weight:.3f}[/dim]")
                console.print(f"  [dim]Global Threshold: {config.global_threshold}%[/dim]")

                return 0
            else:
                console.print()
                console.print(f"[red]✗ Pipeline '{args.name}' has validation errors:[/red]")
                for error in errors:
                    console.print(f"  [red]✗[/red] {error}")

                return 1

        except FileNotFoundError as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            return 1
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return 1


def run_delete_command(args) -> int:
    """Delete a pipeline."""
    console = Console()

    # Confirmation prompt
    if not args.yes:
        console.print(f"\n[yellow]Warning:[/yellow] This will permanently delete pipeline '{args.name}'")
        response = input("Are you sure? (yes/no): ").strip().lower()
        if response not in ('yes', 'y'):
            console.print("[dim]Cancelled[/dim]")
            return 0

    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)
        service = PipelineManagementService(progress, ui)

        try:
            console.print()
            service.delete_pipeline(args.name)

            console.print()
            console.print(f"[green]✓ Pipeline deleted:[/green] {args.name}")

            return 0

        except FileNotFoundError as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            return 1
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/red] {str(e)}")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return 1
