# 🚀 Propositions d'amélioration du CLI run_testset.py

**Date**: 2025-12-19
**Version**: 1.2 - Arborescences + Pipeline Management
**Status**: ✅ Propositions complètes (12 catégories) - En attente de validation

---

## 📋 Résumé Exécutif

Analyse complète de `run_testset.py` (1,647 lignes) avec **12 catégories d'améliorations** proposées.

### 🆕 Nouvelles features killer (ajoutées suite à feedback utilisateur)
- **11. Recherche dans Arborescences** ⭐ - Scan dossiers, détection scènes incluses, cross-search
- **12. Gestion et Configuration des Pipelines** ⭐ - Création interactive, YAML, doc algorithmes pour débutants

### Métriques actuelles
- **Lignes**: 1,647 LOC
- **Architecture**: Monolithique (tout dans 1 fichier)
- **Localisation**: Racine du projet (devrait être dans duplicateflow/)
- **Fonctionnalités**: 85% complètes
- **Maintenabilité**: Bonne (mais peut être améliorée)

### Objectifs des améliorations
1. ✅ **Migrer vers DuplicateFlow** - Structure CLI officielle
2. ✅ **Modulariser** - Split en composants réutilisables
3. ✅ **UX Premium** - Erreurs claires, suggestions intelligentes
4. ✅ **Features manquantes** - Historique, validation, régression, recherche arborescences
5. ✅ **Extensibilité** - Plugin system, configuration avancée

---

## 🎯 12 Catégories d'Améliorations

### 1. 📂 Organisation du code (PRIORITÉ: 🔴 HAUTE)

#### Problème actuel
- 1,647 lignes dans un seul fichier `run_testset.py` à la racine
- Pas d'organisation modulaire
- Difficile à maintenir et étendre

#### Proposition: Migration vers DuplicateFlow

```
duplicateflow/
├── duplicateflow/
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── commands/
│   │   │   ├── __init__.py
│   │   │   ├── benchmark.py       # Commande benchmark
│   │   │   ├── testset.py         # Gestion testsets
│   │   │   └── compare.py         # Comparaison multi-pipelines
│   │   ├── ui/
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py       # Live dashboard
│   │   │   ├── tables.py          # Table formatters
│   │   │   └── interactive.py     # Mode interactif
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── checkpoint.py      # Checkpoint manager
│   │       ├── export.py          # Export results
│   │       └── profiling.py       # Performance profiling
│   └── ...
```

#### Code exemple: Structure modulaire

**duplicateflow/cli/commands/benchmark.py**:
```python
"""Benchmark command - Run pipeline on testset."""
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from duplicateflow.pipeline import Pipeline
from ..ui.dashboard import BenchmarkDashboard
from ..utils.checkpoint import CheckpointManager

class BenchmarkCommand:
    """Run benchmark on a testset with a pipeline."""

    def __init__(self, console: Console):
        self.console = console
        self.dashboard = BenchmarkDashboard(console)
        self.checkpoint_mgr = CheckpointManager()

    def execute(
        self,
        testset_name: str,
        pipeline_name: str,
        limit: Optional[int] = None,
        force_recompute: bool = False,
        resume_from: Optional[Path] = None
    ):
        """Execute benchmark command."""
        # Implementation
        pass
```

**duplicateflow/cli/__main__.py**:
```python
"""CLI entry point."""
import argparse
from rich.console import Console
from .commands.benchmark import BenchmarkCommand
from .commands.compare import CompareCommand
from .commands.testset import TestSetCommand

def main():
    parser = argparse.ArgumentParser(description="DuplicateFlow CLI")
    subparsers = parser.add_subparsers(dest='command')

    # Benchmark command
    bench_parser = subparsers.add_parser('benchmark')
    bench_parser.add_argument('--testset', required=True)
    bench_parser.add_argument('--pipeline', required=True)
    # ... more args

    # Compare command
    compare_parser = subparsers.add_parser('compare')
    # ... args

    args = parser.parse_args()
    console = Console()

    if args.command == 'benchmark':
        cmd = BenchmarkCommand(console)
        cmd.execute(...)
    elif args.command == 'compare':
        cmd = CompareCommand(console)
        cmd.execute(...)

if __name__ == '__main__':
    main()
```

**Impact**:
- ✅ Meilleure maintenabilité
- ✅ Réutilisabilité des composants
- ✅ Structure professionnelle
- ✅ Facilite l'ajout de nouvelles commandes

---

### 2. 🎨 Amélioration UX (PRIORITÉ: 🔴 HAUTE)

#### 2.1 Messages d'erreur avec suggestions

**Problème actuel**:
```
Error: Testset 'defaukt' not found
```

**Proposition**:
```python
from difflib import get_close_matches

def handle_testset_not_found(testset_name: str, available_testsets: List[str]):
    """Show helpful error with suggestions."""
    console.print(f"\n[red]✗[/red] Testset '{testset_name}' not found\n")

    # Fuzzy matching
    suggestions = get_close_matches(testset_name, available_testsets, n=3, cutoff=0.6)

    if suggestions:
        console.print("[yellow]Did you mean?[/yellow]")
        for suggestion in suggestions:
            console.print(f"  • {suggestion}")

    console.print("\n[cyan]Available testsets:[/cyan]")
    for testset in available_testsets:
        console.print(f"  • {testset}")

    console.print("\n[dim]Hint: Use --list-testsets to see details[/dim]")
```

**Exemple output**:
```
✗ Testset 'defaukt' not found

Did you mean?
  • default
  • test_quick

Available testsets:
  • default
  • stress_test
  • test_quick

Hint: Use --list-testsets to see details
```

#### 2.2 Enhanced --help

**Proposition**:
```python
def create_rich_help():
    """Create enhanced help with examples."""
    help_text = """
[bold cyan]DuplicateFlow CLI - Benchmark Tool[/bold cyan]

[yellow]QUICK START:[/yellow]
  # Interactive mode (recommended for first time)
  $ duplicateflow benchmark --interactive

  # Run single benchmark
  $ duplicateflow benchmark --testset default --pipeline balanced

  # Compare multiple pipelines
  $ duplicateflow compare --pipelines balanced,thorough,fast

[yellow]COMMON WORKFLOWS:[/yellow]

  1. Quick test (10 pairs):
     $ duplicateflow benchmark --testset default --pipeline fast --limit 10

  2. Full benchmark with analysis:
     $ duplicateflow benchmark --testset default --pipeline balanced --analyze --export-matrix

  3. Resume from checkpoint:
     $ duplicateflow benchmark --resume checkpoint_20231219_185030.json

[yellow]COMMANDS:[/yellow]
  benchmark     Run pipeline on testset
  compare       Compare multiple pipelines
  list          List testsets or pipelines
  validate      Validate test set integrity

[dim]Use 'duplicateflow <command> --help' for more information[/dim]
"""
    console.print(help_text)
```

#### 2.3 Progress estimation améliorée

**Proposition**:
```python
from datetime import timedelta

class SmartProgressEstimator:
    """Estimate remaining time with learning."""

    def __init__(self):
        self.samples = []
        self.window_size = 10

    def add_sample(self, duration: float):
        """Add timing sample."""
        self.samples.append(duration)
        if len(self.samples) > self.window_size:
            self.samples.pop(0)

    def estimate_remaining(self, completed: int, total: int) -> str:
        """Estimate remaining time."""
        if not self.samples:
            return "Calculating..."

        avg_duration = sum(self.samples) / len(self.samples)
        remaining_items = total - completed
        seconds = avg_duration * remaining_items

        # Format nicely
        td = timedelta(seconds=int(seconds))
        return str(td)

    def get_eta(self) -> str:
        """Get ETA as timestamp."""
        if not self.samples:
            return "Unknown"

        from datetime import datetime
        eta = datetime.now() + timedelta(seconds=int(self.estimate_remaining_seconds()))
        return eta.strftime("%H:%M:%S")
```

---

### 3. ⚡ Optimisations Performance (PRIORITÉ: 🟡 MOYENNE)

#### 3.1 Cache intelligent avec compression

**Proposition**:
```python
import pickle
import lzma
from pathlib import Path

class CompressedFeatureCache:
    """Feature cache with compression."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def save_features(self, video_path: str, features: dict):
        """Save features with compression."""
        cache_file = self.cache_dir / f"{Path(video_path).stem}.xz"

        # Serialize and compress
        data = pickle.dumps(features)
        compressed = lzma.compress(data, preset=6)

        cache_file.write_bytes(compressed)

    def load_features(self, video_path: str) -> Optional[dict]:
        """Load compressed features."""
        cache_file = self.cache_dir / f"{Path(video_path).stem}.xz"

        if not cache_file.exists():
            return None

        # Decompress and deserialize
        compressed = cache_file.read_bytes()
        data = lzma.decompress(compressed)
        return pickle.loads(data)

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        files = list(self.cache_dir.glob("*.xz"))
        total_size = sum(f.stat().st_size for f in files)

        return {
            'files': len(files),
            'total_size_mb': total_size / (1024 * 1024),
            'avg_size_kb': (total_size / len(files) / 1024) if files else 0
        }
```

**Gains**: 60-80% réduction taille cache

#### 3.2 Parallélisation adaptative

**Proposition**:
```python
import psutil
from concurrent.futures import ThreadPoolExecutor

class AdaptiveExecutor:
    """Thread pool that adapts to system load."""

    def __init__(self, max_workers: Optional[int] = None):
        if max_workers is None:
            # Start with conservative estimate
            self.max_workers = max(1, psutil.cpu_count(logical=False) - 1)
        else:
            self.max_workers = max_workers

        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

    def adjust_workers(self):
        """Adjust worker count based on load."""
        cpu_percent = psutil.cpu_percent(interval=1)

        if cpu_percent > 90:
            # System under load, reduce workers
            new_count = max(1, self.max_workers - 1)
        elif cpu_percent < 50:
            # System idle, can add workers
            max_possible = psutil.cpu_count(logical=False)
            new_count = min(max_possible, self.max_workers + 1)
        else:
            return  # Keep current

        if new_count != self.max_workers:
            console.print(f"[dim]Adjusting workers: {self.max_workers} → {new_count}[/dim]")
            self.max_workers = new_count
            # Recreate executor
            self.executor.shutdown(wait=False)
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
```

---

### 4. 🆕 Fonctionnalités Manquantes (PRIORITÉ: 🟡 MOYENNE)

#### 4.1 Comparaison historique

**Proposition**:
```python
class BenchmarkHistory:
    """Track benchmark results over time."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        """Create history tables."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_runs (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                testset TEXT,
                pipeline TEXT,
                precision REAL,
                recall REAL,
                f1_score REAL,
                accuracy REAL,
                duration_seconds REAL,
                git_commit TEXT,
                config_json TEXT
            )
        """)
        self.conn.commit()

    def save_run(self, results: dict):
        """Save benchmark run."""
        self.conn.execute("""
            INSERT INTO benchmark_runs
            (timestamp, testset, pipeline, precision, recall, f1_score,
             accuracy, duration_seconds, git_commit, config_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            results['testset'],
            results['pipeline'],
            results['precision'],
            results['recall'],
            results['f1_score'],
            results['accuracy'],
            results['duration'],
            self._get_git_commit(),
            json.dumps(results['config'])
        ))
        self.conn.commit()

    def get_history(self, testset: str, pipeline: str, limit: int = 10):
        """Get historical results."""
        cursor = self.conn.execute("""
            SELECT * FROM benchmark_runs
            WHERE testset = ? AND pipeline = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (testset, pipeline, limit))
        return cursor.fetchall()

    def show_trend(self, testset: str, pipeline: str):
        """Show performance trend."""
        history = self.get_history(testset, pipeline, limit=20)

        if not history:
            console.print("[yellow]No historical data[/yellow]")
            return

        # Create sparkline chart
        f1_scores = [row[6] for row in history]

        table = Table(title=f"Performance Trend: {pipeline} on {testset}")
        table.add_column("Date", style="cyan")
        table.add_column("F1 Score", style="green")
        table.add_column("Trend", style="yellow")

        for i, row in enumerate(history[:10]):
            date = row[1][:10]
            f1 = row[6]

            # Calculate trend
            if i < len(history) - 1:
                prev_f1 = history[i + 1][6]
                diff = f1 - prev_f1
                trend = "↑" if diff > 0 else "↓" if diff < 0 else "→"
                trend_text = f"{trend} {abs(diff):.2f}%"
            else:
                trend_text = "-"

            table.add_row(date, f"{f1:.2f}%", trend_text)

        console.print(table)
```

**Usage**:
```bash
# Show performance trend
duplicateflow benchmark --history --testset default --pipeline balanced

# Compare with last run
duplicateflow benchmark --testset default --pipeline balanced --compare-with-last
```

#### 4.2 Test Set Validation

