#!/usr/bin/env python3
"""
CLI pour lancer un pipeline DuplicateFlow sur un testset avec cache de features.

Workflow en 2 phases:
1. Extraction : Pré-calcule et met en cache toutes les features
2. Comparaison : Compare rapidement en utilisant le cache

Usage:
    python run_testset.py --testset default --pipeline audioshazam
    python run_testset.py --testset default --pipeline balanced --limit 10
    python run_testset.py --compare audioshazam,balanced,staged_test
    python run_testset.py --interactive
    python run_testset.py --list-testsets
    python run_testset.py --list-pipelines
    python run_testset.py --resume checkpoint_default_audioshazam.json
"""

import argparse
import sys
import json
import time
import threading
import termios
import tty
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Rich imports
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    MofNCompleteColumn
)
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.tree import Tree
from rich import box
from rich.text import Text
from rich.align import Align

console = Console()


def fix_terminal_mode():
    """Force terminal into cooked mode to handle Enter key properly."""
    try:
        if sys.stdin.isatty():
            fd = sys.stdin.fileno()
            # Get current settings
            old_settings = termios.tcgetattr(fd)
            # Make a copy
            new_settings = termios.tcgetattr(fd)
            # Enable canonical mode (ICANON) and echo (ECHO)
            new_settings[3] |= termios.ICANON | termios.ECHO
            # Apply new settings
            termios.tcsetattr(fd, termios.TCSANOW, new_settings)
            return old_settings
    except Exception as e:
        console.print(f"[yellow]Note: Could not configure terminal: {e}[/yellow]")
    return None


def json_encoder(obj):
    """Custom JSON encoder for non-serializable types."""
    if isinstance(obj, (bool, int, float, str, type(None))):
        return obj
    if isinstance(obj, dict):
        return {k: json_encoder(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_encoder(item) for item in obj]
    # For any other type, try to convert to string
    return str(obj)


def safe_int_prompt(prompt: str, default: int) -> int:
    """Safe integer prompt that works with terminal issues."""
    while True:
        try:
            # Force flush and use raw input
            sys.stdout.write(f"\n{prompt} [{default}]: ")
            sys.stdout.flush()

            # Read directly from stdin
            line = sys.stdin.readline()
            if not line or line == '\n':
                return default

            value = line.strip()
            if not value:
                return default
            return int(value)
        except ValueError:
            sys.stdout.write("Valeur invalide, veuillez entrer un nombre\n")
            sys.stdout.flush()
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write("\n")
            sys.stdout.flush()
            return default

def safe_confirm(prompt: str, default: bool) -> bool:
    """Safe yes/no prompt that works with terminal issues."""
    default_str = "Y/n" if default else "y/N"
    while True:
        try:
            # Force flush and use raw input
            sys.stdout.write(f"\n{prompt} [{default_str}]: ")
            sys.stdout.flush()

            # Read directly from stdin
            line = sys.stdin.readline()
            if not line or line == '\n':
                return default

            value = line.strip().lower()
            if not value:
                return default
            if value in ('y', 'yes', 'o', 'oui'):
                return True
            if value in ('n', 'no', 'non'):
                return False
            sys.stdout.write("Réponse invalide, utilisez y/n\n")
            sys.stdout.flush()
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write("\n")
            sys.stdout.flush()
            return default

def safe_text_prompt(prompt: str, default: str = "") -> str:
    """Safe text prompt that works with terminal issues."""
    try:
        # Force flush and use raw input
        if default:
            sys.stdout.write(f"\n{prompt} [{default}]: ")
        else:
            sys.stdout.write(f"\n{prompt}: ")
        sys.stdout.flush()

        # Read directly from stdin
        line = sys.stdin.readline()
        if not line or line == '\n':
            return default

        value = line.strip()
        return value if value else default
    except (EOFError, KeyboardInterrupt):
        sys.stdout.write("\n")
        sys.stdout.flush()
        return default

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Add duplicateflow to path
duplicateflow_path = Path(__file__).parent / "duplicateflow"
if duplicateflow_path.exists():
    sys.path.insert(0, str(duplicateflow_path))

from src.core.logger import Logger
from src.plugins.duplicate_finder.database_manager import VideoDatabase
from src.plugins.duplicate_finder.services.test_set_manager import TestSetManager
from src.plugins.duplicate_finder.orchestration.pipeline_manager import PipelineManager

# Import DuplicateFlow
from duplicateflow.storage import StorageManager
from duplicateflow.core import get_algorithm
import duplicateflow.algorithms

logger = Logger.get_logger('TestSetCLI')

# Use the ROOT database (same as GUI)
ROOT_DB_PATH = str(Path(__file__).parent / "video_duplicates.db")

# Checkpoint directory
CHECKPOINT_DIR = Path(__file__).parent / ".checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)

# Benchmark results directory
RESULTS_DIR = Path(__file__).parent / "benchmark_results"
RESULTS_DIR.mkdir(exist_ok=True)


class BenchmarkState:
    """Thread-safe benchmark state for live dashboard."""

    def __init__(self, total_pairs: int, total_videos: int, total_algorithms: int):
        self.total_pairs = total_pairs
        self.total_videos = total_videos
        self.total_algorithms = total_algorithms

        self.current_phase = "Initialization"
        self.current_pair = 0
        self.current_video = ""
        self.current_algorithm = ""
        self.current_score = 0.0
        self.current_result = ""
        self.current_classification = ""

        # Metrics
        self.tp = 0
        self.fp = 0
        self.tn = 0
        self.fn = 0
        self.errors = 0

        # Timing
        self.start_time = time.time()
        self.pair_times = []

        # Extraction tracking
        self.extracted_count = 0
        self.cached_count = 0

        self._lock = threading.Lock()

    def update(self, **kwargs):
        """Thread-safe update of state."""
        with self._lock:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def increment_metric(self, classification: str):
        """Thread-safe increment of classification metric."""
        with self._lock:
            if classification == 'tp':
                self.tp += 1
            elif classification == 'fp':
                self.fp += 1
            elif classification == 'tn':
                self.tn += 1
            elif classification == 'fn':
                self.fn += 1
            elif classification == 'error':
                self.errors += 1

    def add_pair_time(self, pair_time: float):
        """Thread-safe addition of pair timing."""
        with self._lock:
            self.pair_times.append(pair_time)

    def get_metrics(self) -> Dict[str, int]:
        """Get current metrics."""
        with self._lock:
            return {
                'tp': self.tp,
                'fp': self.fp,
                'tn': self.tn,
                'fn': self.fn,
                'errors': self.errors
            }

    def get_avg_time(self) -> float:
        """Get average pair time."""
        with self._lock:
            if not self.pair_times:
                return 0.0
            return sum(self.pair_times) / len(self.pair_times)

    def get_eta(self) -> float:
        """Get estimated time remaining."""
        with self._lock:
            if not self.pair_times or self.current_pair == 0:
                return 0.0
            avg_time = sum(self.pair_times) / len(self.pair_times)
            remaining = self.total_pairs - self.current_pair
            return avg_time * remaining


def create_dashboard(state: BenchmarkState, pipeline_name: str) -> Layout:
    """Create rich dashboard layout."""
    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=8)
    )

    # Header
    elapsed = time.time() - state.start_time
    header_text = f"[bold cyan]BENCHMARK:[/bold cyan] {pipeline_name} | Phase: {state.current_phase} | Elapsed: {elapsed:.1f}s"
    layout["header"].update(Panel(header_text, style="bold blue"))

    # Body - Current status
    if state.current_phase == "Extraction":
        body_content = f"""[yellow]Extracting features...[/yellow]
Video: {state.current_video}
Algorithm: {state.current_algorithm}
Progress: {state.extracted_count}/{state.total_videos * state.total_algorithms} ({state.cached_count} from cache)
"""
    else:
        body_content = f"""[cyan]Comparing pair {state.current_pair}/{state.total_pairs}[/cyan]
Videos: {state.current_video}
Score: [bold]{state.current_score:.1f}%[/bold]
Result: {state.current_result}
Classification: {state.current_classification}
"""
    layout["body"].update(Panel(body_content, title="Current Status", border_style="cyan"))

    # Footer - Metrics and timing
    metrics = state.get_metrics()
    total = metrics['tp'] + metrics['fp'] + metrics['tn'] + metrics['fn']

    if total > 0:
        precision = metrics['tp'] / (metrics['tp'] + metrics['fp']) if (metrics['tp'] + metrics['fp']) > 0 else 0
        recall = metrics['tp'] / (metrics['tp'] + metrics['fn']) if (metrics['tp'] + metrics['fn']) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (metrics['tp'] + metrics['tn']) / total

        metrics_text = f"""[bold]Live Metrics:[/bold]
TP: [green]{metrics['tp']}[/green]  FP: [yellow]{metrics['fp']}[/yellow]  TN: [green]{metrics['tn']}[/green]  FN: [red]{metrics['fn']}[/red]  Errors: [red]{metrics['errors']}[/red]
Precision: [cyan]{precision*100:.1f}%[/cyan]  Recall: [cyan]{recall*100:.1f}%[/cyan]  F1: [cyan]{f1*100:.1f}%[/cyan]  Accuracy: [cyan]{accuracy*100:.1f}%[/cyan]

Avg time: {state.get_avg_time():.2f}s/pair  ETA: {state.get_eta():.0f}s
"""
    else:
        metrics_text = "[dim]Waiting for first comparison...[/dim]"

    layout["footer"].update(Panel(metrics_text, title="Metrics", border_style="green"))

    return layout


