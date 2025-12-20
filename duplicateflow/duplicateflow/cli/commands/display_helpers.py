"""
Rich display helpers for CLI commands.

Functions for displaying comparison and detection results in beautiful terminal UI.
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from duplicateflow.core.models.comparison import ComparisonResult
from duplicateflow.core.models.detection import DetectionResult
from duplicateflow.core.models.benchmark import ComparisonBenchmark, TestSetBenchmark


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

def display_comparison_benchmark(
    console: Console,
    benchmark: ComparisonBenchmark,
    show_profiling: bool = False
) -> None:
    """
    Display multi-pipeline comparison benchmark.

    Args:
        console: Rich Console instance
        benchmark: ComparisonBenchmark to display
        show_profiling: Whether to show algorithm profiling

    Example:
        >>> from rich.console import Console
        >>> console = Console()
        >>> display_comparison_benchmark(console, benchmark, show_profiling=True)
    """
    # Summary panel
    fastest = benchmark.get_fastest_pipeline()

    summary = f"""[bold]Videos:[/bold] {benchmark.video1_path.name} vs {benchmark.video2_path.name}
[bold]Pipelines tested:[/bold] {len(benchmark.pipeline_benchmarks)}"""

    if fastest:
        summary += f"\n[bold]Fastest:[/bold] {fastest.pipeline_name} ({fastest.total_time_ms:.0f}ms)"

    if benchmark.ground_truth is not None:
        most_accurate = benchmark.get_most_accurate_pipeline()
        truth = "DUPLICATE" if benchmark.ground_truth else "NOT DUPLICATE"
        summary += f"\n\n[bold]Ground truth:[/bold] {truth}"
        if most_accurate:
            summary += f"\n[bold]Most accurate:[/bold] {most_accurate.pipeline_name}"

    console.print()
    console.print(Panel(summary, title="📊 Benchmark Summary", border_style="cyan"))
    console.print()

    # Speed ranking table
    table = Table(title="Pipeline Performance Comparison")
    table.add_column("Rank", justify="center", style="cyan")
    table.add_column("Pipeline", style="yellow")
    table.add_column("Time (ms)", justify="right")
    table.add_column("Time (s)", justify="right")
    table.add_column("Similarity", justify="right")
    table.add_column("Duplicate", justify="center")
    table.add_column("Memory (MB)", justify="right")
    table.add_column("Algorithms", justify="right")

    rankings = benchmark.rank_by_speed()
    for idx, (pipeline_name, time_ms) in enumerate(rankings, 1):
        pb = next(b for b in benchmark.pipeline_benchmarks if b.pipeline_name == pipeline_name)

        duplicate_icon = "✓" if pb.is_duplicate else "✗"
        duplicate_color = "green" if pb.is_duplicate else "yellow"

        table.add_row(
            f"#{idx}",
            pipeline_name,
            f"{time_ms:.0f}",
            f"{time_ms / 1000:.2f}",
            f"{pb.similarity_score:.1f}%",
            f"[{duplicate_color}]{duplicate_icon}[/{duplicate_color}]",
            f"{pb.memory_peak_mb:.1f}",
            str(len(pb.algorithm_benchmarks))
        )

    console.print(table)
    console.print()

    # Algorithm profiling if requested
    if show_profiling and benchmark.pipeline_benchmarks:
        for pb in benchmark.pipeline_benchmarks:
            console.print(f"[bold cyan]{pb.pipeline_name} - Algorithm Breakdown[/bold cyan]")

            algo_table = Table()
            algo_table.add_column("Algorithm", style="yellow")
            algo_table.add_column("Time (ms)", justify="right")
            algo_table.add_column("% of Total", justify="right")
            algo_table.add_column("Similarity", justify="right")
            algo_table.add_column("Frames", justify="right")

            time_breakdown = pb.get_time_breakdown()
            for algo_name, time_ms in time_breakdown.items():
                algo_bench = next(
                    (a for a in pb.algorithm_benchmarks if a.algorithm_name == algo_name),
                    None
                )
                if algo_bench:
                    percentage = (time_ms / pb.total_time_ms) * 100 if pb.total_time_ms > 0 else 0
                    algo_table.add_row(
                        algo_name,
                        f"{time_ms:.0f}",
                        f"{percentage:.1f}%",
                        f"{algo_bench.similarity:.1f}%",
                        str(algo_bench.frames_processed)
                    )

            console.print(algo_table)
            console.print()


def display_testset_benchmark(
    console: Console,
    benchmark: TestSetBenchmark
) -> None:
    """
    Display test set benchmark results.

    Args:
        console: Rich Console instance
        benchmark: TestSetBenchmark to display

    Example:
        >>> from rich.console import Console
        >>> console = Console()
        >>> display_testset_benchmark(console, benchmark)
    """
    metrics = benchmark.accuracy_metrics

    # Accuracy panel
    accuracy_panel = f"""[bold]Test Set:[/bold] {benchmark.test_set_name}
[bold]Pipeline:[/bold] {benchmark.pipeline_name}
[bold]Total Comparisons:[/bold] {benchmark.total_comparisons}

[bold cyan]Accuracy Metrics:[/bold cyan]
[bold]Accuracy:[/bold]  {metrics.accuracy * 100:.2f}%
[bold]Precision:[/bold] {metrics.precision * 100:.2f}%
[bold]Recall:[/bold]    {metrics.recall * 100:.2f}%
[bold]F1 Score:[/bold]  {metrics.f1_score * 100:.2f}%

[bold cyan]Performance:[/bold cyan]
[bold]Avg Time:[/bold]   {benchmark.avg_execution_time_ms:.0f}ms per comparison
[bold]Total Time:[/bold] {benchmark.total_time_seconds:.1f}s"""

    console.print()
    console.print(Panel(accuracy_panel, title="📈 Test Set Results", border_style="green"))
    console.print()

    # Confusion matrix
    cm_table = Table(title="Confusion Matrix")
    cm_table.add_column("", style="bold")
    cm_table.add_column("Predicted: Duplicate", justify="center")
    cm_table.add_column("Predicted: Not Duplicate", justify="center")

    cm_table.add_row(
        "Actual: Duplicate",
        f"[green]{metrics.true_positives}[/green] (TP)",
        f"[red]{metrics.false_negatives}[/red] (FN)"
    )
    cm_table.add_row(
        "Actual: Not Duplicate",
        f"[red]{metrics.false_positives}[/red] (FP)",
        f"[green]{metrics.true_negatives}[/green] (TN)"
    )

    console.print(cm_table)
    console.print()

    # Performance summary
    if benchmark.total_comparisons > 0:
        comp_per_sec = benchmark.total_comparisons / benchmark.total_time_seconds if benchmark.total_time_seconds > 0 else 0
        console.print(f"[dim]Speed: {comp_per_sec:.2f} comparisons/second[/dim]")