**Proposition**:
```python
class TestSetValidator:
    """Validate test set integrity."""

    def validate(self, testset_name: str) -> dict:
        """Run validation checks."""
        results = {
            'valid': True,
            'warnings': [],
            'errors': []
        }

        # Check 1: All videos exist
        missing = self._check_missing_videos(testset_name)
        if missing:
            results['errors'].append(f"Missing {len(missing)} videos")
            results['valid'] = False

        # Check 2: Balanced positive/negative ratio
        ratio = self._check_balance(testset_name)
        if ratio < 0.05 or ratio > 0.3:
            results['warnings'].append(
                f"Unbalanced testset: {ratio:.1%} positive pairs"
            )

        # Check 3: Duplicate pairs
        duplicates = self._check_duplicate_pairs(testset_name)
        if duplicates:
            results['warnings'].append(
                f"Found {len(duplicates)} duplicate pair definitions"
            )

        # Check 4: Video accessibility
        corrupt = self._check_video_integrity(testset_name)
        if corrupt:
            results['errors'].append(f"{len(corrupt)} videos cannot be read")
            results['valid'] = False

        return results

    def show_validation_report(self, testset_name: str):
        """Display validation report."""
        results = self.validate(testset_name)

        if results['valid'] and not results['warnings']:
            console.print(f"\n[green]✓[/green] Testset '{testset_name}' is valid\n")
            return

        console.print(f"\n[bold]Validation Report: {testset_name}[/bold]\n")

        if results['errors']:
            console.print("[red]Errors:[/red]")
            for error in results['errors']:
                console.print(f"  ✗ {error}")

        if results['warnings']:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in results['warnings']:
                console.print(f"  ⚠ {warning}")
```

**Usage**:
```bash
# Validate test set
duplicateflow testset validate default

# Validate all test sets
duplicateflow testset validate --all
```

#### 4.3 Détection de régression

**Proposition**:
```python
class RegressionDetector:
    """Detect performance regressions."""

    def __init__(self, history: BenchmarkHistory):
        self.history = history

    def check_regression(
        self,
        current_results: dict,
        threshold: float = 0.05  # 5% drop is regression
    ) -> Optional[dict]:
        """Check if current run is a regression."""
        testset = current_results['testset']
        pipeline = current_results['pipeline']

        # Get recent baseline (avg of last 5 runs)
        recent = self.history.get_history(testset, pipeline, limit=5)
        if len(recent) < 2:
            return None  # Not enough history

        baseline_f1 = sum(row[6] for row in recent) / len(recent)
        current_f1 = current_results['f1_score']

        drop = baseline_f1 - current_f1

        if drop > threshold * 100:
            return {
                'is_regression': True,
                'baseline_f1': baseline_f1,
                'current_f1': current_f1,
                'drop_percent': drop,
                'severity': 'HIGH' if drop > 10 else 'MEDIUM'
            }

        return {'is_regression': False}

    def show_regression_warning(self, regression: dict):
        """Display regression warning."""
        if not regression['is_regression']:
            return

        severity_colors = {
            'HIGH': 'red',
            'MEDIUM': 'yellow'
        }
        color = severity_colors.get(regression['severity'], 'yellow')

        panel = Panel(
            f"""[{color}]⚠ PERFORMANCE REGRESSION DETECTED[/{color}]

Baseline F1:  {regression['baseline_f1']:.2f}%
Current F1:   {regression['current_f1']:.2f}%
Drop:         {regression['drop_percent']:.2f}% [{color}]↓[/{color}]

Severity: [{color}]{regression['severity']}[/{color}]

[dim]Review recent code changes or pipeline configuration[/dim]
""",
            title="Regression Alert",
            border_style=color
        )
        console.print(panel)
```

**Usage**:
```bash
# Enable regression detection
duplicateflow benchmark --testset default --pipeline balanced --check-regression

# If regression detected, exit with code 1 (useful for CI)
duplicateflow benchmark --testset default --pipeline balanced --fail-on-regression
```

---

### 5. 📊 Formats d'Export (PRIORITÉ: 🟢 BASSE)

#### 5.1 Export HTML interactif

**Proposition**:
```python
from jinja2 import Template

class HTMLReportExporter:
    """Export benchmark results as interactive HTML."""

    TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Report - {{pipeline}} on {{testset}}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: system-ui; margin: 40px; }
        .metric { display: inline-block; margin: 20px; }
        .metric-value { font-size: 48px; font-weight: bold; }
        .confusion-matrix { margin: 40px 0; }
    </style>
</head>
<body>
    <h1>Benchmark Report</h1>
    <p><strong>Pipeline:</strong> {{pipeline}}</p>
    <p><strong>Testset:</strong> {{testset}}</p>
    <p><strong>Date:</strong> {{date}}</p>

    <div class="metrics">
        <div class="metric">
            <div>Precision</div>
            <div class="metric-value" style="color: #00aa00;">{{precision}}%</div>
        </div>
        <div class="metric">
            <div>Recall</div>
            <div class="metric-value" style="color: #0066cc;">{{recall}}%</div>
        </div>
        <div class="metric">
            <div>F1 Score</div>
            <div class="metric-value" style="color: #cc6600;">{{f1_score}}%</div>
        </div>
    </div>

    <div id="confusion-matrix" class="confusion-matrix"></div>

    <script>
    var data = [{
        z: [[{{tn}}, {{fp}}], [{{fn}}, {{tp}}]],
        x: ['Predicted Negative', 'Predicted Positive'],
        y: ['Actual Negative', 'Actual Positive'],
        type: 'heatmap',
        colorscale: 'Viridis'
    }];
    Plotly.newPlot('confusion-matrix', data);
    </script>
</body>
</html>
"""

    def export(self, results: dict, output_path: Path):
        """Generate HTML report."""
        template = Template(self.TEMPLATE)
        html = template.render(**results)
        output_path.write_text(html)
        console.print(f"[green]✓[/green] HTML report: {output_path}")
```

#### 5.2 Export Markdown

**Proposition**:
```python
class MarkdownExporter:
    """Export results as Markdown."""

    def export(self, results: dict, output_path: Path):
        """Generate Markdown report."""
        md = f"""# Benchmark Report

**Pipeline**: {results['pipeline']}
**Testset**: {results['testset']}
**Date**: {results['date']}
**Duration**: {results['duration']:.1f}s

## Metrics

| Metric | Value |
|--------|-------|
| Precision | {results['precision']:.2f}% |
| Recall | {results['recall']:.2f}% |
| F1 Score | {results['f1_score']:.2f}% |
| Accuracy | {results['accuracy']:.2f}% |

## Confusion Matrix

|           | Pred Neg | Pred Pos |
|-----------|----------|----------|
| Act Neg   | {results['tn']} | {results['fp']} |
| Act Pos   | {results['fn']} | {results['tp']} |

## False Positives ({len(results.get('false_positives', []))})

"""
        for fp in results.get('false_positives', []):
            md += f"- `{fp['video1']}` vs `{fp['video2']}` (score: {fp['score']:.1f}%)\n"

        md += f"\n## False Negatives ({len(results.get('false_negatives', []))})\n\n"
        for fn in results.get('false_negatives', []):
            md += f"- `{fn['video1']}` vs `{fn['video2']}` (score: {fn['score']:.1f}%)\n"

        output_path.write_text(md)
        console.print(f"[green]✓[/green] Markdown report: {output_path}")
```

**Usage**:
```bash
# Export as HTML
duplicateflow benchmark --testset default --pipeline balanced --export html

# Export as Markdown
duplicateflow benchmark --testset default --pipeline balanced --export markdown

# Export both
duplicateflow benchmark --testset default --pipeline balanced --export html,markdown,json
```

---

### 6. ⚙️ Système de Configuration (PRIORITÉ: 🟡 MOYENNE)

#### 6.1 Fichier de configuration TOML

**Proposition: duplicateflow.toml**
```toml
[benchmark]
# Default settings
cache_dir = "~/.duplicateflow/cache"
output_dir = "./benchmark_results"
max_workers = 8
checkpoint_interval = 10

[benchmark.limits]
# Resource limits
max_memory_mb = 8192
max_cache_size_mb = 4096

[export]
# Export settings
formats = ["json", "csv", "html"]
include_failures = true
include_timings = true

[profiles.quick]
# Quick test profile
limit = 10
force_recompute = false
analyze = false
export_matrix = false

[profiles.production]
# Full production benchmark
limit = null
force_recompute = true
analyze = true
export_matrix = true
check_regression = true
fail_on_regression = true

[testsets.default]
# Default testset configuration
auto_validate = true
require_balance = true
min_positive_ratio = 0.05
max_positive_ratio = 0.30
```

**Code pour charger config**:
```python
import tomli

class Config:
    """Configuration manager."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path.cwd() / "duplicateflow.toml"

        if config_path.exists():
            self.data = tomli.loads(config_path.read_text())
        else:
            self.data = self._default_config()

    def get(self, key: str, default=None):
        """Get config value with dot notation."""
        parts = key.split('.')
        value = self.data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
        return value if value is not None else default

    def get_profile(self, profile_name: str) -> dict:
        """Get profile configuration."""
        return self.data.get('profiles', {}).get(profile_name, {})
```

**Usage**:
```bash
# Use quick profile
duplicateflow benchmark --profile quick --testset default --pipeline balanced

# Use production profile
duplicateflow benchmark --profile production --testset default --pipeline balanced

# Override config
duplicateflow benchmark --config myconfig.toml --testset default --pipeline balanced
```

---

### 7. 🔍 Debug et Logging (PRIORITÉ: 🟢 BASSE)

#### 7.1 Structured logging

**Proposition**:
```python
import logging
from pathlib import Path
import json

class StructuredLogger:
    """Structured JSON logger."""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.logger = logging.getLogger('duplicateflow.benchmark')

        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_event(self, event_type: str, data: dict):
        """Log structured event."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'data': data
        }
        self.logger.info(json.dumps(event))

    def log_comparison(self, pair_id: str, result: dict):
        """Log comparison result."""
        self.log_event('comparison', {
            'pair_id': pair_id,
            'similarity': result['similarity'],
            'accepted': result['accepted'],
            'duration_ms': result.get('duration_ms')
        })

    def log_error(self, error: Exception, context: dict):
        """Log error with context."""
        self.log_event('error', {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context
        })
```

#### 7.2 Debug mode

**Proposition**:
```bash
# Enable debug mode
duplicateflow benchmark --debug --testset default --pipeline balanced

# This enables:
# - Verbose logging to duplicateflow_debug.log
# - Step-by-step execution with prompts
# - Feature extraction details
# - Memory profiling
```

```python
class DebugMode:
    """Debug mode utilities."""

    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.step_count = 0

    def step(self, description: str):
        """Execute debug step."""
        if not self.enabled:
            return

        self.step_count += 1
        console.print(f"\n[cyan]DEBUG STEP {self.step_count}:[/cyan] {description}")

        if Confirm.ask("Continue?", default=True):
            return
        else:
            console.print("[yellow]Execution paused[/yellow]")
            sys.exit(0)

    def inspect(self, obj: Any, name: str):
        """Inspect object."""
        if not self.enabled:
            return

        console.print(f"\n[cyan]INSPECT {name}:[/cyan]")
        console.print(obj)
        input("Press Enter to continue...")
```

#### 7.3 Performance profiling

**Proposition**:
```python
import cProfile
import pstats
from io import StringIO

class ProfileManager:
    """Performance profiling manager."""

    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.profiler = cProfile.Profile() if enabled else None

    def __enter__(self):
        """Start profiling."""
        if self.enabled:
            self.profiler.enable()
        return self

    def __exit__(self, *args):
        """Stop profiling and show results."""
        if self.enabled:
            self.profiler.disable()
            self.show_results()

    def show_results(self):
        """Display profiling results."""
        s = StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions

        console.print("\n[bold]Performance Profile (Top 20):[/bold]")
        console.print(s.getvalue())
```

**Usage**:
```bash
# Enable profiling
duplicateflow benchmark --profile-performance --testset default --pipeline balanced
```

---

### 8. 🧩 Plugin System (PRIORITÉ: 🟢 BASSE)

#### 8.1 Test Set Loaders