def list_testsets_interactive(db: VideoDatabase) -> Optional[str]:
    """List testsets and let user select one."""
    test_set_manager = TestSetManager(db)
    test_sets = test_set_manager.list_test_sets()

    if not test_sets:
        console.print("[red]Aucun testset trouvé.[/red]")
        return None

    table = Table(title="Testsets Disponibles", box=box.ROUNDED)
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Nom", style="green")
    table.add_column("Total", style="yellow", justify="right")
    table.add_column("Positives", style="blue", justify="right")
    table.add_column("Négatives", style="magenta", justify="right")

    for i, ts in enumerate(test_sets, 1):
        stats = test_set_manager.get_stats(ts['name'])
        table.add_row(
            str(i),
            ts['name'],
            str(stats['total']),
            str(stats['positives']),
            str(stats['negatives'])
        )

    console.print(table)
    console.print()

    choice = safe_int_prompt("Sélectionner un testset", default=1)

    idx = choice - 1
    if 0 <= idx < len(test_sets):
        return test_sets[idx]['name']
    else:
        console.print(f"[red]Choix invalide: {choice}[/red]")
        return None


def list_pipelines_interactive(db: VideoDatabase) -> Optional[str]:
    """List pipelines and let user select one."""
    pipeline_manager = PipelineManager(db)
    db_pipelines = pipeline_manager.list_pipelines(include_defaults=True)

    if not db_pipelines:
        console.print("[red]Aucun pipeline trouvé.[/red]")
        return None

    table = Table(title="Pipelines Disponibles", box=box.ROUNDED)
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Nom", style="green")
    table.add_column("Mode", style="yellow")
    table.add_column("Algorithmes", style="blue", justify="right")
    table.add_column("Type", style="magenta")

    for i, p in enumerate(db_pipelines, 1):
        methods = p.get('methods', [])
        mode = p.get('mode', 'unknown')
        is_default = "Défaut" if p.get('is_default') else "Custom"
        table.add_row(
            str(i),
            p['name'],
            mode,
            str(len(methods)),
            is_default
        )

    console.print(table)
    console.print()

    choice = safe_int_prompt("Sélectionner un pipeline", default=1)

    idx = choice - 1
    if 0 <= idx < len(db_pipelines):
        return db_pipelines[idx]['name']
    else:
        console.print(f"[red]Choix invalide: {choice}[/red]")
        return None


def list_testsets(db: VideoDatabase):
    """List all available test sets."""
    test_set_manager = TestSetManager(db)
    test_sets = test_set_manager.list_test_sets()

    if not test_sets:
        console.print("[red]Aucun testset trouvé.[/red]")
        return

    table = Table(title="Testsets Disponibles", box=box.ROUNDED)
    table.add_column("Nom", style="green")
    table.add_column("Total", style="yellow", justify="right")
    table.add_column("Positives", style="blue", justify="right")
    table.add_column("Négatives", style="magenta", justify="right")

    for ts in test_sets:
        stats = test_set_manager.get_stats(ts['name'])
        table.add_row(
            ts['name'],
            str(stats['total']),
            str(stats['positives']),
            str(stats['negatives'])
        )

    console.print(table)


def list_pipelines(db: VideoDatabase):
    """List all available pipelines."""
    try:
        pipeline_manager = PipelineManager(db)
        db_pipelines = pipeline_manager.list_pipelines(include_defaults=True)

        if not db_pipelines:
            console.print("[red]Aucun pipeline trouvé[/red]")
            return

        custom = [p for p in db_pipelines if not p.get('is_default')]
        defaults = [p for p in db_pipelines if p.get('is_default')]

        if custom:
            table = Table(title="Pipelines Personnalisés", box=box.ROUNDED)
            table.add_column("Nom", style="green")
            table.add_column("Mode", style="cyan")
            table.add_column("Algorithmes", style="yellow", justify="right")

            for p in custom:
                methods = p.get('methods', [])
                mode = p.get('mode', 'unknown')
                table.add_row(p['name'], mode, str(len(methods)))

            console.print(table)

        if defaults:
            table = Table(title="Pipelines par Défaut", box=box.ROUNDED)
            table.add_column("Nom", style="green")
            table.add_column("Mode", style="cyan")

            for p in defaults[:10]:
                mode = p.get('mode', 'unknown')
                table.add_row(p['name'], mode)

            console.print(table)

    except Exception as e:
        console.print(f"[red]Erreur: {e}[/red]")
        logger.error(f"Error listing pipelines: {e}", exc_info=True)


