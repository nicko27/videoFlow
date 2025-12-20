"""
Rich display helpers for CLI commands.

Functions for displaying comparison and detection results in beautiful terminal UI.
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from duplicateflow.core.models.comparison import ComparisonResult
from duplicateflow.core.models.detection import DetectionResult


def display_comparison_result(
    console: Console,
    result: ComparisonResult,
    show_details: bool = False
) -> None:
    """
    Display comparison result with Rich formatting.

    Args:
        console: Rich Console instance
        result: ComparisonResult to display
        show_details: Whether to show algorithm details

    Example:
        >>> from rich.console import Console
        >>> console = Console()
        >>> display_comparison_result(console, result, show_details=True)
    """
    # Main result panel
    match_symbol = "✓" if result.is_duplicate else "✗"
    match_text = "DUPLICATE" if result.is_duplicate else "NOT DUPLICATE"
    match_color = "green" if result.is_duplicate else "yellow"

    panel_content = f"""[bold]Video 1:[/bold] {result.video1_path.name}
[bold]Video 2:[/bold] {result.video2_path.name}

[bold]Similarity:[/bold] {result.similarity_score:.2f}%
[bold]Match:[/bold] [{match_color}]{match_symbol} {match_text}[/{match_color}]

[bold]Pipeline:[/bold] {result.pipeline_name}
[bold]Time:[/bold] {result.execution_time_ms:.0f}ms ({result.execution_time_ms / 1000:.2f}s)
[bold]Algorithms:[/bold] {len(result.algorithm_results)} executed"""

    console.print()
    console.print(Panel(
        panel_content,
        title="📊 Comparison Result",
        border_style="cyan",
        expand=False
    ))

    # Algorithm details table (if requested)
    if show_details and result.algorithm_results:
        console.print()

        table = Table(title="Algorithm Details", show_header=True)
        table.add_column("Algorithm", style="cyan", no_wrap=True)
        table.add_column("Similarity", justify="right", style="magenta")
        table.add_column("Weight", justify="right", style="blue")
        table.add_column("Accepted", justify="center", style="green")
        table.add_column("Weighted", justify="right", style="yellow")

        for algo in result.algorithm_results:
            accepted_symbol = "✓" if algo.accepted else "✗"
            accepted_style = "green" if algo.accepted else "red"
            weighted_score = algo.similarity * algo.weight

            table.add_row(
                algo.algorithm_name,
                f"{algo.similarity:.2f}%",
                f"{algo.weight:.3f}",
                f"[{accepted_style}]{accepted_symbol}[/{accepted_style}]",
                f"{weighted_score:.2f}"
            )

        console.print(table)

    # Execution summary
    if show_details:
        summary = result.get_execution_summary()
        console.print()
        console.print(f"[dim]Algorithms used: {summary['algorithms_used']}[/dim]")
        console.print(f"[dim]Algorithms accepted: {summary['algorithms_accepted']}[/dim]")
        console.print(f"[dim]Average similarity: {summary['avg_similarity']:.2f}%[/dim]")


def display_detection_result(
    console: Console,
    result: DetectionResult
) -> None:
    """
    Display detection result with Rich formatting.

    Args:
        console: Rich Console instance
        result: DetectionResult to display

    Example:
        >>> from rich.console import Console
        >>> console = Console()
        >>> display_detection_result(console, result)
    """
    # Statistics panel
    stats = result.get_statistics()

    panel_content = f"""[bold]Videos Scanned:[/bold] {result.total_videos_scanned}
[bold]Comparisons:[/bold] {result.total_comparisons}

[bold]Duplicate Groups:[/bold] {len(result.duplicate_groups)}
[bold]Duplicates Found:[/bold] {result.duplicates_found}
[bold]Duplicate Percentage:[/bold] {stats['duplicate_percentage']:.1f}%

[bold]Space Reclaimable:[/bold] {result.space_reclaimable_mb:.2f} MB ({result.space_reclaimable_mb / 1024:.2f} GB)