**Proposition**:
```python
from abc import ABC, abstractmethod

class TestSetLoader(ABC):
    """Base class for test set loaders."""

    @abstractmethod
    def load(self, source: str) -> List[Tuple[str, str, bool]]:
        """Load test set from source."""
        pass

class JSONTestSetLoader(TestSetLoader):
    """Load from JSON file."""

    def load(self, source: str) -> List[Tuple[str, str, bool]]:
        data = json.loads(Path(source).read_text())
        return [(p['video1'], p['video2'], p['is_duplicate']) for p in data['pairs']]

class CSVTestSetLoader(TestSetLoader):
    """Load from CSV file."""

    def load(self, source: str) -> List[Tuple[str, str, bool]]:
        import csv
        pairs = []
        with open(source) as f:
            reader = csv.DictReader(f)
            for row in reader:
                pairs.append((row['video1'], row['video2'], row['is_duplicate'] == 'true'))
        return pairs

class TestSetLoaderRegistry:
    """Registry for test set loaders."""

    def __init__(self):
        self.loaders = {}

    def register(self, format: str, loader: TestSetLoader):
        """Register loader."""
        self.loaders[format] = loader

    def load(self, source: str, format: str = None) -> List[Tuple[str, str, bool]]:
        """Load test set."""
        if format is None:
            format = Path(source).suffix[1:]  # .json -> json

        loader = self.loaders.get(format)
        if not loader:
            raise ValueError(f"No loader for format: {format}")

        return loader.load(source)
```

**Usage**:
```bash
# Load from JSON
duplicateflow benchmark --testset-file testset.json --pipeline balanced

# Load from CSV
duplicateflow benchmark --testset-file testset.csv --format csv --pipeline balanced
```

#### 8.2 Custom Analyzers

**Proposition**:
```python
class Analyzer(ABC):
    """Base class for custom analyzers."""

    @abstractmethod
    def analyze(self, results: BenchmarkResults) -> dict:
        """Analyze results."""
        pass

class DurationAnalyzer(Analyzer):
    """Analyze comparison durations."""

    def analyze(self, results: BenchmarkResults) -> dict:
        durations = [r['duration_ms'] for r in results.individual_results]
        return {
            'mean': statistics.mean(durations),
            'median': statistics.median(durations),
            'p95': statistics.quantiles(durations, n=20)[18],  # 95th percentile
            'outliers': [d for d in durations if d > statistics.mean(durations) * 3]
        }

class AnalyzerRegistry:
    """Registry for analyzers."""

    def __init__(self):
        self.analyzers = {}

    def register(self, name: str, analyzer: Analyzer):
        """Register analyzer."""
        self.analyzers[name] = analyzer

    def run_all(self, results: BenchmarkResults) -> dict:
        """Run all analyzers."""
        analyses = {}
        for name, analyzer in self.analyzers.items():
            analyses[name] = analyzer.analyze(results)
        return analyses
```

---

### 9. 🔄 Integration avec DuplicateFlow SDK (PRIORITÉ: 🔴 HAUTE)

#### Problème actuel
- Import direct de classes internes
- Pas d'utilisation de l'API publique DuplicateFlow

#### Proposition: Utiliser SDK officiel

```python
# Au lieu de:
from duplicateflow.pipeline.pipeline import Pipeline

# Utiliser:
from duplicateflow import Pipeline, StorageManager, PipelineStore

# Au lieu de:
storage_manager = StorageManager(db_path)

# Utiliser API de haut niveau:
from duplicateflow.sdk import BenchmarkRunner

class BenchmarkRunner:
    """High-level API for benchmarking."""

    def __init__(
        self,
        cache_dir: Path = None,
        max_workers: int = None
    ):
        self.cache_dir = cache_dir or Path.home() / ".duplicateflow"
        self.max_workers = max_workers or (os.cpu_count() or 4)
        self.storage = StorageManager(self.cache_dir / "cache.db")
        self.pipeline_store = PipelineStore(self.cache_dir / "pipelines.db")

    def run_benchmark(
        self,
        testset: TestSet,
        pipeline: Pipeline,
        on_progress: Optional[Callable] = None
    ) -> BenchmarkResults:
        """Run benchmark with progress callback."""
        # Implementation with proper API
        pass
```

---

### 10. 📦 Packaging et Distribution (PRIORITÉ: 🟢 BASSE)

#### 10.1 Entry point PyPI

**setup.py**:
```python
setup(
    name='duplicateflow',
    # ...
    entry_points={
        'console_scripts': [
            'duplicateflow=duplicateflow.cli:main',
        ],
    },
)
```

**Usage après installation**:
```bash
# Après: pip install duplicateflow
duplicateflow benchmark --testset default --pipeline balanced
```

#### 10.2 Commandes intégrées

```bash
# Liste toutes les commandes
duplicateflow --help

# Commandes proposées:
duplicateflow benchmark      # Run benchmark
duplicateflow compare        # Compare pipelines
duplicateflow testset        # Manage testsets
duplicateflow pipeline       # Manage pipelines
duplicateflow cache          # Cache management
duplicateflow validate       # Validate configuration
```

---

### 11. 🔍 Recherche dans Arborescences (PRIORITÉ: 🔴 HAUTE) ⭐ NEW

#### Problème actuel
Le CLI actuel ne permet que de:
- Comparer 2 vidéos spécifiques
- Benchmarker sur un test set prédéfini

**Mais ne permet PAS de**:
- Scanner un dossier pour trouver tous les duplicates
- Détecter scènes courtes incluses dans vidéos longues
- Rechercher où une vidéo apparaît dans une arborescence
- Localiser précisément les timestamps de correspondance

#### Proposition: Commandes de recherche avancée

##### 11.1 Scan de Dossier pour Duplicates

**Commande**: `duplicateflow scan`

```bash
# Scan simple - Trouve tous les duplicates dans un dossier
duplicateflow scan /path/to/videos --pipeline balanced

# Scan récursif avec filtres
duplicateflow scan /path/to/videos --recursive --extensions mp4,avi,mkv --pipeline thorough

# Scan avec limite de taille
duplicateflow scan /path/to/videos --min-size 10MB --max-size 5GB

# Scan avec grouping automatique
duplicateflow scan /path/to/videos --group-duplicates --output duplicates.json
```

**Code implémentation**:
```python
class DirectoryScanCommand:
    """Scan directory for duplicate videos."""

    def __init__(self, pipeline: Pipeline, console: Console):
        self.pipeline = pipeline
        self.console = console
        self.fingerprint_index = FingerprintIndex()

    def scan(
        self,
        directory: Path,
        recursive: bool = True,
        extensions: List[str] = None,
        min_size: int = 0,
        max_size: int = None,
        group_duplicates: bool = True
    ) -> List[DuplicateGroup]:
        """Scan directory for duplicates."""

        # 1. Découvrir toutes les vidéos
        videos = self._discover_videos(
            directory,
            recursive=recursive,
            extensions=extensions or ['mp4', 'avi', 'mkv', 'mov'],
            min_size=min_size,
            max_size=max_size
        )

        console.print(f"[cyan]Discovered {len(videos)} videos[/cyan]")

        # 2. Indexer via Fingerprint Index (O(N) au lieu de O(N²))
        console.print("[yellow]Building fingerprint index...[/yellow]")

        with Progress() as progress:
            task = progress.add_task("Indexing", total=len(videos))

            for video in videos:
                fingerprint = self._extract_fingerprint(video)
                self.fingerprint_index.add(video, fingerprint)
                progress.advance(task)

        # 3. Trouver candidats via LSH (Locality-Sensitive Hashing)
        console.print("[yellow]Finding duplicate candidates...[/yellow]")
        candidate_pairs = self.fingerprint_index.find_all_duplicates(
            threshold=self.pipeline.global_threshold
        )

        console.print(f"[cyan]Found {len(candidate_pairs)} candidate pairs[/cyan]")

        # 4. Vérification précise avec pipeline complet
        console.print("[yellow]Verifying with full pipeline...[/yellow]")

        duplicates = []
        with Progress() as progress:
            task = progress.add_task("Verifying", total=len(candidate_pairs))

            for video1, video2 in candidate_pairs:
                result = self.pipeline.compare(video1, video2)

                if result.accepted:
                    duplicates.append({
                        'video1': video1,
                        'video2': video2,
                        'similarity': result.global_score,
                        'details': result.individual_results
                    })

                progress.advance(task)

        # 5. Grouper en clusters si demandé
        if group_duplicates:
            groups = self._group_duplicates(duplicates)
            return groups

        return duplicates

    def _discover_videos(
        self,
        directory: Path,
        recursive: bool,
        extensions: List[str],
        min_size: int,
        max_size: int
    ) -> List[Path]:
        """Discover all videos in directory."""
        videos = []

        pattern = "**/*" if recursive else "*"

        for ext in extensions:
            for video_path in directory.glob(f"{pattern}.{ext}"):
                if not video_path.is_file():
                    continue

                size = video_path.stat().st_size

                if size < min_size:
                    continue

                if max_size and size > max_size:
                    continue

                videos.append(video_path)

        return videos

    def _group_duplicates(self, duplicates: List[dict]) -> List[DuplicateGroup]:
        """Group duplicates into clusters using Union-Find."""
        from collections import defaultdict

        # Union-Find structure
        parent = {}

        def find(x):
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Build clusters
        for dup in duplicates:
            union(dup['video1'], dup['video2'])

        # Group by root
        clusters = defaultdict(list)
        for dup in duplicates:
            root = find(dup['video1'])
            clusters[root].append(dup)

        # Convert to DuplicateGroup objects
        groups = []
        for root, cluster_dups in clusters.items():
            videos = set()
            for dup in cluster_dups:
                videos.add(dup['video1'])
                videos.add(dup['video2'])

            groups.append(DuplicateGroup(
                videos=list(videos),
                pairs=cluster_dups,
                representative=root  # Smallest or best quality
            ))

        return groups

    def show_results(self, groups: List[DuplicateGroup]):
        """Display results as Rich table."""

        table = Table(title=f"Duplicate Groups Found: {len(groups)}")
        table.add_column("Group", style="cyan")
        table.add_column("Videos", style="green")
        table.add_column("Total Size", style="yellow")
        table.add_column("Potential Savings", style="red")

        total_savings = 0

        for i, group in enumerate(groups, 1):
            # Calculate sizes
            sizes = [Path(v).stat().st_size for v in group.videos]
            total_size = sum(sizes)
            savings = total_size - max(sizes)  # Keep largest, delete rest
            total_savings += savings

            table.add_row(
                f"#{i}",
                f"{len(group.videos)} videos",
                f"{total_size / (1024**3):.2f} GB",
                f"{savings / (1024**3):.2f} GB"
            )

        console.print(table)

        console.print(f"\n[bold green]Total potential savings: {total_savings / (1024**3):.2f} GB[/bold green]")
```

**Output exemple**:
```bash
$ duplicateflow scan /media/videos --recursive --pipeline balanced

Discovered 1,247 videos
Building fingerprint index... ━━━━━━━━━━━━━━━━━━━━━━━━ 100%
Found 89 candidate pairs
Verifying with full pipeline... ━━━━━━━━━━━━━━━━━━━━━━━━ 100%

Duplicate Groups Found: 12
┌───────┬───────────┬────────────┬───────────────────┐
│ Group │ Videos    │ Total Size │ Potential Savings │
├───────┼───────────┼────────────┼───────────────────┤
│ #1    │ 3 videos  │ 4.25 GB    │ 2.80 GB           │
│ #2    │ 2 videos  │ 1.80 GB    │ 0.90 GB           │
│ #3    │ 5 videos  │ 8.50 GB    │ 6.80 GB           │
│ ...   │ ...       │ ...        │ ...               │
└───────┴───────────┴────────────┴───────────────────┘

Total potential savings: 25.40 GB

Results saved to: duplicates_20251219_183045.json
```

##### 11.2 Détection de Scènes Incluses (Subsequence Search) ⭐

**Commande**: `duplicateflow find-scenes`

```bash
# Trouver où A.avi apparaît dans une arborescence
duplicateflow find-scenes /path/to/short_clip.mp4 --in /path/to/videos --pipeline balanced

# Avec timestamps précis
duplicateflow find-scenes short_clip.mp4 --in /videos --show-timestamps --min-duration 5

# Mode batch - Scanner plusieurs courts clips
duplicateflow find-scenes /clips/*.mp4 --in /archive --batch
```