def extract_features_for_video(
    video_path: str,
    algorithm_name: str,
    params: Dict,
    storage: StorageManager,
    force_recompute: bool = False
) -> Tuple[bool, bool]:
    """
    Extract and cache features for a single video.

    Returns:
        (success, was_cached)
    """
    try:
        # Check if already cached (unless force_recompute)
        if not force_recompute:
            cached = storage.get_cached_features(video_path, algorithm_name, params)
            if cached is not None:
                return (True, True)  # Success, was cached

        # Extract features
        AlgoClass = get_algorithm(algorithm_name)
        algo = AlgoClass()
        algo.configure(**params)

        # Try extract_features() first (new standard), then extract_fingerprints() (legacy)
        if hasattr(algo, 'extract_features'):
            features = algo.extract_features(video_path)
            metadata = {
                'num_features': len(features) if isinstance(features, (list, dict)) else 0,
                'feature_type': type(features).__name__
            }
        elif hasattr(algo, 'extract_fingerprints'):
            # Fallback for legacy audio_fingerprint
            features = algo.extract_fingerprints(video_path)
            metadata = {
                'num_hashes': len(features) if isinstance(features, dict) else 0,
                'feature_type': 'fingerprints'
            }
        else:
            # Algorithm doesn't support feature extraction yet
            logger.warning(f"Algorithm {algorithm_name} doesn't have extract_features() method")
            return (True, False)

        # Store in cache
        storage.store_features(video_path, algorithm_name, params, features, metadata)
        return (True, False)  # Success, was extracted

    except Exception as e:
        logger.error(f"Error extracting features from {video_path}: {e}")
        return (False, False)


def save_checkpoint(
    checkpoint_path: Path,
    testset_name: str,
    pipeline_name: str,
    processed_pairs: List[Dict],
    remaining_pairs: List[Dict],
    metrics: Dict,
    start_time: float
):
    """Save checkpoint for resume capability."""
    checkpoint_data = {
        'testset': testset_name,
        'pipeline': pipeline_name,
        'timestamp': datetime.now().isoformat(),
        'processed_count': len(processed_pairs),
        'remaining_count': len(remaining_pairs),
        'metrics': metrics,
        'elapsed_time': time.time() - start_time,
        'processed_pairs': processed_pairs,
        'remaining_pairs': remaining_pairs
    }

    # Sanitize data before saving
    safe_checkpoint_data = json_encoder(checkpoint_data)

    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(safe_checkpoint_data, f, indent=2, ensure_ascii=False)


def load_checkpoint(checkpoint_path: Path) -> Optional[Dict]:
    """Load checkpoint data."""
    try:
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load checkpoint: {e}")
        return None


def analyze_errors(results: List[Dict], pipeline_name: str):
    """Analyze and display detailed error analysis."""
    fps = [r for r in results if r.get('classification') == 'fp']
    fns = [r for r in results if r.get('classification') == 'fn']
    tps = [r for r in results if r.get('classification') == 'tp']

    console.print("\n")
    console.print(Panel.fit(
        f"[bold cyan]Analyse Détaillée des Résultats - {pipeline_name}[/bold cyan]",
        border_style="cyan"
    ))

    # True Positives (Matches correctly detected)
    if tps:
        console.print(f"\n[bold green]✅ TRUE POSITIVES ({len(tps)}) - MATCHES correctement détectés:[/bold green]")
        tp_table = Table(box=box.ROUNDED, show_header=True)
        tp_table.add_column("#", style="cyan", justify="right", width=4)
        tp_table.add_column("Video 1", style="white", no_wrap=True, overflow="ellipsis", max_width=40)
        tp_table.add_column("Video 2", style="white", no_wrap=True, overflow="ellipsis", max_width=40)
        tp_table.add_column("Score", style="green", justify="right", width=10)

        for i, r in enumerate(tps[:20], 1):  # Limit to first 20
            v1 = Path(r['video1']).name
            v2 = Path(r['video2']).name

            # Truncate long names manually with ellipsis in middle
            if len(v1) > 38:
                v1 = v1[:18] + "..." + v1[-17:]
            if len(v2) > 38:
                v2 = v2[:18] + "..." + v2[-17:]

            tp_table.add_row(
                str(i),
                v1,
                v2,
                f"{r['score']:.1f}%"
            )

        if len(tps) > 20:
            tp_table.add_row("...", f"... et {len(tps) - 20} autres", "", "")

        console.print(tp_table)

    # False Positives
    if fps:
        console.print(f"\n[bold yellow]⚠️  FALSE POSITIVES ({len(fps)}) - Fausses alertes (ne devraient PAS matcher):[/bold yellow]")
        fp_table = Table(box=box.ROUNDED, show_header=True)
        fp_table.add_column("#", style="cyan", justify="right", width=4)
        fp_table.add_column("Video 1", style="white", no_wrap=True, overflow="ellipsis", max_width=35)
        fp_table.add_column("Video 2", style="white", no_wrap=True, overflow="ellipsis", max_width=35)
        fp_table.add_column("Score", style="yellow", justify="right", width=10)
        fp_table.add_column("Raison", style="dim", no_wrap=True, max_width=30)

        for i, r in enumerate(fps, 1):
            v1 = Path(r['video1']).name
            v2 = Path(r['video2']).name

            # Truncate long names
            if len(v1) > 33:
                v1 = v1[:16] + "..." + v1[-14:]
            if len(v2) > 33:
                v2 = v2[:16] + "..." + v2[-14:]

            # Analyze probable reason
            metadata = r.get('metadata', {})
            if 'votes' in metadata and metadata['votes'] < 5000:
                reason = "Peu de votes"
            elif r['score'] < 75:
                reason = "Score proche seuil"
            else:
                reason = "Similitude partielle"

            fp_table.add_row(
                str(i),
                v1,
                v2,
                f"{r['score']:.1f}%",
                reason
            )

        console.print(fp_table)

        # Suggestions for FP
        console.print("\n[dim]💡 Suggestions pour réduire les FP:[/dim]")
        avg_fp_score = sum(r['score'] for r in fps) / len(fps)
        console.print(f"   • Score moyen des FP: {avg_fp_score:.1f}%")
        console.print(f"   • Augmenter le seuil global à {avg_fp_score + 10:.0f}%")
        console.print(f"   • Activer la confirmation visuelle (pHash)")
        console.print(f"   • Utiliser un pipeline staged avec verification stricte")

    # False Negatives
    if fns:
        console.print(f"\n[bold red]❌ FALSE NEGATIVES ({len(fns)}) - MATCHES ratés (devraient matcher):[/bold red]")
        fn_table = Table(box=box.ROUNDED, show_header=True)
        fn_table.add_column("#", style="cyan", justify="right", width=4)
        fn_table.add_column("Video 1", style="white", no_wrap=True, overflow="ellipsis", max_width=35)
        fn_table.add_column("Video 2", style="white", no_wrap=True, overflow="ellipsis", max_width=35)
        fn_table.add_column("Score", style="red", justify="right", width=10)
        fn_table.add_column("Raison", style="dim", no_wrap=True, max_width=30)

        for i, r in enumerate(fns, 1):
            v1 = Path(r['video1']).name
            v2 = Path(r['video2']).name

            # Truncate long names
            if len(v1) > 33:
                v1 = v1[:16] + "..." + v1[-14:]
            if len(v2) > 33:
                v2 = v2[:16] + "..." + v2[-14:]

            # Analyze probable reason
            metadata = r.get('metadata', {})
            if 'votes' in metadata and metadata['votes'] < 1000:
                reason = "Peu de votes"
            elif r['score'] > 60:
                reason = "Score proche seuil"
            else:
                reason = "Similitude faible"

            fn_table.add_row(
                str(i),
                v1,
                v2,
                f"{r['score']:.1f}%",
                reason
            )

        console.print(fn_table)

        # Suggestions for FN
        console.print("\n[dim]💡 Suggestions pour réduire les FN:[/dim]")
        avg_fn_score = sum(r['score'] for r in fns) / len(fns)
        console.print(f"   • Score moyen des FN: {avg_fn_score:.1f}%")
        console.print(f"   • Baisser le seuil global à {avg_fn_score - 5:.0f}%")
        console.print(f"   • Ajouter des algorithmes complémentaires")
        console.print(f"   • Vérifier la qualité des vidéos (codec, résolution)")


