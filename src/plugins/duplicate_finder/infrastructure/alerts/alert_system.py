"""
Alert System - Intelligent monitoring and notifications for benchmark results

Features:
- Performance regression detection
- Quality gate monitoring
- Trend analysis
- Anomaly detection
- Multi-channel notifications (UI, logs, email)
"""

from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.AlertSystem')


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts."""
    PERFORMANCE_REGRESSION = "performance_regression"
    QUALITY_GATE_FAILURE = "quality_gate_failure"
    ANOMALY_DETECTED = "anomaly_detected"
    TREND_CHANGE = "trend_change"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    CACHE_LOW_HIT_RATE = "cache_low_hit_rate"


@dataclass
class Alert:
    """
    Alert data structure.

    Attributes:
        type: Alert type enum
        level: Severity level
        title: Short alert title
        message: Detailed message
        timestamp: When alert was created
        metadata: Additional context data
    """
    type: AlertType
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    metadata: Dict

    def __str__(self):
        return f"[{self.level.value.upper()}] {self.title}: {self.message}"


class BenchmarkAlertSystem(QObject):
    """
    Intelligent alert system for benchmark monitoring.

    Features:
        - Regression detection (compare to historical baseline)
        - Quality gate enforcement
        - Anomaly detection (statistical outliers)
        - Trend analysis (improving/degrading over time)
        - Configurable thresholds
        - Multi-channel notifications

    Signals:
        alert_triggered(Alert): Emitted when alert is raised
    """

    alert_triggered = pyqtSignal(object)  # Alert object

    # Default quality gates
    DEFAULT_QUALITY_GATES = {
        'f1_min': 0.75,
        'precision_min': 0.70,
        'recall_min': 0.70,
        'accuracy_min': 0.75
    }

    # Regression thresholds (percentage drop)
    REGRESSION_THRESHOLDS = {
        'f1': 0.05,  # 5% drop
        'precision': 0.05,
        'recall': 0.05,
        'accuracy': 0.05
    }

    def __init__(self, benchmark_manager, quality_gates: Optional[Dict] = None):
        """
        Initialize alert system.

        Args:
            benchmark_manager: BenchmarkManager instance
            quality_gates: Custom quality gate thresholds
        """
        super().__init__()
        self.benchmark_manager = benchmark_manager
        self.quality_gates = quality_gates or self.DEFAULT_QUALITY_GATES.copy()

        # Alert history
        self.alerts = deque(maxlen=1000)  # Keep last 1000 alerts

        # Historical metrics (for regression detection)
        self.metrics_history = deque(maxlen=20)  # Last 20 runs per pipeline

        # Alert callbacks (for custom handling)
        self.alert_callbacks: List[Callable[[Alert], None]] = []

        logger.info("Alert system initialized")

    def register_alert_callback(self, callback: Callable[[Alert], None]):
        """
        Register callback to be called when alert is triggered.

        Args:
            callback: Function that takes Alert as parameter
        """
        self.alert_callbacks.append(callback)
        logger.debug(f"Registered alert callback: {callback.__name__}")

    def check_benchmark_run(self, run_id: int) -> List[Alert]:
        """
        Check a benchmark run for issues and generate alerts.

        Args:
            run_id: Benchmark run ID to check

        Returns:
            List of alerts generated
        """
        alerts = []

        try:
            # Get run details and results
            run = self.benchmark_manager.get_run_details(run_id)
            if not run:
                logger.error(f"Run {run_id} not found")
                return alerts

            results = self.benchmark_manager.get_benchmark_results(run_id)
            if not results:
                logger.warning(f"No results for run {run_id}")
                return alerts

            # Calculate metrics
            metrics = self._calculate_metrics(results)

            # Store in history
            self.metrics_history.append({
                'run_id': run_id,
                'timestamp': run.get('timestamp'),
                'metrics': metrics
            })

            # Run checks
            alerts.extend(self._check_quality_gates(metrics, run))
            alerts.extend(self._check_regression(metrics, run))
            alerts.extend(self._check_anomalies(metrics, run))
            alerts.extend(self._check_trends(run))

            # Store and trigger alerts
            for alert in alerts:
                self._trigger_alert(alert)

            if alerts:
                logger.info(f"Generated {len(alerts)} alerts for run {run_id}")
            else:
                logger.debug(f"No alerts for run {run_id}")

        except Exception as e:
            logger.error(f"Error checking run {run_id}: {e}", exc_info=True)

        return alerts

    def _check_quality_gates(self, metrics: Dict, run: Dict) -> List[Alert]:
        """Check if metrics pass quality gates."""
        alerts = []

        for metric_name, threshold in self.quality_gates.items():
            metric_key = metric_name.replace('_min', '')
            metric_value = metrics.get(metric_key, 0)

            if metric_value < threshold:
                alert = Alert(
                    type=AlertType.QUALITY_GATE_FAILURE,
                    level=AlertLevel.ERROR if metric_value < threshold * 0.8 else AlertLevel.WARNING,
                    title=f"Quality Gate Failed: {metric_key.upper()}",
                    message=f"{metric_key.capitalize()} {metric_value:.1%} is below threshold {threshold:.1%}",
                    timestamp=datetime.now(),
                    metadata={
                        'run_id': run['id'],
                        'metric': metric_key,
                        'value': metric_value,
                        'threshold': threshold,
                        'delta': threshold - metric_value
                    }
                )
                alerts.append(alert)

        return alerts

    def _check_regression(self, current_metrics: Dict, run: Dict) -> List[Alert]:
        """Check for performance regression compared to baseline."""
        alerts = []

        if len(self.metrics_history) < 2:
            return alerts  # Need history to detect regression

        # Calculate baseline (average of last 5 runs, excluding current)
        baseline_count = min(5, len(self.metrics_history) - 1)
        if baseline_count == 0:
            return alerts

        baseline_metrics = {}
        for metric in ['f1', 'precision', 'recall', 'accuracy']:
            values = []
            for i in range(baseline_count):
                hist = self.metrics_history[-(i + 2)]  # Skip last (current)
                values.append(hist['metrics'].get(metric, 0))

            baseline_metrics[metric] = sum(values) / len(values) if values else 0

        # Check for regressions
        for metric, baseline in baseline_metrics.items():
            current = current_metrics.get(metric, 0)
            threshold = self.REGRESSION_THRESHOLDS.get(metric, 0.05)

            if baseline > 0:
                delta = (baseline - current) / baseline

                if delta > threshold:
                    alert = Alert(
                        type=AlertType.PERFORMANCE_REGRESSION,
                        level=AlertLevel.ERROR if delta > threshold * 2 else AlertLevel.WARNING,
                        title=f"Performance Regression: {metric.upper()}",
                        message=f"{metric.capitalize()} dropped {delta:.1%} from baseline (was {baseline:.1%}, now {current:.1%})",
                        timestamp=datetime.now(),
                        metadata={
                            'run_id': run['id'],
                            'metric': metric,
                            'current': current,
                            'baseline': baseline,
                            'delta_percent': delta,
                            'threshold': threshold
                        }
                    )
                    alerts.append(alert)

        return alerts

    def _check_anomalies(self, metrics: Dict, run: Dict) -> List[Alert]:
        """Detect statistical anomalies in metrics."""
        alerts = []

        if len(self.metrics_history) < 10:
            return alerts  # Need sufficient history

        # Check each metric for anomalies (simple z-score approach)
        for metric in ['f1', 'precision', 'recall', 'accuracy']:
            # Get historical values
            values = [h['metrics'].get(metric, 0) for h in list(self.metrics_history)[:-1]]

            if not values:
                continue

            # Calculate mean and std
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std = variance ** 0.5

            if std == 0:
                continue

            # Check current value
            current = metrics.get(metric, 0)
            z_score = abs((current - mean) / std)

            # Alert if z-score > 2.5 (outlier)
            if z_score > 2.5:
                alert = Alert(
                    type=AlertType.ANOMALY_DETECTED,
                    level=AlertLevel.WARNING,
                    title=f"Anomaly Detected: {metric.upper()}",
                    message=f"{metric.capitalize()} {current:.1%} is unusual (z-score: {z_score:.1f}, mean: {mean:.1%})",
                    timestamp=datetime.now(),
                    metadata={
                        'run_id': run['id'],
                        'metric': metric,
                        'value': current,
                        'mean': mean,
                        'std': std,
                        'z_score': z_score
                    }
                )
                alerts.append(alert)

        return alerts

    def _check_trends(self, run: Dict) -> List[Alert]:
        """Analyze trends over time."""
        alerts = []

        if len(self.metrics_history) < 5:
            return alerts

        # Check for consistent degradation over last 5 runs
        for metric in ['f1', 'precision', 'recall']:
            values = [h['metrics'].get(metric, 0) for h in list(self.metrics_history)[-5:]]

            # Check if consistently decreasing
            is_decreasing = all(values[i] >= values[i+1] for i in range(len(values)-1))

            if is_decreasing:
                total_drop = values[0] - values[-1]
                if total_drop > 0.10:  # 10% total drop over 5 runs
                    alert = Alert(
                        type=AlertType.TREND_CHANGE,
                        level=AlertLevel.WARNING,
                        title=f"Degrading Trend: {metric.upper()}",
                        message=f"{metric.capitalize()} has consistently decreased over last 5 runs (total drop: {total_drop:.1%})",
                        timestamp=datetime.now(),
                        metadata={
                            'run_id': run['id'],
                            'metric': metric,
                            'values': values,
                            'total_drop': total_drop
                        }
                    )
                    alerts.append(alert)

        return alerts

    def check_cache_performance(self, cache_stats: Dict, run_id: int) -> List[Alert]:
        """
        Check cache performance and alert if low hit rate.

        Args:
            cache_stats: Dict with cache statistics
            run_id: Benchmark run ID

        Returns:
            List of cache-related alerts
        """
        alerts = []

        hit_rate = cache_stats.get('hit_rate', 0)

        # Alert if cache hit rate is below 30%
        if hit_rate < 30:
            alert = Alert(
                type=AlertType.CACHE_LOW_HIT_RATE,
                level=AlertLevel.INFO if hit_rate > 10 else AlertLevel.WARNING,
                title="Low Cache Hit Rate",
                message=f"Cache hit rate is {hit_rate:.1f}% (expected >30%). Consider reviewing cache configuration or test set uniqueness.",
                timestamp=datetime.now(),
                metadata={
                    'run_id': run_id,
                    'hit_rate': hit_rate,
                    'hits': cache_stats.get('hits', 0),
                    'misses': cache_stats.get('misses', 0),
                    'cache_size': cache_stats.get('size', 0)
                }
            )
            alerts.append(alert)
            self._trigger_alert(alert)

        return alerts

    def _calculate_metrics(self, results: List[Dict]) -> Dict:
        """Calculate metrics from results."""
        tp = fp = tn = fn = 0

        for result in results:
            expected = result['expected']
            predicted = 'duplicate' if result['is_match'] else 'not_duplicate'

            if expected == 'duplicate' and predicted == 'duplicate':
                tp += 1
            elif expected == 'not_duplicate' and predicted == 'duplicate':
                fp += 1
            elif expected == 'not_duplicate' and predicted == 'not_duplicate':
                tn += 1
            elif expected == 'duplicate' and predicted == 'not_duplicate':
                fn += 1

        total = tp + fp + tn + fn
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / total if total > 0 else 0

        return {
            'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
            'precision': precision, 'recall': recall,
            'f1': f1, 'accuracy': accuracy
        }

    def _trigger_alert(self, alert: Alert):
        """
        Trigger an alert - store, log, emit signal, call callbacks.

        Args:
            alert: Alert to trigger
        """
        # Store in history
        self.alerts.append(alert)

        # Log
        log_func = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }.get(alert.level, logger.info)

        log_func(f"ALERT: {alert}")

        # Emit signal
        self.alert_triggered.emit(alert)

        # Call callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback {callback.__name__}: {e}")

    def get_alert_history(self, limit: int = 100, level: Optional[AlertLevel] = None) -> List[Alert]:
        """
        Get recent alerts.

        Args:
            limit: Maximum number of alerts to return
            level: Filter by alert level (optional)

        Returns:
            List of alerts
        """
        alerts = list(self.alerts)

        # Filter by level if specified
        if level:
            alerts = [a for a in alerts if a.level == level]

        # Return most recent
        return alerts[-limit:]

    def get_alert_summary(self) -> Dict:
        """
        Get summary of recent alerts.

        Returns:
            Dict with alert counts by type and level
        """
        summary = {
            'total': len(self.alerts),
            'by_level': {},
            'by_type': {},
            'recent_24h': 0
        }

        # Count by level and type
        for alert in self.alerts:
            # By level
            level_name = alert.level.value
            summary['by_level'][level_name] = summary['by_level'].get(level_name, 0) + 1

            # By type
            type_name = alert.type.value
            summary['by_type'][type_name] = summary['by_type'].get(type_name, 0) + 1

            # Recent (last 24h)
            if (datetime.now() - alert.timestamp).total_seconds() < 86400:
                summary['recent_24h'] += 1

        return summary

    def clear_alerts(self):
        """Clear all stored alerts."""
        self.alerts.clear()
        logger.info("Alert history cleared")

    def set_quality_gates(self, gates: Dict):
        """
        Update quality gate thresholds.

        Args:
            gates: Dict with threshold values (f1_min, precision_min, etc.)
        """
        self.quality_gates.update(gates)
        logger.info(f"Quality gates updated: {gates}")