**Code implémentation**:
```python
class SubsequenceSearchCommand:
    """Find short videos included in longer videos."""

    def __init__(self, pipeline: Pipeline, console: Console):
        self.pipeline = pipeline
        self.console = console

    def find_scenes(
        self,
        query_video: Path,
        search_in: Path,
        min_duration: float = 3.0,
        show_timestamps: bool = True,
        recursive: bool = True
    ) -> List[SceneMatch]:
        """Find where query_video appears in search_in directory."""

        # 1. Extraire features du query video
        console.print(f"[cyan]Analyzing query video: {query_video.name}[/cyan]")

        query_features = self._extract_scene_features(query_video)
        query_duration = self._get_duration(query_video)

        console.print(f"  Duration: {query_duration:.1f}s")
        console.print(f"  Features: {len(query_features)} segments")

        # 2. Découvrir vidéos candidates (plus longues que query)
        candidates = self._discover_longer_videos(
            search_in,
            min_duration=query_duration + min_duration,
            recursive=recursive
        )

        console.print(f"\n[yellow]Searching in {len(candidates)} videos...[/yellow]")

        # 3. Recherche par sliding window
        matches = []

        with Progress() as progress:
            task = progress.add_task("Scanning", total=len(candidates))

            for candidate in candidates:
                candidate_matches = self._find_in_video(
                    query_video,
                    query_features,
                    query_duration,
                    candidate,
                    show_timestamps
                )

                matches.extend(candidate_matches)
                progress.advance(task)

        return matches

    def _find_in_video(
        self,
        query_video: Path,
        query_features: List[dict],
        query_duration: float,
        target_video: Path,
        show_timestamps: bool
    ) -> List[SceneMatch]:
        """Find query video within target using sliding window."""

        target_duration = self._get_duration(target_video)
        window_size = query_duration
        step_size = window_size * 0.25  # 75% overlap for precision

        matches = []
        current_time = 0.0

        while current_time + window_size <= target_duration:
            # Compare query avec window actuelle
            result = self.pipeline.compare(
                query_video,
                target_video,
                start_time=current_time,
                duration=window_size
            )

            if result.accepted:
                # Match trouvé!
                match = SceneMatch(
                    query_video=query_video,
                    target_video=target_video,
                    start_time=current_time,
                    end_time=current_time + window_size,
                    similarity=result.global_score,
                    confidence=self._calculate_confidence(result)
                )

                matches.append(match)

                # Skip ahead pour éviter matches qui se chevauchent
                current_time += window_size
            else:
                current_time += step_size

        # Merge overlapping matches
        if matches:
            matches = self._merge_overlapping_matches(matches)

        return matches

    def _merge_overlapping_matches(self, matches: List[SceneMatch]) -> List[SceneMatch]:
        """Merge overlapping matches into continuous segments."""
        if not matches:
            return []

        # Sort by start time
        matches.sort(key=lambda m: m.start_time)

        merged = [matches[0]]

        for current in matches[1:]:
            last = merged[-1]

            # Si overlap significatif (>50%)
            overlap = min(last.end_time, current.end_time) - max(last.start_time, current.start_time)
            last_duration = last.end_time - last.start_time

            if overlap / last_duration > 0.5:
                # Merge: extend last match
                last.end_time = max(last.end_time, current.end_time)
                last.similarity = max(last.similarity, current.similarity)
            else:
                merged.append(current)

        return merged

    def show_results(self, query_video: Path, matches: List[SceneMatch]):
        """Display scene matches with timestamps."""

        if not matches:
            console.print(f"\n[yellow]No matches found for {query_video.name}[/yellow]")
            return

        console.print(f"\n[bold green]Found {len(matches)} matches for {query_video.name}[/bold green]\n")

        table = Table(title="Scene Matches")
        table.add_column("Target Video", style="cyan")
        table.add_column("Time Range", style="yellow")
        table.add_column("Duration", style="green")
        table.add_column("Similarity", style="magenta")

        for match in matches:
            time_range = f"{self._format_time(match.start_time)} → {self._format_time(match.end_time)}"
            duration = match.end_time - match.start_time

            table.add_row(
                match.target_video.name,
                time_range,
                f"{duration:.1f}s",
                f"{match.similarity:.1f}%"
            )

        console.print(table)

        # Génère commandes FFmpeg pour extraction
        console.print("\n[dim]FFmpeg commands to extract scenes:[/dim]\n")
        for i, match in enumerate(matches, 1):
            cmd = (
                f"ffmpeg -i '{match.target_video}' "
                f"-ss {match.start_time:.2f} -t {match.end_time - match.start_time:.2f} "
                f"-c copy 'scene_{i}_{match.target_video.stem}.mp4'"
            )
            console.print(f"  {cmd}")

    def _format_time(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
```

**Output exemple**:
```bash
$ duplicateflow find-scenes short_intro.mp4 --in /archive/movies --show-timestamps

Analyzing query video: short_intro.mp4
  Duration: 15.3s
  Features: 46 segments

Searching in 234 videos...
Scanning ━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

Found 3 matches for short_intro.mp4

Scene Matches
┌─────────────────────┬──────────────────────┬──────────┬────────────┐
│ Target Video        │ Time Range           │ Duration │ Similarity │
├─────────────────────┼──────────────────────┼──────────┼────────────┤
│ movie_full.mp4      │ 00:02:35 → 00:02:50  │ 15.0s    │ 96.8%      │
│ compilation_01.avi  │ 01:15:20 → 01:15:35  │ 15.0s    │ 94.2%      │
│ remastered_HD.mkv   │ 00:03:10 → 00:03:25  │ 15.0s    │ 98.5%      │
└─────────────────────┴──────────────────────┴──────────┴────────────┘

FFmpeg commands to extract scenes:

  ffmpeg -i '/archive/movies/movie_full.mp4' -ss 155.00 -t 15.00 -c copy 'scene_1_movie_full.mp4'
  ffmpeg -i '/archive/movies/compilation_01.avi' -ss 4520.00 -t 15.00 -c copy 'scene_2_compilation_01.mp4'
  ffmpeg -i '/archive/movies/remastered_HD.mkv' -ss 190.00 -t 15.00 -c copy 'scene_3_remastered_HD.mp4'
```

##### 11.3 Recherche Bidirectionnelle (Mutual Search)

**Commande**: `duplicateflow cross-search`

```bash
# Comparer 2 dossiers entre eux
duplicateflow cross-search /folder_A /folder_B --pipeline balanced

# Trouver vidéos de A qui sont dans B (et inversement)
duplicateflow cross-search /new_downloads /archive --show-direction
```

**Use case**: Tu as téléchargé plein de vidéos, tu veux savoir lesquelles sont déjà dans ton archive.

---

### 12. ⚙️ Gestion et Configuration des Pipelines (PRIORITÉ: 🔴 HAUTE) ⭐ NEW

#### Problème actuel
- Pas de moyen de créer/éditer des pipelines via CLI
- Pas de sauvegarde/chargement de configurations
- Documentation algorithmes insuffisante pour débutants
- Configuration complexe sans guide

**Mais devrait permettre**:
- Créer pipelines custom facilement
- Sauvegarder/charger configs YAML
- Comprendre chaque algorithme et ses paramètres
- Valider configuration avant exécution

#### Proposition: Commandes de gestion de pipelines

##### 12.1 Création de Pipeline Interactif

**Commande**: `duplicateflow pipeline create`

```bash
# Mode interactif guidé (pour débutants)
duplicateflow pipeline create --interactive

# Mode expert (YAML direct)
duplicateflow pipeline create --name my_pipeline --edit
```

**Mode interactif - Flow complet**:
```
$ duplicateflow pipeline create --interactive

🎯 Pipeline Creator - Mode Guidé

Nom du pipeline: my_custom_pipeline

📊 Quel est votre cas d'usage?
  1. Duplicates exacts (même vidéo, qualités différentes)
  2. Scènes similaires (intro, générique, extraits)
  3. Vidéos perceptuellement similaires
  4. Détection générique (équilibré)
Choix [1-4]: 1

✓ Cas d'usage: Duplicates exacts

📋 Algorithmes recommandés pour ce cas:
  • frame_hash (rapide, précis pour duplicates exacts)
  • color_histogram (complémentaire pour variations)
  • dct_coefficients (robuste aux re-encodages)

Voulez-vous:
  [1] Utiliser configuration recommandée (rapide)
  [2] Personnaliser les algorithmes
Choix [1-2]: 2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 Configuration: frame_hash

Description:
  Compare les hashes de frames vidéo. Très rapide et précis pour
  détecter duplicates exacts ou quasi-exacts (re-encodages).

Paramètres:

  threshold (70-95, défaut: 85)
    Seuil de similarité minimum.
    • 95: Très strict (uniquement duplicates quasi-parfaits)
    • 85: Équilibré (duplicates avec variations légères) ✓
    • 70: Permissif (vidéos très similaires)

  weight (0.0-1.0, défaut: 0.4)
    Importance dans le score global.
    Plus élevé = plus d'influence sur la décision finale.

Seuil [85]: 90
Weight [0.4]: 0.5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 Configuration: color_histogram

Description:
  Analyse la distribution des couleurs. Robuste aux petites
  modifications mais peut donner faux positifs sur vidéos
  avec palettes similaires.

Paramètres:

  threshold (60-90, défaut: 70)
    • 90: Très strict
    • 70: Équilibré ✓
    • 60: Permissif

  weight (0.0-1.0, défaut: 0.3)

Seuil [70]:
Weight [0.3]:

✓ Configuration color_histogram acceptée (défauts)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Résumé de votre pipeline:

Pipeline: my_custom_pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Algorithmes (2):
  1. frame_hash
     • threshold: 90
     • weight: 0.5 (50% du score)

  2. color_histogram
     • threshold: 70
     • weight: 0.3 (30% du score)

Seuil global: 75.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Actions:
  [1] Sauvegarder et tester sur 2 vidéos
  [2] Modifier configuration
  [3] Sauvegarder sans tester
  [4] Annuler

Choix [1-4]: 1

💾 Pipeline sauvegardé: ~/.duplicateflow/pipelines/my_custom_pipeline.yaml

🧪 Test du pipeline sur 2 vidéos

Vidéo 1: /path/to/video1.mp4
Vidéo 2: /path/to/video2.mp4

Comparaison en cours...

Résultats:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frame_hash:        92.5% ✓ (seuil: 90)
color_histogram:   85.3% ✓ (seuil: 70)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Score global:      89.1% ✓
Décision:          DUPLICATE (seuil global: 75)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Pipeline my_custom_pipeline prêt à l'emploi!

Utilisation:
  duplicateflow scan /videos --pipeline my_custom_pipeline
```

##### 12.2 Sauvegarde/Chargement YAML

**Format YAML simple et clair**:

```yaml
# my_custom_pipeline.yaml
name: my_custom_pipeline
description: Pipeline optimisé pour duplicates exacts avec variations légères

# Seuil global (70-95, recommandé: 75)
# Décision finale: match si score global >= threshold
global_threshold: 75.0

# Liste des algorithmes à utiliser
algorithms:
  # 1. Frame Hash - Comparaison rapide de frames
  - name: frame_hash
    weight: 0.5  # 50% du score global
    threshold: 90  # Seuil pour cet algo
    params:
      sample_rate: 1  # 1 frame/sec
      hash_size: 8    # Taille du hash

  # 2. Color Histogram - Distribution couleurs
  - name: color_histogram
    weight: 0.3  # 30% du score global
    threshold: 70
    params:
      bins: 32  # Précision histogramme

  # 3. DCT Coefficients - Robuste aux re-encodages
  - name: dct_coefficients
    weight: 0.2  # 20% du score global
    threshold: 75
    params:
      block_size: 8

# Pré-validation (optionnel)
# Filtre avant comparaison pour économiser du temps
pre_validators:
  - name: length_validator
    tolerance_percent: 10.0  # ±10% de durée

# Post-validation (optionnel)
# Filtre après comparaison pour affiner résultats
post_validators:
  - name: min_score_validator
    algorithm: frame_hash
    min_score: 80.0

# Analyse partielle (optionnel)
# analyze_duration: 60.0  # Analyser seulement 60 premières secondes
# analyze_from_start: true
```

**Commandes de gestion**:
```bash
# Lister pipelines disponibles
duplicateflow pipeline list

# Output:
# Pipelines Disponibles
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Nom                 │ Type    │ Algos │ Fichier
# ────────────────────┼─────────┼───────┼──────────────────
# my_custom_pipeline  │ Custom  │ 3     │ ~/.duplicateflow/pipelines/my_custom_pipeline.yaml
# balanced            │ Preset  │ 4     │ (builtin)
# thorough            │ Preset  │ 6     │ (builtin)

# Afficher détails d'un pipeline
duplicateflow pipeline show my_custom_pipeline

# Valider un pipeline YAML
duplicateflow pipeline validate my_custom_pipeline.yaml

# Charger depuis fichier
duplicateflow scan /videos --pipeline-file my_custom_pipeline.yaml

# Éditer un pipeline existant
duplicateflow pipeline edit my_custom_pipeline
```

##### 12.3 Documentation Algorithmes pour Débutants

**Commande**: `duplicateflow algorithms explain`