[bold]Pipeline:[/bold] {result.pipeline_used}
[bold]Time:[/bold] {result.execution_time_seconds:.1f}s ({result.execution_time_seconds / 60:.1f}m)
[bold]Speed:[/bold] {stats['comparisons_per_second']:.1f} comp/s"""

    console.print()
    console.print(Panel(
        panel_content,
        title="🔍 Detection Summary",
        border_style="green",
        expand=False
    ))

    # Duplicate groups table
    if result.duplicate_groups:
        console.print()

        table = Table(title="Duplicate Groups", show_header=True)
        table.add_column("Group", style="cyan", justify="center")
        table.add_column("Videos", justify="right", style="magenta")
        table.add_column("Avg Similarity", justify="right", style="green")
        table.add_column("Total Size", justify="right", style="yellow")
        table.add_column("Representative", style="blue", no_wrap=True)

        for idx, group in enumerate(result.duplicate_groups, 1):
            table.add_row(
                f"#{idx}",
                str(len(group.videos)),
                f"{group.avg_similarity:.1f}%",
                f"{group.total_size_mb:.1f} MB",
                group.representative.name
            )

        console.print(table)

        # Show video names in each group
        console.print()
        console.print("[bold cyan]Group Details:[/bold cyan]")
        for idx, group in enumerate(result.duplicate_groups, 1):
            console.print(f"\n[yellow]Group #{idx}:[/yellow]")
            for video in group.videos:
                is_rep = " [green](representative)[/green]" if video == group.representative else ""
                console.print(f"  • {video.name}{is_rep}")

    else:
        console.print()
        console.print("[green]✓ No duplicates found![/green]")

    # Statistics
    console.print()
    console.print(f"[dim]Average group size: {stats['avg_group_size']:.1f} videos[/dim]")
    console.print(f"[dim]Largest group: {stats['largest_group_size']} videos[/dim]")


def display_benchmark_result(
    console: Console,
    results: dict,
    video1_name: str,
    video2_name: str
) -> None:
    """
    Display benchmark comparison of multiple presets.

    Args:
        console: Rich Console instance
        results: Dictionary mapping preset name to comparison result
        video1_name: Name of first video
        video2_name: Name of second video

    Example:
        >>> results = {'fast': result1, 'balanced': result2}
        >>> display_benchmark_result(console, results, "v1.mp4", "v2.mp4")
    """
    console.print()
    console.print(Panel(
        f"[bold]Video 1:[/bold] {video1_name}\n[bold]Video 2:[/bold] {video2_name}",
        title="📊 Benchmark Comparison",
        border_style="cyan"
    ))

    console.print()
    table = Table(title="Pipeline Presets Comparison", show_header=True)
    table.add_column("Preset", style="cyan", no_wrap=True)
    table.add_column("Similarity", justify="right", style="magenta")
    table.add_column("Match", justify="center", style="green")
    table.add_column("Time (ms)", justify="right", style="yellow")
    table.add_column("Algorithms", justify="right", style="blue")

    for preset_name, result in results.items():
        match_symbol = "✓" if result.is_duplicate else "✗"
        match_style = "green" if result.is_duplicate else "red"

        table.add_row(
            preset_name,
            f"{result.similarity_score:.2f}%",
            f"[{match_style}]{match_symbol}[/{match_style}]",
            f"{result.execution_time_ms:.0f}",
            str(len(result.algorithm_results))
        )

    console.print(table)

    # Summary
    console.print()
    fastest = min(results.items(), key=lambda x: x[1].execution_time_ms)
    most_accurate = max(results.items(), key=lambda x: x[1].similarity_score)

    console.print(f"[green]⚡ Fastest:[/green] {fastest[0]} ({fastest[1].execution_time_ms:.0f}ms)")
    console.print(f"[green]🎯 Most Similar:[/green] {most_accurate[0]} ({most_accurate[1].similarity_score:.2f}%)")