def profile_performance(results: List[Dict], extraction_time: float, algorithm_names: List[str]):
    """Display performance profiling."""
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Profil de Performance[/bold cyan]",
        border_style="cyan"
    ))

    # Extraction breakdown
    console.print("\n[bold]Phase 1: Extraction[/bold]")
    console.print(f"  Temps total: {extraction_time:.1f}s")

    # Comparison breakdown
    total_comparison_time = sum(r.get('time_seconds', 0) for r in results)
    avg_comparison_time = total_comparison_time / len(results) if results else 0

    console.print(f"\n[bold]Phase 2: Comparaison[/bold]")
    console.print(f"  Temps total: {total_comparison_time:.1f}s")
    console.print(f"  Temps moyen: {avg_comparison_time:.2f}s/paire")

    # Time distribution
    if results:
        times = [r.get('time_seconds', 0) for r in results]
        times.sort()

        p50 = times[len(times) // 2]
        p95 = times[int(len(times) * 0.95)]
        p99 = times[int(len(times) * 0.99)]

        console.print(f"\n[bold]Distribution des temps:[/bold]")
        console.print(f"  P50: {p50:.2f}s")
        console.print(f"  P95: {p95:.2f}s")
        console.print(f"  P99: {p99:.2f}s")
        console.print(f"  Max: {max(times):.2f}s")

    # Algorithm performance (if metadata available)
    algo_stats = defaultdict(list)
    for r in results:
        metadata = r.get('metadata', {})
        if 'algorithm_times' in metadata:
            for algo, algo_time in metadata['algorithm_times'].items():
                algo_stats[algo].append(algo_time)

    if algo_stats:
        console.print(f"\n[bold]Performance par algorithme:[/bold]")
        for algo, times in algo_stats.items():
            avg = sum(times) / len(times)
            console.print(f"  {algo}: {avg:.2f}s avg")


def export_to_benchmark_results(
    testset_name: str,
    pipeline_name: str,
    results: List[Dict],
    metrics: Dict,
    total_time: float,
    extraction_time: float,
    comparison_time: float,
    pipeline_config: Dict
) -> Path:
    """Export results to benchmark_results/ directory structure."""
    # Create timestamped directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pipeline_safe = pipeline_name.replace(' ', '_').replace('/', '_')
    export_dir = RESULTS_DIR / f"{pipeline_safe}_{timestamp}"
    export_dir.mkdir(parents=True, exist_ok=True)

    # Calculate statistics
    tp = metrics.get('tp', 0)
    fp = metrics.get('fp', 0)
    tn = metrics.get('tn', 0)
    fn = metrics.get('fn', 0)
    errors = metrics.get('errors', 0)

    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / total if total > 0 else 0.0

    # Create JSON-safe pipeline config (remove non-serializable objects)
    safe_pipeline_config = {
        'mode': pipeline_config.get('mode', 'unknown'),
        'global_threshold': pipeline_config.get('global_threshold', 70.0),
        'algorithms': []
    }

    # Add algorithm names only (not full method objects)
    if 'methods' in pipeline_config:
        for method in pipeline_config['methods']:
            if isinstance(method, dict):
                safe_pipeline_config['algorithms'].append({
                    'name': method.get('name', 'unknown'),
                    'weight': method.get('weight', 1.0),
                    'enabled': method.get('enabled', True)
                })

    # Export JSON
    json_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'testset': testset_name,
            'pipeline_name': pipeline_name,
            'pipeline_mode': pipeline_config.get('mode', 'unknown'),
            'threshold': pipeline_config.get('global_threshold', 70.0),
            'total_pairs': len(results),
            'total_time_seconds': round(total_time, 2),
            'extraction_time_seconds': round(extraction_time, 2),
            'comparison_time_seconds': round(comparison_time, 2),
            'avg_time_seconds': round(comparison_time / len(results), 2) if results else 0
        },
        'pipeline_config': safe_pipeline_config,
        'summary': {
            'confusion_matrix': {
                'tp': tp,
                'fp': fp,
                'tn': tn,
                'fn': fn
            },
            'metrics': {
                'precision': round(precision, 4),
                'recall': round(recall, 4),
                'f1_score': round(f1, 4),
                'accuracy': round(accuracy, 4)
            },
            'counts': {
                'total_positives': tp + fn,
                'total_negatives': tn + fp,
                'errors': errors
            }
        },
        'results': results
    }

    json_path = export_dir / "results.json"

    # Recursively sanitize the data using global json_encoder
    safe_json_data = json_encoder(json_data)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(safe_json_data, f, indent=2, ensure_ascii=False)

    # Export summary text
    summary_path = export_dir / "summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"BENCHMARK SUMMARY\n")
        f.write(f"=" * 70 + "\n\n")
        f.write(f"Testset: {testset_name}\n")
        f.write(f"Pipeline: {pipeline_name}\n")
        f.write(f"Mode: {pipeline_config.get('mode', 'unknown')}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write(f"CONFUSION MATRIX:\n")
        f.write(f"  TP: {tp}  FP: {fp}  TN: {tn}  FN: {fn}\n\n")

        f.write(f"METRICS:\n")
        f.write(f"  Precision: {precision*100:.2f}%\n")
        f.write(f"  Recall:    {recall*100:.2f}%\n")
        f.write(f"  F1-Score:  {f1*100:.2f}%\n")
        f.write(f"  Accuracy:  {accuracy*100:.2f}%\n\n")

        f.write(f"TIMING:\n")
        f.write(f"  Extraction:  {extraction_time:.1f}s\n")
        f.write(f"  Comparison:  {comparison_time:.1f}s\n")
        f.write(f"  Total:       {total_time:.1f}s\n")
        f.write(f"  Avg/pair:    {comparison_time/len(results):.2f}s\n")

    # Export failures CSV
    fps = [r for r in results if r.get('classification') == 'fp']
    fns = [r for r in results if r.get('classification') == 'fn']

    if fps or fns:
        failures_path = export_dir / "failures.csv"
        with open(failures_path, 'w', encoding='utf-8') as f:
            f.write("Type,Video1,Video2,Expected,Score,Metadata\n")
            for r in fps:
                f.write(f"FP,{r['video1']},{r['video2']},{r['expected']},{r['score']:.1f},\"{r.get('metadata', {})}\"\n")
            for r in fns:
                f.write(f"FN,{r['video1']},{r['video2']},{r['expected']},{r['score']:.1f},\"{r.get('metadata', {})}\"\n")

    console.print(f"\n[green]✅ Résultats exportés vers:[/green] {export_dir}")
    console.print(f"   • [cyan]results.json[/cyan] - Données complètes")
    console.print(f"   • [cyan]summary.txt[/cyan] - Résumé textuel")
    if fps or fns:
        console.print(f"   • [cyan]failures.csv[/cyan] - FP/FN pour analyse")

    return export_dir


def run_single_benchmark(
    testset_name: str,
    pipeline_name: str,
    limit: int = None,
    force_recompute: bool = False,
    resume_from: str = None,
    analyze: bool = False,
    profile: bool = False,
    export_matrix: bool = False,
    silent_progress: bool = False
) -> Dict[str, Any]:
    """
    Run a single benchmark.

    Args:
        silent_progress: If True, disable live progress displays (for multi-pipeline mode)

    Returns summary dict with metrics and results.
    """
    # Initialize
    db = VideoDatabase(ROOT_DB_PATH)
    test_set_manager = TestSetManager(db)
    pipeline_manager = PipelineManager(db)
    storage = StorageManager()

    # Check for resume
    processed_results = []
    resume_metrics = {'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0, 'errors': 0}
    resume_start_time = 0

    if resume_from:
        checkpoint_path = CHECKPOINT_DIR / resume_from
        if checkpoint_path.exists():
            checkpoint = load_checkpoint(checkpoint_path)
            if checkpoint:
                console.print(f"[yellow]📂 Reprise depuis checkpoint:[/yellow] {resume_from}")
                console.print(f"   Déjà traité: {checkpoint['processed_count']} paires")
                processed_results = checkpoint['processed_pairs']
                resume_metrics = checkpoint['metrics']
                resume_start_time = checkpoint['elapsed_time']

    # Get testset
    console.print(f"\n[cyan]📋 Chargement du testset '{testset_name}'...[/cyan]")
    all_testsets = test_set_manager.list_test_sets()
    matched_testset = None
    for ts in all_testsets:
        if ts['name'].lower() == testset_name.lower():
            matched_testset = ts['name']
            break

    if not matched_testset:
        console.print(f"[red]❌ Testset '{testset_name}' non trouvé[/red]")
        return None

    pairs = test_set_manager.get_test_set(matched_testset)

    # Apply resume filter
    if resume_from and processed_results:
        processed_ids = {r.get('pair_id') for r in processed_results}
        pairs = [p for p in pairs if p.get('id') not in processed_ids]

    if limit and limit < len(pairs):
        pairs = pairs[:limit]
        console.print(f"[green]✅ {len(pairs)} paires (limité à {limit})[/green]")
    else:
        console.print(f"[green]✅ {len(pairs)} paires chargées[/green]")

    # Get pipeline
    console.print(f"\n[cyan]🔧 Chargement du pipeline '{pipeline_name}'...[/cyan]")
    all_pipelines = pipeline_manager.list_pipelines(include_defaults=True)
    matched_pipeline = None
    search_key = pipeline_name.lower().strip()

    for p in all_pipelines:
        normalized = p['name'].lower()
        normalized = normalized.replace('🚀 ', '').replace('(duplicateflow)', '').strip()
        if normalized == search_key or p['name'].lower() == search_key:
            matched_pipeline = p
            break

    if not matched_pipeline:
        console.print(f"[red]❌ Pipeline '{pipeline_name}' non trouvé[/red]")
        return None

    methods = matched_pipeline.get('methods', [])
    global_threshold = matched_pipeline.get('global_threshold', 70.0) or 70.0

    # Display pipeline info
    panel_content = f"[bold]{matched_pipeline['name']}[/bold]\n"
    panel_content += f"Seuil global: [cyan]{global_threshold:.1f}%[/cyan]\n"
    panel_content += f"Algorithmes: {len(methods)}"
    console.print(Panel(panel_content, title="Pipeline", border_style="blue"))

    # Collect unique videos
    unique_videos: Set[str] = set()
    for pair in pairs:
        unique_videos.add(pair['video1_path'])
        unique_videos.add(pair['video2_path'])

    # Create state for dashboard
    state = BenchmarkState(
        total_pairs=len(pairs),
        total_videos=len(unique_videos),
        total_algorithms=len(methods)
    )

    # Restore resume metrics
    for key, value in resume_metrics.items():
        state.update(**{key: value})

    # === PHASE 1: EXTRACTION ===
    state.update(current_phase="Extraction")

    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print("[bold cyan]PHASE 1: EXTRACTION DES FEATURES[/bold cyan]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")

    if force_recompute:
        console.print("[yellow]⚠️  MODE FORCE RECOMPUTE: Le cache sera ignoré[/yellow]\n")

    console.print(f"[cyan]📊 {len(unique_videos)} vidéos uniques à indexer[/cyan]")
    console.print(f"[cyan]🔧 {len(methods)} algorithmes[/cyan]\n")

    extraction_start = time.time()

    # Progress bar for extraction (disable live mode if silent_progress)
    progress_kwargs = {
        'console': console,
        'disable': silent_progress
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        **progress_kwargs
    ) as progress:

        task = progress.add_task(
            "[cyan]Extraction...",
            total=len(unique_videos) * len(methods)
        )

        for video_path in unique_videos:
            video_name = Path(video_path).name
            state.update(current_video=video_name[:40])

            for method in methods:
                if not method.get('enabled', True):
                    progress.update(task, advance=1)
                    continue

                algo_name = method.get('name', '')
                if algo_name.startswith('df_'):
                    algo_name = algo_name[3:]

                state.update(current_algorithm=algo_name)

                params = method.get('parameters', {}).copy()
                params.pop('threshold', None)  # Remove threshold

                success, was_cached = extract_features_for_video(
                    video_path, algo_name, params, storage, force_recompute
                )

                if was_cached:
                    state.update(cached_count=state.cached_count + 1)

                state.update(extracted_count=state.extracted_count + 1)
                progress.update(task, advance=1)

    extraction_time = time.time() - extraction_start
    console.print(f"\n[green]✅ Extraction terminée en {extraction_time:.1f}s[/green]")

    # Cache stats
    stats = storage.get_stats()
    feat_stats = stats['feature_cache']

    cache_panel = f"""Entries: {feat_stats['total_entries']}
Hit rate: [green]{feat_stats['hit_rate']:.1f}%[/green]
DB size: {feat_stats['db_size_mb']:.1f} MB"""
    console.print(Panel(cache_panel, title="📊 Cache Stats", border_style="green"))

    # === PHASE 2: COMPARISON ===
    state.update(current_phase="Comparison")

    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print("[bold cyan]PHASE 2: COMPARAISON[/bold cyan]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")

    results = processed_results.copy()  # Start with resumed results
    metrics = resume_metrics.copy()
    comparison_start = time.time() - resume_start_time

    # Checkpoint path
    checkpoint_path = CHECKPOINT_DIR / f"checkpoint_{testset_name}_{pipeline_name}.json"

    # Progress bar for comparison (disable live mode if silent_progress)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        **progress_kwargs
    ) as progress:

        task = progress.add_task("[cyan]Comparaison...", total=len(pairs))

        for i, pair in enumerate(pairs, 1):
            video1 = pair['video1_path']
            video2 = pair['video2_path']
            expected = pair['expected']

            v1_name = Path(video1).name
            v2_name = Path(video2).name
            state.update(
                current_pair=len(processed_results) + i,
                current_video=f"{v1_name[:25]} ↔ {v2_name[:25]}"
            )

            try:
                pair_start = time.time()

                # Compare using cached features
                individual_results = []
                weighted_sum = 0.0
                total_weight = 0.0

                for method in methods:
                    if not method.get('enabled', True):
                        continue

                    algo_name = method.get('name', '')
                    if algo_name.startswith('df_'):
                        algo_name = algo_name[3:]

                    weight = method.get('weight', 1.0)
                    params = method.get('parameters', {}).copy()
                    threshold = params.pop('threshold', 70.0)

                    # Get cached features
                    features1 = storage.get_cached_features(video1, algo_name, params)
                    features2 = storage.get_cached_features(video2, algo_name, params)

                    if features1 is None or features2 is None:
                        logger.warning(f"Missing features for {algo_name}")
                        continue

                    # Compare features
                    try:
                        AlgoClass = get_algorithm(algo_name)

                        if hasattr(AlgoClass, 'compare_features'):
                            result = AlgoClass.compare_features(features1, features2, threshold, params)
                        else:
                            logger.warning(f"Algorithm {algo_name} doesn't have compare_features() method")
                            result = {'similarity': 0.0, 'accepted': False, 'metadata': {'error': 'No compare_features method'}}
                    except Exception as e:
                        logger.error(f"Error comparing features for {algo_name}: {e}")
                        result = {'similarity': 0.0, 'accepted': False, 'metadata': {'error': str(e)}}

                    individual_results.append({
                        'algorithm': algo_name,
                        'similarity': result['similarity'],
                        'accepted': result['accepted'],
                        'weight': weight,
                        'metadata': result.get('metadata', {})
                    })

                    weighted_sum += result['similarity'] * weight
                    total_weight += weight

                # Calculate weighted score
                if total_weight > 0:
                    score = weighted_sum / total_weight
                else:
                    score = 0.0

                # Determine if match based on global threshold
                is_match = score >= global_threshold

                pair_time = time.time() - pair_start
                state.add_pair_time(pair_time)

                # Determine classification
                if expected in ['positive', 'duplicate', 'scene_found']:
                    if is_match:
                        classification = 'tp'
                        metrics['tp'] += 1
                        result_text = "[bold green]MATCH[/bold green]"
                        class_text = "[bold blue]✅ TP[/bold blue]"
                    else:
                        classification = 'fn'
                        metrics['fn'] += 1
                        result_text = "[bold red]NO MATCH[/bold red]"
                        class_text = "[bold red]❌ FN[/bold red]"
                elif expected in ['negative', 'not_duplicate', 'scene_not_found']:
                    if is_match:
                        classification = 'fp'
                        metrics['fp'] += 1
                        result_text = "[bold yellow]MATCH[/bold yellow]"
                        class_text = "[bold yellow]⚠️  FP[/bold yellow]"
                    else:
                        classification = 'tn'
                        metrics['tn'] += 1
                        result_text = "[bold green]NO MATCH[/bold green]"
                        class_text = "[bold green]✅ TN[/bold green]"
                else:
                    classification = 'unknown'
                    metrics['unknown'] = metrics.get('unknown', 0) + 1
                    result_text = "[dim]UNKNOWN[/dim]"
                    class_text = "[dim]❓ Unknown[/dim]"

                state.update(
                    current_score=score,
                    current_result=result_text,
                    current_classification=class_text
                )
                state.increment_metric(classification)

                results.append({
                    'pair_id': pair.get('id'),
                    'video1': video1,
                    'video2': video2,
                    'expected': expected,
                    'score': score,
                    'is_match': is_match,
                    'classification': classification,
                    'time_seconds': pair_time,
                    'status': 'success',
                    'metadata': {
                        'individual_results': individual_results
                    }
                })

            except Exception as e:
                logger.error(f"Error processing pair: {e}", exc_info=True)
                metrics['errors'] = metrics.get('errors', 0) + 1
                state.increment_metric('error')

                results.append({
                    'pair_id': pair.get('id'),
                    'video1': video1,
                    'video2': video2,
                    'expected': expected,
                    'score': 0.0,
                    'is_match': False,
                    'classification': 'error',
                    'time_seconds': 0.0,
                    'status': 'error',
                    'error': str(e)
                })

            progress.update(task, advance=1)

            # Save checkpoint every 10 pairs
            if i % 10 == 0:
                save_checkpoint(
                    checkpoint_path,
                    testset_name,
                    pipeline_name,
                    results,
                    pairs[i:],
                    metrics,
                    comparison_start
                )

    comparison_time = time.time() - comparison_start
    total_time = extraction_time + comparison_time

    # Remove checkpoint on success
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # === SUMMARY ===
    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print("[bold cyan]RÉSUMÉ[/bold cyan]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")

    total = metrics['tp'] + metrics['fp'] + metrics['tn'] + metrics['fn']
    if total > 0:
        precision = metrics['tp'] / (metrics['tp'] + metrics['fp']) if (metrics['tp'] + metrics['fp']) > 0 else 0
        recall = metrics['tp'] / (metrics['tp'] + metrics['fn']) if (metrics['tp'] + metrics['fn']) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (metrics['tp'] + metrics['tn']) / total

        # Metrics table
        metrics_table = Table(title="📊 Métriques", box=box.ROUNDED)
        metrics_table.add_column("Métrique", style="cyan")
        metrics_table.add_column("Valeur", style="green", justify="right")

        metrics_table.add_row("TP (True Positives)", f"[green]{metrics['tp']}[/green]")
        metrics_table.add_row("FP (False Positives)", f"[yellow]{metrics['fp']}[/yellow]")
        metrics_table.add_row("TN (True Negatives)", f"[green]{metrics['tn']}[/green]")
        metrics_table.add_row("FN (False Negatives)", f"[red]{metrics['fn']}[/red]")
        if metrics.get('errors', 0) > 0:
            metrics_table.add_row("Errors", f"[red]{metrics['errors']}[/red]")
        metrics_table.add_row("", "")
        metrics_table.add_row("Precision", f"{precision*100:.1f}%")
        metrics_table.add_row("Recall", f"{recall*100:.1f}%")
        metrics_table.add_row("F1-Score", f"{f1*100:.1f}%")
        metrics_table.add_row("Accuracy", f"{accuracy*100:.1f}%")

        console.print(metrics_table)

    # Timing table
    timing_table = Table(title="⏱️  Timings", box=box.ROUNDED)
    timing_table.add_column("Phase", style="cyan")
    timing_table.add_column("Temps", style="green", justify="right")

    timing_table.add_row("Extraction", f"{extraction_time:.1f}s")
    timing_table.add_row("Comparaison", f"{comparison_time:.1f}s")
    timing_table.add_row("Total", f"{total_time:.1f}s")
    timing_table.add_row("Moyenne/paire", f"{comparison_time/len(pairs):.2f}s")

    console.print(timing_table)

    # Error analysis
    if analyze:
        analyze_errors(results, pipeline_name)

    # Performance profiling
    if profile:
        profile_performance(results, extraction_time, [m['name'] for m in methods])

    # Export to benchmark_results/
    export_dir = None
    if export_matrix:
        export_dir = export_to_benchmark_results(
            testset_name,
            pipeline_name,
            results,
            metrics,
            total_time,
            extraction_time,
            comparison_time,
            matched_pipeline
        )

    return {
        'pipeline_name': pipeline_name,
        'metrics': metrics,
        'results': results,
        'total_time': total_time,
        'extraction_time': extraction_time,
        'comparison_time': comparison_time,
        'export_dir': export_dir
    }


def run_multi_pipeline_comparison(
    testset_name: str,
    pipeline_names: List[str],
    limit: int = None,
    max_workers: int = 3
):
    """Run multiple pipelines in parallel and compare results."""
    console.print(f"\n[bold cyan]🔬 COMPARAISON MULTI-PIPELINES[/bold cyan]")
    console.print(f"Testset: [green]{testset_name}[/green]")
    console.print(f"Pipelines: [yellow]{', '.join(pipeline_names)}[/yellow]")
    console.print(f"Workers: [cyan]{max_workers}[/cyan]\n")

    # Run benchmarks in parallel
    all_summaries = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for pipeline_name in pipeline_names:
            future = executor.submit(
                run_single_benchmark,
                testset_name,
                pipeline_name,
                limit=limit,
                analyze=False,
                profile=False,
                export_matrix=True,
                silent_progress=True  # Disable live progress to avoid conflicts
            )
            futures[future] = pipeline_name

        # Collect results
        for future in as_completed(futures):
            pipeline_name = futures[future]
            try:
                summary = future.result()
                if summary:
                    all_summaries[pipeline_name] = summary
                    console.print(f"[green]✅ {pipeline_name} terminé[/green]")
            except Exception as e:
                console.print(f"[red]❌ {pipeline_name} échoué: {e}[/red]")

    # Display comparison table
    if all_summaries:
        console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
        console.print("[bold cyan]TABLEAU COMPARATIF[/bold cyan]")
        console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")

        comp_table = Table(title="Comparaison des Pipelines", box=box.DOUBLE)
        comp_table.add_column("Pipeline", style="cyan", no_wrap=False, max_width=20)
        comp_table.add_column("Prec.", style="green", justify="right")
        comp_table.add_column("Recall", style="green", justify="right")
        comp_table.add_column("F1", style="green", justify="right")
        comp_table.add_column("Acc.", style="yellow", justify="right")
        comp_table.add_column("TP", style="blue", justify="right")
        comp_table.add_column("FP", style="yellow", justify="right")
        comp_table.add_column("TN", style="blue", justify="right")
        comp_table.add_column("FN", style="red", justify="right")
        comp_table.add_column("Temps", style="magenta", justify="right")

        for pipeline_name, summary in all_summaries.items():
            metrics = summary['metrics']
            tp = metrics['tp']
            fp = metrics['fp']
            tn = metrics['tn']
            fn = metrics['fn']

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            accuracy = (tp + tn) / (tp + fp + tn + fn) if (tp + fp + tn + fn) > 0 else 0

            comp_table.add_row(
                pipeline_name,
                f"{precision*100:.1f}%",
                f"{recall*100:.1f}%",
                f"{f1*100:.1f}%",
                f"{accuracy*100:.1f}%",
                str(tp),
                str(fp),
                str(tn),
                str(fn),
                f"{summary['comparison_time']:.1f}s"
            )

        console.print(comp_table)

        # Best pipeline recommendation
        best_f1 = max(all_summaries.items(), key=lambda x:
            2 * (x[1]['metrics']['tp'] / (x[1]['metrics']['tp'] + x[1]['metrics']['fp'])) *
            (x[1]['metrics']['tp'] / (x[1]['metrics']['tp'] + x[1]['metrics']['fn'])) /
            ((x[1]['metrics']['tp'] / (x[1]['metrics']['tp'] + x[1]['metrics']['fp'])) +
             (x[1]['metrics']['tp'] / (x[1]['metrics']['tp'] + x[1]['metrics']['fn'])))
            if (x[1]['metrics']['tp'] + x[1]['metrics']['fp']) > 0 and
               (x[1]['metrics']['tp'] + x[1]['metrics']['fn']) > 0 else 0
        )

        best_speed = min(all_summaries.items(), key=lambda x: x[1]['comparison_time'])

        console.print(f"\n[bold]Recommandations:[/bold]")
        console.print(f"  🏆 Meilleur F1-Score: [green]{best_f1[0]}[/green]")
        console.print(f"  ⚡ Plus rapide: [cyan]{best_speed[0]}[/cyan] ({best_speed[1]['comparison_time']:.1f}s)")


def interactive_mode():
    """Interactive mode with prompts."""
    # Fix terminal mode to handle Enter key properly
    old_terminal_settings = fix_terminal_mode()

    try:
        console.print(Panel.fit(
            "[bold cyan]Mode Interactif - DuplicateFlow Benchmark[/bold cyan]",
            border_style="cyan"
        ))

        db = VideoDatabase(ROOT_DB_PATH)

        # Select testset
        testset = list_testsets_interactive(db)
        if not testset:
            return

        # Select mode
        console.print("\n[bold]Mode de benchmark:[/bold]")
        console.print("  1. Pipeline unique")
        console.print("  2. Comparaison multi-pipelines")
        console.print()

        mode = safe_int_prompt("Choisir un mode", default=1)

        if mode == 1:
            # Single pipeline
            pipeline = list_pipelines_interactive(db)
            if not pipeline:
                return

            # Options
            limit = None
            console.print()
            if safe_confirm("Limiter le nombre de paires?", default=False):
                limit = safe_int_prompt("Nombre de paires", default=10)

            analyze = safe_confirm("Analyse détaillée des erreurs?", default=True)
            profile = safe_confirm("Profiling de performance?", default=False)
            export = safe_confirm("Exporter vers benchmark_results/?", default=True)

            # Run
            run_single_benchmark(
                testset,
                pipeline,
                limit=limit,
                analyze=analyze,
                profile=profile,
                export_matrix=export
            )

        else:
            # Multi-pipeline comparison
            console.print("\n[yellow]Sélectionner les pipelines à comparer (séparés par des virgules):[/yellow]")
            pipeline_manager = PipelineManager(db)
            all_pipelines = pipeline_manager.list_pipelines(include_defaults=True)

            for i, p in enumerate(all_pipelines[:10], 1):
                console.print(f"  {i}. {p['name']}")

            console.print()
            pipeline_names = safe_text_prompt("Pipelines (ex: 1,3,5 ou noms)")

            # Parse selection
            selected = []
            for item in pipeline_names.split(','):
                item = item.strip()
                if item.isdigit():
                    idx = int(item) - 1
                    if 0 <= idx < len(all_pipelines):
                        selected.append(all_pipelines[idx]['name'])
                else:
                    selected.append(item)

            if len(selected) < 2:
                console.print("[red]Au moins 2 pipelines requis pour comparaison[/red]")
                return

            # Options
            limit = None
            console.print()
            if safe_confirm("Limiter le nombre de paires?", default=False):
                limit = safe_int_prompt("Nombre de paires", default=10)

            max_workers = safe_int_prompt("Nombre de workers parallèles", default=3)

            # Run
            run_multi_pipeline_comparison(
                testset,
                selected,
                limit=limit,
                max_workers=max_workers
            )

    finally:
        # Restore original terminal settings if they were saved
        if old_terminal_settings and sys.stdin.isatty():
            try:
                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSANOW, old_terminal_settings)
            except:
                pass


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark avec cache de features et mode avancé',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--testset', help='Nom du testset')
    parser.add_argument('--pipeline', help='Nom du pipeline')
    parser.add_argument('--compare', help='Comparer plusieurs pipelines (séparés par des virgules)')
    parser.add_argument('--output', '-o', help='Fichier JSON de sortie (deprecated, use --export-matrix)')
    parser.add_argument('--list-testsets', action='store_true', help='Lister les testsets disponibles')
    parser.add_argument('--list-pipelines', action='store_true', help='Lister les pipelines disponibles')
    parser.add_argument('--interactive', '-i', action='store_true', help='Mode interactif')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mode verbeux')
    parser.add_argument('--limit', type=int, help='Limiter le nombre de paires')
    parser.add_argument('--force-recompute', action='store_true',
                        help='Forcer le recalcul des features (ignorer le cache)')
    parser.add_argument('--resume', help='Reprendre depuis un checkpoint (nom du fichier)')
    parser.add_argument('--analyze', action='store_true',
                        help='Analyse détaillée des erreurs (FP/FN/TP)')
    parser.add_argument('--profile', action='store_true',
                        help='Profiling de performance')
    parser.add_argument('--export-matrix', action='store_true',
                        help='Exporter vers benchmark_results/ avec structure complète')
    parser.add_argument('--max-workers', type=int, default=3,
                        help='Nombre de workers pour comparaison multi-pipelines')

    args = parser.parse_args()

    db = VideoDatabase(ROOT_DB_PATH)

    # List modes
    if args.list_testsets:
        list_testsets(db)
        return 0

    if args.list_pipelines:
        list_pipelines(db)
        return 0

    # Interactive mode
    if args.interactive:
        interactive_mode()
        return 0

    # Multi-pipeline comparison
    if args.compare:
        if not args.testset:
            console.print("[red]--testset requis pour --compare[/red]")
            return 1

        pipeline_names = [p.strip() for p in args.compare.split(',')]
        run_multi_pipeline_comparison(
            args.testset,
            pipeline_names,
            limit=args.limit,
            max_workers=args.max_workers
        )
        return 0

    # Single pipeline benchmark
    if not args.testset or not args.pipeline:
        parser.print_help()
        console.print("\n[red]❌ --testset et --pipeline requis (ou --interactive)[/red]")
        return 1

    run_single_benchmark(
        args.testset,
        args.pipeline,
        limit=args.limit,
        force_recompute=args.force_recompute,
        resume_from=args.resume,
        analyze=args.analyze,
        profile=args.profile,
        export_matrix=args.export_matrix
    )

    return 0


if __name__ == '__main__':
    sys.exit(main())