```bash
# Lister tous les algorithmes avec descriptions courtes
duplicateflow algorithms list

# Output:
# Algorithmes Disponibles (16)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Nom                  │ Catégorie    │ Vitesse │ Usage
# ─────────────────────┼──────────────┼─────────┼────────────────
# frame_hash           │ Statistical  │ ⚡⚡⚡    │ Duplicates exacts
# color_histogram      │ Statistical  │ ⚡⚡⚡    │ Variations couleur
# ssim                 │ Perceptual   │ ⚡⚡     │ Qualité visuelle
# dct_coefficients     │ Perceptual   │ ⚡⚡     │ Re-encodages
# feature_matching     │ Structural   │ ⚡      │ Objets similaires
# optical_flow         │ Temporal     │ ⚡      │ Mouvement
# audio_fingerprint    │ Audio        │ ⚡⚡     │ Piste audio

# Explication détaillée d'un algorithme
duplicateflow algorithms explain frame_hash

# Output:
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 frame_hash - Hash de Frames
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# DESCRIPTION:
#   Compare les hashes perceptuels de frames vidéo échantillonnées.
#   Génère une empreinte compacte de chaque frame et compare la
#   similarité entre empreintes.
#
# QUAND L'UTILISER:
#   ✓ Duplicates exacts ou quasi-exacts
#   ✓ Re-encodages avec mêmes frames
#   ✓ Scan rapide de grandes bibliothèques
#   ✗ Vidéos avec crop/zoom différents
#   ✗ Scènes très courtes (<5s)
#
# VITESSE: ⚡⚡⚡ Très rapide (~30 vidéos/sec sur CPU standard)
#
# PARAMÈTRES:
#
#   threshold (70-95, défaut: 85)
#     Seuil de similarité minimum pour accepter un match.
#
#     Recommandations:
#     • 95: Uniquement duplicates quasi-parfaits
#            Use case: Détecter copies exactes
#     • 85: Équilibré - duplicates avec variations légères ✓
#            Use case: Usage général, re-encodages
#     • 70: Permissif - vidéos très similaires
#            Use case: Trouver variations importantes
#
#   weight (0.0-1.0, défaut: 0.4)
#     Importance de cet algorithme dans le score global du pipeline.
#
#     Si weight=0.4 et threshold=85:
#     • L'algo contribue 40% au score final
#     • Si score algo < 85, contribue 0 au score global
#     • Si score algo >= 85, contribue (score * 0.4) au global
#
#   sample_rate (0.5-5, défaut: 1)
#     Nombre de frames analysées par seconde.
#
#     • 5: Très précis mais plus lent
#     • 1: Équilibré ✓
#     • 0.5: Rapide mais moins précis
#
#   hash_size (4-16, défaut: 8)
#     Taille du hash perceptuel (en bits).
#
#     • 16: Très précis, détecte petites différences
#     • 8: Équilibré ✓
#     • 4: Rapide, tolère plus de variations
#
# EXEMPLES DE CONFIGURATION:
#
#   # Configuration stricte (duplicates parfaits uniquement)
#   - name: frame_hash
#     threshold: 95
#     weight: 0.6
#     params:
#       sample_rate: 2
#       hash_size: 12
#
#   # Configuration permissive (variations importantes)
#   - name: frame_hash
#     threshold: 70
#     weight: 0.3
#     params:
#       sample_rate: 0.5
#       hash_size: 6
#
#   # Configuration équilibrée (recommandée)
#   - name: frame_hash
#     threshold: 85
#     weight: 0.4
#     params:
#       sample_rate: 1
#       hash_size: 8
#
# COMBINAISONS RECOMMANDÉES:
#   • frame_hash + color_histogram → Duplicates exacts robustes
#   • frame_hash + dct_coefficients → Re-encodages
#   • frame_hash + ssim → Qualité différente
#
# PERFORMANCES TYPIQUES:
#   • Précision: 95% sur duplicates exacts
#   • Recall: 90% (manque vidéos avec crop/zoom)
#   • Vitesse: ~30 vidéos/sec (1h de vidéo en 2 min)
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Guide pour débutants
duplicateflow algorithms guide

# Output: Guide interactif qui pose des questions
# et recommande les meilleurs algorithmes
```

##### 12.4 Validation de Configuration

**Commande**: `duplicateflow pipeline validate`

```bash
# Valider un fichier YAML
duplicateflow pipeline validate my_pipeline.yaml

# Output si erreurs:
# ❌ Erreurs de validation:
#
# Ligne 8: weight invalide
#   └─ weight=1.5 doit être entre 0.0 et 1.0
#
# Ligne 15: algorithme inconnu
#   └─ 'frame_hass' n'existe pas. Vouliez-vous dire 'frame_hash'?
#
# Ligne 22: paramètre invalide
#   └─ 'sample_rat' n'est pas un paramètre de frame_hash
#       Paramètres disponibles: sample_rate, hash_size
#
# ⚠ Avertissements:
#
# Ligne 5: global_threshold très permissif
#   └─ threshold=60 est très bas. Risque de faux positifs.
#       Recommandé: 70-85
#
# Ligne 10: weights ne somment pas à 1.0
#   └─ Total weights: 0.7 (frame_hash: 0.4 + color: 0.3)
#       Recommandé: ajuster pour sommer à 1.0

# Valider avec suggestions d'amélioration
duplicateflow pipeline validate my_pipeline.yaml --suggest

# Output:
# ✓ Configuration valide
#
# 💡 Suggestions d'amélioration:
#
# 1. Optimiser weights
#    Actuellement: frame_hash=0.4, color=0.3 (total: 0.7)
#    Suggéré: frame_hash=0.57, color=0.43 (normalisé à 1.0)
#
# 2. Ajouter validator
#    Votre pipeline détecte duplicates exacts.
#    Suggéré: Ajouter LengthValidator pour filtrer vidéos
#             de durées très différentes (gain de vitesse: ~30%)
#
# 3. Ajuster sample_rate
#    sample_rate=5 est très élevé pour frame_hash.
#    Suggéré: sample_rate=1 (gain vitesse: 5x, précision: -2%)
```

##### 12.5 Templates de Pipelines

**Commande**: `duplicateflow pipeline template`

```bash
# Lister templates disponibles
duplicateflow pipeline templates

# Output:
# Templates de Pipelines
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Nom                │ Description
# ───────────────────┼────────────────────────────────────
# exact_duplicates   │ Détecter copies exactes (re-encodages)
# similar_scenes     │ Scènes similaires (intros, génériques)
# quality_variants   │ Même vidéo, qualités différentes
# audio_match        │ Même piste audio, vidéo différente
# fast_scan          │ Scan rapide, précision moyenne
# thorough_scan      │ Scan précis, plus lent
#
# Créer depuis template
duplicateflow pipeline create --template exact_duplicates --name my_exact

# Afficher un template
duplicateflow pipeline template show exact_duplicates
```

**Impact utilisateur**: 🌟🌟🌟🌟🌟 (essentiel)
**Effort dev**: 4 jours
**ROI**: Maximum

---

### 13. 🏗️ Infrastructure Production-Ready (PRIORITÉ: 🔴 HAUTE) ⭐ NEW

#### Problème actuel
Pour être production-ready et prêt pour une GUI future, il manque:
- **Tests**: Pas de suite de tests complète (unitaires, intégration, E2E)
- **Architecture GUI-ready**: Code couplé au CLI, pas de séparation logique/présentation
- **Documentation technique**: Pas de génération automatique, pas de sync code↔docs
- **Qualité code**: Pas de CI/CD, pas de linting automatique, pas de coverage
- **Rich UI**: Console basique, pas d'exploitation complète de Rich

#### Proposition: Infrastructure complète pour production

##### 13.1 Architecture MVC/Clean pour GUI Future

**Principe**: Séparer **Logique métier** (core) de **Présentation** (CLI/GUI)

```
duplicateflow/
├── duplicateflow/
│   ├── core/                    # LOGIQUE MÉTIER (réutilisable GUI/CLI)
│   │   ├── services/           # Services métier purs
│   │   │   ├── scan_service.py          # Logique scan dossiers
│   │   │   ├── scene_search_service.py  # Logique find-scenes
│   │   │   ├── pipeline_service.py      # Logique pipeline management
│   │   │   └── benchmark_service.py     # Logique benchmark
│   │   │
│   │   ├── models/             # Modèles de données
│   │   │   ├── scan_result.py
│   │   │   ├── scene_match.py
│   │   │   ├── pipeline_config.py
│   │   │   └── benchmark_result.py
│   │   │
│   │   └── interfaces/         # Contrats (ABC)
│   │       ├── i_progress_reporter.py   # Interface pour progress
│   │       ├── i_ui_adapter.py          # Interface pour UI
│   │       └── i_storage.py             # Interface storage
│   │
│   ├── cli/                     # PRÉSENTATION CLI (Rich)
│   │   ├── adapters/           # Adaptateurs Rich
│   │   │   ├── rich_progress.py         # Implémente IProgressReporter
│   │   │   ├── rich_ui.py               # Implémente IUIAdapter
│   │   │   └── rich_display.py          # Rich tables, panels, etc.
│   │   │
│   │   ├── commands/           # Commandes CLI (thin wrappers)
│   │   │   ├── scan_command.py          # Appelle ScanService
│   │   │   ├── find_scenes_command.py   # Appelle SceneSearchService
│   │   │   └── pipeline_command.py      # Appelle PipelineService
│   │   │
│   │   └── ui/                 # Composants UI Rich
│   │       ├── dashboards/
│   │       │   ├── scan_dashboard.py    # Live dashboard scan
│   │       │   ├── benchmark_dashboard.py
│   │       │   └── pipeline_creator_ui.py
│   │       │
│   │       ├── widgets/
│   │       │   ├── progress_bars.py
│   │       │   ├── tables.py
│   │       │   ├── panels.py
│   │       │   └── prompts.py          # Prompts interactifs
│   │       │
│   │       └── themes/
│   │           ├── default_theme.py
│   │           └── high_contrast_theme.py
│   │
│   └── gui/                     # FUTURE GUI (prêt à accueillir)
│       ├── __init__.py
│       ├── adapters/           # Adaptateurs GUI (Qt/Tkinter/etc)
│       │   ├── qt_progress.py           # Implémente IProgressReporter
│       │   └── qt_ui.py                 # Implémente IUIAdapter
│       │
│       └── windows/            # Fenêtres GUI
│           └── main_window.py
```

**Code exemple - Service pur (réutilisable CLI + GUI)**:

```python
# duplicateflow/core/services/scan_service.py
from typing import List, Optional
from pathlib import Path
from ..models.scan_result import ScanResult, DuplicateGroup
from ..interfaces.i_progress_reporter import IProgressReporter
from ..interfaces.i_storage import IStorage

class ScanService:
    """
    Service de scan de dossiers.

    PURE LOGIQUE MÉTIER - Aucune dépendance à CLI/GUI.
    Peut être utilisé par CLI, GUI, API, tests.
    """

    def __init__(
        self,
        storage: IStorage,
        progress_reporter: Optional[IProgressReporter] = None
    ):
        self.storage = storage
        self.progress = progress_reporter or NullProgressReporter()

    def scan_directory(
        self,
        directory: Path,
        pipeline_name: str,
        recursive: bool = True,
        extensions: List[str] = None,
        min_size: int = 0,
        max_size: Optional[int] = None,
        group_duplicates: bool = True
    ) -> ScanResult:
        """
        Scan directory for duplicates.

        Returns:
            ScanResult avec groupes, paires, métriques
        """

        # 1. Découvrir vidéos
        self.progress.start_phase("discovery", total=1)
        videos = self._discover_videos(
            directory, recursive, extensions, min_size, max_size
        )
        self.progress.update("discovery", current=1,
                            message=f"Found {len(videos)} videos")

        # 2. Indexer
        self.progress.start_phase("indexing", total=len(videos))
        index = self._build_fingerprint_index(videos)

        # 3. Trouver candidats
        self.progress.start_phase("candidates", total=1)
        candidates = index.find_candidates(threshold=0.8)
        self.progress.update("candidates", current=1,
                            message=f"Found {len(candidates)} pairs")

        # 4. Vérifier avec pipeline
        self.progress.start_phase("verification", total=len(candidates))
        duplicates = self._verify_with_pipeline(candidates, pipeline_name)

        # 5. Grouper
        if group_duplicates:
            groups = self._group_duplicates(duplicates)
        else:
            groups = []

        # 6. Retourner résultat
        return ScanResult(
            directory=directory,
            total_videos=len(videos),
            duplicate_pairs=duplicates,
            duplicate_groups=groups,
            potential_savings_bytes=self._calculate_savings(groups),
            scan_duration_seconds=self.progress.elapsed_time()
        )
```

**Interface Progress (implémentée différemment par CLI et GUI)**:

```python
# duplicateflow/core/interfaces/i_progress_reporter.py
from abc import ABC, abstractmethod
from typing import Optional

class IProgressReporter(ABC):
    """Interface pour reporter la progression (CLI, GUI, API, tests)."""

    @abstractmethod
    def start_phase(self, phase_name: str, total: int, message: str = ""):
        """Démarrer une phase avec nombre d'étapes."""
        pass

    @abstractmethod
    def update(self, phase_name: str, current: int, message: str = ""):
        """Mettre à jour progression d'une phase."""
        pass

    @abstractmethod
    def finish_phase(self, phase_name: str, message: str = ""):
        """Terminer une phase."""
        pass

    @abstractmethod
    def elapsed_time(self) -> float:
        """Temps écoulé depuis début."""
        pass

class NullProgressReporter(IProgressReporter):
    """Implémentation null (pour tests)."""

    def start_phase(self, phase_name: str, total: int, message: str = ""):
        pass

    def update(self, phase_name: str, current: int, message: str = ""):
        pass

    def finish_phase(self, phase_name: str, message: str = ""):
        pass

    def elapsed_time(self) -> float:
        return 0.0
```

**Adaptateur Rich (CLI)**:

```python
# duplicateflow/cli/adapters/rich_progress.py
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from duplicateflow.core.interfaces.i_progress_reporter import IProgressReporter
import time

class RichProgressReporter(IProgressReporter):
    """Implémentation Rich pour CLI."""

    def __init__(self, console):
        self.console = console
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        )
        self.tasks = {}
        self.start_time = time.time()
        self.progress.start()

    def start_phase(self, phase_name: str, total: int, message: str = ""):
        task_id = self.progress.add_task(message or phase_name, total=total)
        self.tasks[phase_name] = task_id

    def update(self, phase_name: str, current: int, message: str = ""):
        task_id = self.tasks[phase_name]
        self.progress.update(task_id, completed=current, description=message)

    def finish_phase(self, phase_name: str, message: str = ""):
        task_id = self.tasks[phase_name]
        self.progress.remove_task(task_id)
        if message:
            self.console.print(f"✓ {message}")

    def elapsed_time(self) -> float:
        return time.time() - self.start_time
```

**Commande CLI (thin wrapper)**:

```python
# duplicateflow/cli/commands/scan_command.py
from pathlib import Path
from rich.console import Console
from duplicateflow.core.services.scan_service import ScanService
from duplicateflow.storage import StorageManager
from ..adapters.rich_progress import RichProgressReporter
from ..ui.dashboards.scan_dashboard import ScanDashboard

class ScanCommand:
    """
    Commande CLI pour scan.

    THIN WRAPPER - Délègue tout au ScanService.
    """

    def __init__(self, console: Console):
        self.console = console

    def execute(
        self,
        directory: Path,
        pipeline: str,
        recursive: bool = True,
        group_duplicates: bool = True
    ):
        """Execute scan command."""

        # 1. Setup
        storage = StorageManager()
        progress = RichProgressReporter(self.console)
        service = ScanService(storage, progress)

        # 2. Exécuter service (logique métier pure)
        result = service.scan_directory(
            directory=directory,
            pipeline_name=pipeline,
            recursive=recursive,
            group_duplicates=group_duplicates
        )

        # 3. Afficher résultats (présentation Rich)
        dashboard = ScanDashboard(self.console)
        dashboard.show_results(result)

        return 0
```

**Avantages**:
- ✅ Core services testables sans CLI/GUI (tests rapides)
- ✅ Même logique métier pour CLI et future GUI
- ✅ Rich progress reporter injectable (mockable pour tests)
- ✅ Séparation claire responsabilités
- ✅ GUI peut réutiliser 100% de la logique

##### 13.2 Suite de Tests Complète (TDD)

**Structure tests**:

```
tests/
├── unit/                        # Tests unitaires (rapides, isolés)
│   ├── core/
│   │   ├── services/
│   │   │   ├── test_scan_service.py
│   │   │   ├── test_scene_search_service.py
│   │   │   ├── test_pipeline_service.py
│   │   │   └── test_benchmark_service.py
│   │   │
│   │   └── models/
│   │       ├── test_scan_result.py
│   │       └── test_pipeline_config.py
│   │
│   ├── cli/
│   │   ├── commands/
│   │   │   ├── test_scan_command.py
│   │   │   └── test_pipeline_command.py
│   │   │
│   │   └── ui/
│   │       ├── test_dashboards.py
│   │       └── test_widgets.py
│   │
│   └── duplicateflow/          # Tests DuplicateFlow core
│       ├── test_pipeline.py
│       └── test_algorithms.py
│
├── integration/                 # Tests intégration (multi-composants)
│   ├── test_scan_workflow.py          # scan end-to-end
│   ├── test_find_scenes_workflow.py   # find-scenes end-to-end
│   ├── test_pipeline_creation.py      # créer + sauver + charger
│   └── test_storage_integration.py    # DB + cache
│
├── e2e/                         # Tests end-to-end (vraies vidéos)
│   ├── test_cli_scan.py               # Test CLI complet
│   ├── test_cli_find_scenes.py
│   └── test_regression.py             # Tests non-régression
│
├── fixtures/                    # Fixtures partagées
│   ├── videos/                  # Vidéos de test (petites)
│   │   ├── duplicate_1.mp4
│   │   ├── duplicate_2.mp4
│   │   └── scene_in_long.mp4
│   │
│   ├── pipelines/               # Pipelines YAML de test
│   │   ├── test_pipeline.yaml
│   │   └── invalid_pipeline.yaml
│   │
│   └── conftest.py             # Fixtures pytest
│
└── performance/                 # Tests de performance
    ├── test_scan_performance.py
    └── benchmarks.py
```

**Exemple test unitaire (service pur)**:

```python
# tests/unit/core/services/test_scan_service.py
import pytest
from pathlib import Path
from duplicateflow.core.services.scan_service import ScanService
from duplicateflow.core.interfaces.i_progress_reporter import NullProgressReporter
from tests.fixtures.mock_storage import MockStorage

class TestScanService:
    """Tests unitaires ScanService (logique métier pure)."""

    @pytest.fixture
    def service(self):
        """Fixture: service avec dépendances mockées."""
        storage = MockStorage()
        progress = NullProgressReporter()
        return ScanService(storage, progress)

    @pytest.fixture
    def video_directory(self, tmp_path):
        """Fixture: dossier avec vidéos de test."""
        # Créer structure de test
        dir_path = tmp_path / "videos"
        dir_path.mkdir()

        # Copier vidéos de test
        (dir_path / "video1.mp4").write_bytes(b"fake video 1")
        (dir_path / "video2.mp4").write_bytes(b"fake video 2")
        (dir_path / "duplicate.mp4").write_bytes(b"fake video 1")  # Duplicate

        return dir_path

    def test_discover_videos_recursive(self, service, video_directory):
        """Test: découverte vidéos en mode récursif."""
        # Créer sous-dossier
        subdir = video_directory / "subdir"
        subdir.mkdir()
        (subdir / "video3.mp4").write_bytes(b"fake video 3")

        # Découvrir
        videos = service._discover_videos(
            video_directory,
            recursive=True,
            extensions=['mp4'],
            min_size=0,
            max_size=None
        )

        # Vérifier
        assert len(videos) == 4  # video1, video2, duplicate, video3
        assert all(v.suffix == '.mp4' for v in videos)

    def test_discover_videos_non_recursive(self, service, video_directory):
        """Test: découverte vidéos en mode non-récursif."""
        # Créer sous-dossier
        subdir = video_directory / "subdir"
        subdir.mkdir()
        (subdir / "video3.mp4").write_bytes(b"fake video 3")

        # Découvrir
        videos = service._discover_videos(
            video_directory,
            recursive=False,
            extensions=['mp4'],
            min_size=0,
            max_size=None
        )

        # Vérifier: seulement racine
        assert len(videos) == 3  # video1, video2, duplicate

    def test_scan_directory_with_duplicates(self, service, video_directory):
        """Test: scan complet avec détection duplicates."""
        result = service.scan_directory(
            directory=video_directory,
            pipeline_name='balanced',
            recursive=True,
            group_duplicates=True
        )

        # Vérifier résultat
        assert result.total_videos == 3
        assert len(result.duplicate_pairs) >= 1  # video1 ↔ duplicate
        assert len(result.duplicate_groups) >= 1
        assert result.potential_savings_bytes > 0

    def test_scan_directory_no_duplicates(self, service, tmp_path):
        """Test: scan sans duplicates."""
        # Créer vidéos toutes différentes
        dir_path = tmp_path / "unique_videos"
        dir_path.mkdir()
        (dir_path / "video1.mp4").write_bytes(b"unique 1")
        (dir_path / "video2.mp4").write_bytes(b"unique 2")

        result = service.scan_directory(
            directory=dir_path,
            pipeline_name='balanced',
            group_duplicates=True
        )

        # Vérifier: aucun duplicate
        assert result.total_videos == 2
        assert len(result.duplicate_pairs) == 0
        assert len(result.duplicate_groups) == 0
        assert result.potential_savings_bytes == 0

    def test_scan_respects_min_size_filter(self, service, tmp_path):
        """Test: filtre min_size fonctionne."""
        dir_path = tmp_path / "videos"
        dir_path.mkdir()

        # Créer vidéos de tailles différentes
        (dir_path / "small.mp4").write_bytes(b"small")  # 5 bytes
        (dir_path / "large.mp4").write_bytes(b"a" * 1000)  # 1000 bytes

        videos = service._discover_videos(
            dir_path,
            recursive=True,
            extensions=['mp4'],
            min_size=100,  # Minimum 100 bytes
            max_size=None
        )

        # Vérifier: seulement large.mp4
        assert len(videos) == 1
        assert videos[0].name == "large.mp4"
```

**Exemple test intégration**:

```python
# tests/integration/test_scan_workflow.py
import pytest
from pathlib import Path
from duplicateflow.core.services.scan_service import ScanService
from duplicateflow.storage import StorageManager
from duplicateflow.core.interfaces.i_progress_reporter import NullProgressReporter

class TestScanWorkflow:
    """Tests intégration: scan complet avec vrais composants."""

    @pytest.fixture
    def real_storage(self, tmp_path):
        """Fixture: vrai StorageManager avec DB temporaire."""
        db_path = tmp_path / "test.db"
        return StorageManager(db_path=str(db_path))

    @pytest.fixture
    def service(self, real_storage):
        """Fixture: service avec vrais composants."""
        progress = NullProgressReporter()
        return ScanService(real_storage, progress)

    def test_full_scan_workflow_with_storage(
        self,
        service,
        real_storage,
        test_videos_directory  # Fixture avec vraies vidéos
    ):
        """Test: workflow complet scan → storage → retrieval."""

        # 1. Scanner
        result = service.scan_directory(
            directory=test_videos_directory,
            pipeline_name='balanced',
            group_duplicates=True
        )

        # 2. Sauvegarder résultats
        scan_id = real_storage.save_scan_result(result)

        # 3. Récupérer depuis storage
        retrieved = real_storage.get_scan_result(scan_id)

        # 4. Vérifier intégrité
        assert retrieved.total_videos == result.total_videos
        assert len(retrieved.duplicate_groups) == len(result.duplicate_groups)
```

**Exemple test E2E (CLI complet)**:

```python
# tests/e2e/test_cli_scan.py
import pytest
import subprocess
from pathlib import Path

class TestCLIScan:
    """Tests end-to-end: vraie commande CLI."""

    def test_scan_command_full_workflow(self, test_videos_directory, tmp_path):
        """Test: commande scan complète via subprocess."""

        output_file = tmp_path / "scan_results.json"

        # Exécuter vraie commande CLI
        result = subprocess.run(
            [
                "python", "-m", "duplicateflow.cli",
                "scan",
                str(test_videos_directory),
                "--pipeline", "balanced",
                "--group-duplicates",
                "--output", str(output_file)
            ],
            capture_output=True,
            text=True
        )

        # Vérifier succès
        assert result.returncode == 0
        assert "Duplicate Groups Found" in result.stdout

        # Vérifier output file créé
        assert output_file.exists()

        # Vérifier contenu JSON
        import json
        data = json.loads(output_file.read_text())
        assert "total_videos" in data
        assert "duplicate_groups" in data

    def test_scan_command_with_invalid_pipeline(self, test_videos_directory):
        """Test: erreur claire si pipeline invalide."""

        result = subprocess.run(
            [
                "python", "-m", "duplicateflow.cli",
                "scan",
                str(test_videos_directory),
                "--pipeline", "nonexistent_pipeline"
            ],
            capture_output=True,
            text=True
        )

        # Vérifier échec gracieux
        assert result.returncode != 0
        assert "Pipeline 'nonexistent_pipeline' not found" in result.stderr
        assert "Available pipelines:" in result.stderr  # Suggestions
```

**Configuration pytest**:

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (multiple components)
    e2e: End-to-end tests (full workflows)
    slow: Slow tests (skip in quick runs)
    performance: Performance benchmarks

# Coverage
addopts =
    --cov=duplicateflow
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    -v
    -ra

# Ignore warnings
filterwarnings =
    ignore::DeprecationWarning
```

**Commandes tests**:

```bash
# Tests rapides (unitaires uniquement)
pytest -m unit

# Tests complets
pytest

# Tests avec coverage
pytest --cov=duplicateflow --cov-report=html

# Tests spécifiques
pytest tests/unit/core/services/test_scan_service.py

# Tests parallèles (rapide)
pytest -n auto

# Tests avec output détaillé
pytest -vv -s
```

##### 13.3 Rich UI Premium (exploitation complète)

**Composants Rich avancés**:

```python
# duplicateflow/cli/ui/dashboards/scan_dashboard.py
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, BarColumn
from rich.tree import Tree
from rich.syntax import Syntax
import time

class ScanDashboard:
    """
    Dashboard live pour scan de dossiers.

    Affichage riche avec:
    - Live progress multi-phases
    - Statistiques en temps réel
    - Preview résultats
    - Alerts/warnings
    """

    def __init__(self, console: Console):
        self.console = console

    def show_live_scan(self, service, **scan_params):
        """Afficher scan en direct avec dashboard live."""

        # Layout complexe
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=7)
        )

        layout["body"].split_row(
            Layout(name="progress", ratio=2),
            Layout(name="stats", ratio=1)
        )

        # Components
        stats = {
            'videos_found': 0,
            'candidates_found': 0,
            'duplicates_verified': 0,
            'savings_gb': 0.0
        }

        def make_header():
            return Panel(
                "[bold cyan]🔍 DuplicateFlow - Directory Scan[/bold cyan]",
                style="bold white on blue"
            )

        def make_progress_panel(progress: Progress):
            return Panel(
                progress,
                title="Progress",
                border_style="green"
            )

        def make_stats_panel():
            table = Table.grid(padding=(0, 2))
            table.add_column(style="cyan")
            table.add_column(style="bold green")

            table.add_row("Videos Found:", f"{stats['videos_found']:,}")
            table.add_row("Candidates:", f"{stats['candidates_found']:,}")
            table.add_row("Duplicates:", f"{stats['duplicates_verified']:,}")
            table.add_row("Savings:", f"{stats['savings_gb']:.2f} GB")

            return Panel(
                table,
                title="Statistics",
                border_style="yellow"
            )

        def make_footer():
            return Panel(
                "[dim]Press Ctrl+C to cancel[/dim]",
                style="dim white on black"
            )

        # Live display
        with Live(layout, console=self.console, refresh_per_second=4) as live:
            with Progress() as progress:
                # Setup layout
                layout["header"].update(make_header())
                layout["progress"].update(make_progress_panel(progress))
                layout["stats"].update(make_stats_panel())
                layout["footer"].update(make_footer())

                # Phases
                discovery_task = progress.add_task("Discovery", total=100)
                indexing_task = progress.add_task("Indexing", total=100)
                matching_task = progress.add_task("Matching", total=100)

                # Simuler scan (dans la vraie impl, callbacks du service)
                for i in range(100):
                    progress.update(discovery_task, advance=1)
                    stats['videos_found'] = i * 12
                    layout["stats"].update(make_stats_panel())
                    time.sleep(0.02)

                # ... (suite des phases)

    def show_results(self, result: ScanResult):
        """Afficher résultats avec Rich formatting."""

        console = self.console

        # 1. Header avec stats
        stats_table = Table.grid(padding=(0, 4))
        stats_table.add_column(style="cyan", justify="right")
        stats_table.add_column(style="bold green")

        stats_table.add_row("Total Videos:", f"{result.total_videos:,}")
        stats_table.add_row("Duplicate Groups:", f"{len(result.duplicate_groups):,}")
        stats_table.add_row("Duplicate Pairs:", f"{len(result.duplicate_pairs):,}")
        stats_table.add_row(
            "Potential Savings:",
            f"[bold red]{result.potential_savings_bytes / (1024**3):.2f} GB[/bold red]"
        )
        stats_table.add_row("Scan Duration:", f"{result.scan_duration_seconds:.1f}s")

        console.print(Panel(stats_table, title="📊 Scan Summary", border_style="green"))

        # 2. Duplicate groups avec tree
        if result.duplicate_groups:
            tree = Tree("🎯 Duplicate Groups", guide_style="dim")

            for i, group in enumerate(result.duplicate_groups, 1):
                group_node = tree.add(f"[bold cyan]Group #{i}[/bold cyan] ({len(group.videos)} videos)")

                # Calcul savings
                sizes = [Path(v).stat().st_size for v in group.videos]
                total_size = sum(sizes)
                savings = total_size - max(sizes)

                group_node.add(f"[yellow]Total Size:[/yellow] {total_size / (1024**3):.2f} GB")
                group_node.add(f"[red]Savings:[/red] {savings / (1024**3):.2f} GB")

                # Videos
                videos_node = group_node.add("[dim]Videos:[/dim]")
                for video in group.videos[:5]:  # Limiter à 5
                    videos_node.add(f"[dim]{video}[/dim]")

                if len(group.videos) > 5:
                    videos_node.add(f"[dim]... and {len(group.videos) - 5} more[/dim]")

            console.print(tree)

        # 3. Actions suggérées
        if result.duplicate_groups:
            suggestions = Panel(
                "[bold yellow]💡 Suggested Actions:[/bold yellow]\n\n"
                "1. Review groups and keep best quality version\n"
                "2. Export results: [cyan]--output duplicates.json[/cyan]\n"
                "3. Auto-clean: [cyan]duplicateflow auto-clean --keep-best-quality[/cyan]",
                border_style="yellow"
            )
            console.print(suggestions)


# duplicateflow/cli/ui/widgets/prompts.py
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.console import Console
from typing import List, Optional

class InteractivePrompts:
    """Prompts interactifs Rich pour création pipelines, etc."""

    def __init__(self, console: Console):
        self.console = console

    def choose_use_case(self) -> str:
        """Prompt: choisir cas d'usage."""

        self.console.print("\n[bold cyan]📊 Quel est votre cas d'usage?[/bold cyan]\n")

        choices = {
            "1": ("exact_duplicates", "Duplicates exacts (même vidéo, qualités différentes)"),
            "2": ("similar_scenes", "Scènes similaires (intro, générique, extraits)"),
            "3": ("perceptual", "Vidéos perceptuellement similaires"),
            "4": ("balanced", "Détection générique (équilibré)")
        }

        for key, (_, description) in choices.items():
            self.console.print(f"  {key}. {description}")

        choice = Prompt.ask(
            "\n[yellow]Choix[/yellow]",
            choices=list(choices.keys()),
            default="4"
        )

        use_case, _ = choices[choice]
        self.console.print(f"\n✓ Cas d'usage: [green]{use_case}[/green]\n")

        return use_case

    def configure_algorithm(
        self,
        algo_name: str,
        algo_info: dict
    ) -> dict:
        """Prompt: configurer un algorithme."""

        self.console.print(f"\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
        self.console.print(f"[bold cyan]🔧 Configuration: {algo_name}[/bold cyan]\n")

        # Description
        self.console.print(f"[dim]{algo_info['description']}[/dim]\n")

        # Paramètres
        config = {}

        # Threshold
        threshold_info = algo_info['parameters']['threshold']
        threshold = IntPrompt.ask(
            f"[yellow]threshold[/yellow] ({threshold_info['range']}, défaut: {threshold_info['default']})",
            default=threshold_info['default']
        )
        config['threshold'] = threshold

        # Weight
        weight_info = algo_info['parameters']['weight']
        weight = Prompt.ask(
            f"[yellow]weight[/yellow] (0.0-1.0, défaut: {weight_info['default']})",
            default=str(weight_info['default'])
        )
        config['weight'] = float(weight)

        # Params spécifiques
        if 'params' in algo_info:
            config['params'] = {}
            for param_name, param_info in algo_info['params'].items():
                value = Prompt.ask(
                    f"[yellow]{param_name}[/yellow] (défaut: {param_info['default']})",
                    default=str(param_info['default'])
                )
                config['params'][param_name] = type(param_info['default'])(value)

        return config
```

##### 13.4 Documentation Auto-Générée et Sync

**Système de documentation vivante**:

```python
# duplicateflow/cli/commands/docs_command.py
from pathlib import Path
from rich.console import Console
import inspect
import ast

class DocsCommand:
    """
    Commande pour générer/mettre à jour documentation automatiquement.

    Maintient sync entre:
    - Code source
    - Docstrings
    - Markdown docs
    - CLI --help
    """

    def __init__(self, console: Console):
        self.console = console

    def generate_all(self, output_dir: Path):
        """Générer toute la documentation."""

        self.console.print("[cyan]Generating documentation...[/cyan]\n")

        # 1. API Reference depuis docstrings
        self._generate_api_reference(output_dir / "API_REFERENCE.md")

        # 2. CLI Reference depuis commands
        self._generate_cli_reference(output_dir / "CLI_REFERENCE.md")

        # 3. Examples depuis tests
        self._generate_examples(output_dir / "EXAMPLES.md")

        # 4. Architecture diagrams
        self._generate_architecture_diagrams(output_dir / "ARCHITECTURE.md")

        self.console.print("[green]✓ Documentation generated![/green]")

    def _generate_api_reference(self, output_path: Path):
        """Générer API reference depuis docstrings."""

        from duplicateflow.core import services

        md = ["# 🔧 API Reference\n"]
        md.append("Auto-generated from source code.\n")
        md.append(f"**Last updated**: {datetime.now().isoformat()}\n\n")

        # Parser tous les services
        for service_module in self._get_all_services():
            md.append(f"## {service_module.__name__}\n")

            # Get all classes
            for name, obj in inspect.getmembers(service_module, inspect.isclass):
                if not name.startswith('_'):
                    md.append(f"### `{name}`\n")

                    # Docstring
                    if obj.__doc__:
                        md.append(f"{inspect.cleandoc(obj.__doc__)}\n\n")

                    # Methods
                    md.append("**Methods**:\n\n")
                    for method_name, method in inspect.getmembers(obj, inspect.isfunction):
                        if not method_name.startswith('_') or method_name == '__init__':
                            sig = inspect.signature(method)
                            md.append(f"#### `{method_name}{sig}`\n")

                            if method.__doc__:
                                md.append(f"{inspect.cleandoc(method.__doc__)}\n\n")

        output_path.write_text('\n'.join(md))
        self.console.print(f"  ✓ {output_path}")

    def _generate_cli_reference(self, output_path: Path):
        """Générer CLI reference depuis commandes."""

        md = ["# 📟 CLI Reference\n"]
        md.append("Complete CLI commands reference.\n\n")

        # Lister toutes les commandes
        from duplicateflow.cli import commands

        for command_file in Path(commands.__file__).parent.glob("*_command.py"):
            # Parser AST pour extraire info
            tree = ast.parse(command_file.read_text())

            # ... (extraction info commande)

        output_path.write_text('\n'.join(md))
        self.console.print(f"  ✓ {output_path}")

    def check_sync(self):
        """Vérifier sync documentation ↔ code."""

        issues = []

        # Vérifier docstrings manquants
        for service in self._get_all_services():
            if not service.__doc__:
                issues.append(f"Missing docstring: {service.__name__}")

        # Vérifier CLI help ↔ docs
        # ...

        if issues:
            self.console.print("[red]❌ Documentation out of sync:[/red]\n")
            for issue in issues:
                self.console.print(f"  • {issue}")
            return False
        else:
            self.console.print("[green]✓ Documentation in sync![/green]")
            return True
```

**Pre-commit hook pour maintenir docs**:

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Vérifier sync documentation
python -m duplicateflow.cli docs check-sync

if [ $? -ne 0 ]; then
    echo "❌ Documentation out of sync. Run: duplicateflow docs generate"
    exit 1
fi

# Vérifier tests passent
pytest -m unit -q

if [ $? -ne 0 ]; then
    echo "❌ Unit tests failing. Fix before committing."
    exit 1
fi

echo "✓ All checks passed!"
```

##### 13.5 CI/CD et Quality Gates

**GitHub Actions workflow**:

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install ruff black mypy

      - name: Lint with ruff
        run: ruff check duplicateflow/

      - name: Check formatting
        run: black --check duplicateflow/

      - name: Type check
        run: mypy duplicateflow/ --strict

  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.9', '3.10', '3.11']

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run unit tests
        run: pytest -m unit --cov=duplicateflow --cov-report=xml

      - name: Run integration tests
        run: pytest -m integration

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4

      - name: Check docs sync
        run: python -m duplicateflow.cli docs check-sync

      - name: Generate docs
        run: python -m duplicateflow.cli docs generate --output docs/

      - name: Deploy docs
        if: github.ref == 'refs/heads/main'
        run: |
          # Deploy to GitHub Pages
          # ...

  quality-gate:
    runs-on: ubuntu-latest
    needs: [lint, test, docs]
    steps:
      - name: Quality Gate
        run: |
          echo "✓ All quality checks passed!"
```

**Impact utilisateur**: 🌟🌟🌟🌟🌟 (infrastructure essentielle)
**Impact dev**: 🌟🌟🌟🌟🌟 (productivité maximale)
**Effort dev**: 6 jours
**ROI**: Maximum (évite bugs, accélère développement)

---

## 📅 Priorisation et Roadmap

### Phase 1: Fondations (Semaine 1) - 🔴 CRITIQUE
1. **Migration vers DuplicateFlow** (Catégorie 1)
   - Créer structure modulaire dans `duplicateflow/cli/`
   - Séparer commands, ui, utils
   - Durée: 2 jours

2. **UX Improvements** (Catégorie 2)
   - Messages d'erreur avec suggestions
   - Enhanced --help
   - Durée: 1 jour

3. **SDK Integration** (Catégorie 9)
   - Utiliser API publique DuplicateFlow
   - Éviter imports internes
   - Durée: 1 jour

### Phase 2: Features Essentielles (Semaine 2-3) - 🟡 IMPORTANT
4. **Recherche dans Arborescences** ⭐ (Catégorie 11) **PRIORITÉ HAUTE**
   - Scan de dossier (duplicateflow scan)
   - Détection scènes incluses (duplicateflow find-scenes)
   - Cross-search entre dossiers
   - Durée: 5 jours

5. **Gestion et Configuration des Pipelines** ⭐ (Catégorie 12) **PRIORITÉ HAUTE**
   - Création interactive guidée (mode débutant)
   - Sauvegarde/chargement YAML avec commentaires
   - Documentation algorithmes pour débutants
   - Validation de configuration
   - Templates de pipelines
   - Durée: 4 jours

6. **Configuration System** (Catégorie 6)
   - Support TOML
   - Profiles (quick, production)
   - Durée: 2 jours

7. **Fonctionnalités manquantes** (Catégorie 4)
   - Historique comparaisons
   - Test set validation
   - Détection régression
   - Durée: 4 jours

8. **Optimisations** (Catégorie 3)
   - Cache compressé
   - Parallélisation adaptative
   - Durée: 2 jours

### Phase 3: Polish (Semaine 4) - 🟢 NICE-TO-HAVE
9. **Export formats** (Catégorie 5)
   - HTML interactif
   - Markdown
   - Durée: 2 jours

10. **Debug & Logging** (Catégorie 7)
    - Structured logging
    - Debug mode
    - Performance profiling
    - Durée: 2 jours

### Phase 4: Extensibilité (Semaine 5+) - 🟢 FUTUR
11. **Plugin System** (Catégorie 8)
    - Test set loaders
    - Custom analyzers
    - Durée: 3 jours

12. **Packaging** (Catégorie 10)
    - Entry points PyPI
    - Distribution
    - Durée: 1 jour

---

## 📊 Impact Estimé

### Bénéfices par catégorie

| Catégorie | Impact Dev | Impact User | Effort | ROI |
|-----------|------------|-------------|--------|-----|
| 1. Organisation | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 🔨🔨 | 🌟🌟🌟🌟🌟 |
| 2. UX | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🔨 | 🌟🌟🌟🌟🌟 |
| 3. Performance | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🔨🔨 | 🌟🌟🌟⭐ |
| 4. Features | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🔨🔨🔨 | 🌟🌟🌟🌟 |
| 5. Export | ⭐⭐ | ⭐⭐⭐ | 🔨 | 🌟🌟⭐ |
| 6. Config | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🔨🔨 | 🌟🌟🌟🌟 |
| 7. Debug | ⭐⭐⭐⭐ | ⭐⭐ | 🔨 | 🌟🌟⭐ |
| 8. Plugins | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 🔨🔨🔨 | 🌟⭐⭐ |
| 9. SDK | ⭐⭐⭐⭐⭐ | ⭐⭐ | 🔨 | 🌟🌟🌟🌟🌟 |
| 10. Packaging | ⭐⭐ | ⭐⭐⭐⭐ | 🔨 | 🌟🌟🌟 |
| **11. Arborescences** ⭐ | **⭐⭐⭐⭐⭐** | **⭐⭐⭐⭐⭐** | **🔨🔨🔨** | **🌟🌟🌟🌟🌟** |
| **12. Pipeline Management** ⭐ | **⭐⭐⭐⭐⭐** | **⭐⭐⭐⭐⭐** | **🔨🔨** | **🌟🌟🌟🌟🌟** |

**Légende**:
- ⭐ Impact (1-5 étoiles)
- 🔨 Effort (1-3 marteaux)
- 🌟 ROI = Impact / Effort

**Features phares**:
- 🥇 **Arborescences** - Impact massif users + devs, très demandée
- 🥇 **Pipeline Management** - Essentiel pour exploiter le système, rend accessible aux débutants

---

## 🎯 Recommandations

### Must-Have (Commencer immédiatement)
1. ✅ **Migration vers duplicateflow/cli/** - Fondation pour tout le reste
2. ✅ **Amélioration UX** - Impact immédiat sur expérience utilisateur
3. ✅ **SDK Integration** - Évite dette technique
4. ✅ **Recherche Arborescences** ⭐ - Feature killer, très demandée
5. ✅ **Pipeline Management** ⭐ - CRITIQUE: Base du système, rend accessible aux débutants

### Should-Have (Dans les 3 semaines)
6. ✅ **Configuration system** - Flexibilité essentielle
7. ✅ **Features manquantes** - Historique, validation, régression
8. ✅ **Optimisations** - Cache compressé, parallélisation

### Nice-to-Have (Quand temps disponible)
9. ✅ **Export formats** - HTML, Markdown
10. ✅ **Debug & Logging** - Aide développement

### Future (Après stabilisation)
11. ✅ **Plugin system** - Extensibilité avancée
12. ✅ **Packaging PyPI** - Distribution large

---

## 🚀 Migration Path

### Étape 1: Backup
```bash
cp run_testset.py run_testset.py.backup
git add run_testset.py.backup
git commit -m "backup: Save original run_testset.py before refactoring"
```

### Étape 2: Créer structure
```bash
mkdir -p duplicateflow/duplicateflow/cli/{commands,ui,utils}
touch duplicateflow/duplicateflow/cli/__init__.py
touch duplicateflow/duplicateflow/cli/__main__.py
```

### Étape 3: Split progressif
1. Extraire commandes → `commands/benchmark.py`, `commands/compare.py`
2. Extraire UI → `ui/dashboard.py`, `ui/interactive.py`
3. Extraire utils → `utils/checkpoint.py`, `utils/export.py`

### Étape 4: Tests
```bash
# Test que ça marche
python -m duplicateflow.cli benchmark --testset default --pipeline balanced --limit 5
```

### Étape 5: Déprécier ancien
```python
# run_testset.py devient wrapper
#!/usr/bin/env python3
"""DEPRECATED: Use 'python -m duplicateflow.cli' instead."""
import sys
print("⚠️  run_testset.py is deprecated. Use: python -m duplicateflow.cli")
from duplicateflow.cli import main
sys.exit(main())
```

### Étape 6: Documentation
```bash
# Mettre à jour docs
echo "See: duplicateflow/cli/README.md" > CLI_MIGRATION.md
```

---

## 📝 Conclusion

### Synthèse des propositions

- **10 catégories** d'améliorations identifiées
- **~150 heures** de développement estimées (1-2 mois)
- **Impact majeur** sur maintenabilité et UX
- **Migration progressive** possible sans disruption

### Gains attendus

#### Pour les utilisateurs
- ✅ UX premium avec suggestions intelligentes
- ✅ Historique et détection régression
- ✅ Exports riches (HTML, Markdown)
- ✅ Configuration flexible (profiles)
- ✅ **Scan d'arborescences complètes** ⭐
- ✅ **Détection scènes dans vidéos longues avec timestamps précis** ⭐
- ✅ **Cross-search entre dossiers** ⭐
- ✅ **25+ GB d'économie d'espace potentielle** (exemple)

#### Pour les développeurs
- ✅ Code modulaire et testable
- ✅ Architecture extensible (plugins)
- ✅ Debug et profiling intégrés
- ✅ Documentation auto-générée

#### Pour le projet
- ✅ Structure professionnelle
- ✅ Ready pour PyPI
- ✅ Facilite contributions
- ✅ Réduit dette technique

### Prochaines actions

1. **Validation**: Review des propositions avec l'équipe
2. **Priorisation**: Confirmer roadmap phases 1-4
3. **POC**: Implémenter migration structure (Phase 1)
4. **Itération**: Implémenter progressivement phases 2-4

---

## 🎬 Cas d'Usage Réels

### Scenario 1: Gestionnaire de médiathèque personnelle
**Besoin**: Tu as 2 TB de vidéos accumulées sur 10 ans, beaucoup de duplicates.

**Workflow avec nouvelle feature**:
```bash
# 1. Scan complet pour identifier duplicates
duplicateflow scan /media/videos --recursive --pipeline balanced --group-duplicates

# Output: 12 groupes trouvés, 25.4 GB économies potentielles
# Duplicate Groups Found: 12
# ┌───────┬───────────┬────────────┬───────────────────┐
# │ Group │ Videos    │ Total Size │ Potential Savings │
# ├───────┼───────────┼────────────┼───────────────────┤
# │ #1    │ 3 videos  │ 4.25 GB    │ 2.80 GB           │
# │ #2    │ 2 videos  │ 1.80 GB    │ 0.90 GB           │
# │ ...   │ ...       │ ...        │ ...               │
# └───────┴───────────┴────────────┴───────────────────┘

# 2. Examiner et supprimer manuellement les duplicates identifiés
```

**Gains**: 25+ GB libérés, vue complète des duplicates

### Scenario 2: Producteur vidéo / Monteur
**Besoin**: Tu cherches où une intro/outro apparaît dans tes projets.

**Workflow**:
```bash
# Trouver toutes les occurrences d'une intro
duplicateflow find-scenes intro_v2.mp4 --in /projects --show-timestamps

# Output:
# - projet_A.mp4: 00:00:10 → 00:00:25 (98.5%)
# - compilation_2024.mp4: 01:05:30 → 01:05:45 (96.2%)
# - final_cut.mp4: 00:00:05 → 00:00:20 (99.1%)

# Génère automatiquement commandes FFmpeg pour extraire
```

**Gains**: Retrouver instantanément des scènes dans des heures de footage

### Scenario 3: Archiviste / Bibliothèque
**Besoin**: Comparer 2 collections pour identifier redondances.

**Workflow**:
```bash
# Comparer nouvelle acquisition vs fonds existant
duplicateflow cross-search /new_acquisition /archive --pipeline thorough --report matches.json

# Analyse détaillée avec heatmap
duplicateflow heatmap /new_acquisition/*.mp4 --output similarity_matrix.html

# Historique de qualité
duplicateflow benchmark --testset archive_validation --pipeline production --history --check-regression
```

**Gains**: Évite acquisitions redondantes, garantit qualité d'indexation

### Scenario 4: Chercheur / Data Scientist
**Besoin**: Benchmarker pipelines sur datasets, tracking performance.

**Workflow**:
```bash
# Benchmark avec historique
duplicateflow benchmark --testset research_v3 --pipeline custom_v5 --analyze --history

# Détection régression automatique
duplicateflow benchmark --testset research_v3 --pipeline custom_v5 --check-regression --fail-on-regression

# Si OK, compare vs autres pipelines
duplicateflow compare --testset research_v3 --pipelines custom_v5,balanced,thorough --export-matrix

# Export pour publication
duplicateflow benchmark --testset research_v3 --pipeline custom_v5 --export html,markdown --include-failures
```

**Gains**: Tracking scientifique, reproductibilité, détection bugs instantanée

---

## 📈 Métriques de Succès

### Adoption
- 🎯 **80%** des utilisateurs utilisent `scan` dans le 1er mois
- 🎯 **60%** des utilisateurs utilisent `find-scenes` pour recherche précise
- 🎯 **40%** des utilisateurs créent pipelines custom

### Performance
- 🎯 **O(N)** au lieu de **O(N²)** grâce au Fingerprint Index
- 🎯 **<30s** pour scanner 1000 vidéos (index)
- 🎯 **95%+** de précision sur détection scènes

### Impact Business
- 🎯 **20-40%** réduction espace stockage (moyenne)
- 🎯 **10x** plus rapide que scan manuel
- 🎯 **0** faux négatifs critiques (grâce à historique + régression)

---

**Document créé**: 2025-12-19
**Auteur**: Claude Sonnet 4.5
**Status**: ✅ Propositions complètes (12 catégories) - En attente de validation
**Version**: 1.2 - Arborescences + Pipeline Management
**Lignes**: 2,436 LOC

