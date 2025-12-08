"""Optimized conversion statistics management."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json
import threading
from datetime import datetime, timedelta
from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.Stats')

@dataclass
class ConversionStats:
    """Statistics for individual conversion."""
    input_size: int
    output_size: int
    duration: float  # in seconds
    attempt_count: int
    params_used: Dict
    success: bool
    date: str = field(default_factory=lambda: datetime.now().isoformat())
    input_file: str = ""
    output_file: str = ""
    
    def __post_init__(self):
        """Data validation after initialization."""
        # Validate and correct values
        self.input_size = max(0, int(self.input_size or 0))
        self.output_size = max(0, int(self.output_size or 0))
        self.duration = max(0.0, float(self.duration or 0.0))
        self.attempt_count = max(1, int(self.attempt_count or 1))
        
        if not isinstance(self.params_used, dict):
            self.params_used = {}
        
        if not isinstance(self.success, bool):
            self.success = bool(self.success)
    
    @property
    def compression_ratio(self) -> float:
        """Returns compression ratio (0.0 to 1.0)."""
        if self.input_size > 0:
            return self.output_size / self.input_size
        return 1.0
    
    @property
    def compression_percentage(self) -> float:
        """Returns compression percentage (positive = size reduction)."""
        if self.input_size > 0:
            return ((self.input_size - self.output_size) / self.input_size) * 100
        return 0.0
    
    @property
    def space_saved(self) -> int:
        """Returns space saved in bytes."""
        return max(0, self.input_size - self.output_size)
    
    @property
    def space_saved_percentage(self) -> float:
        """Returns space saved as percentage."""
        if self.input_size > 0:
            return (self.space_saved / self.input_size) * 100
        return 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'input_size': self.input_size,
            'output_size': self.output_size,
            'duration': self.duration,
            'attempt_count': self.attempt_count,
            'params_used': self.params_used,
            'success': self.success,
            'date': self.date,
            'input_file': self.input_file,
            'output_file': self.output_file
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create instance from dictionary."""
        return cls(
            input_size=data.get('input_size', 0),
            output_size=data.get('output_size', 0),
            duration=data.get('duration', 0.0),
            attempt_count=data.get('attempt_count', 1),
            params_used=data.get('params_used', {}),
            success=data.get('success', False),
            date=data.get('date', datetime.now().isoformat()),
            input_file=data.get('input_file', ''),
            output_file=data.get('output_file', '')
        )

class StatsManager:
    """Thread-safe and optimized statistics manager."""
    
    _instance: Optional['StatsManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize statistics manager."""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.stats_file = Path.home() / '.videoflow' / 'converter_stats.json'
        self.stats_lock = threading.RLock()  # Reentrant lock
        self.stats: List[ConversionStats] = []
        self.max_stats = 1000  # Limit to avoid excessive growth

        # Cache for calculated statistics
        self._summary_cache = None
        self._cache_timestamp = 0

        # Ensure folder exists
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing statistics
        self.load_stats()
    
    def _invalidate_cache(self):
        """Invalidate calculated statistics cache."""
        self._summary_cache = None
        self._cache_timestamp = 0
    
    def load_stats(self) -> bool:
        """Load statistics from file."""
        with self.stats_lock:
            try:
                if self.stats_file.exists():
                    with open(self.stats_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if isinstance(data, list):
                        self.stats = []
                        valid_count = 0
                        
                        for stat_data in data:
                            if isinstance(stat_data, dict):
                                try:
                                    stat = ConversionStats.from_dict(stat_data)
                                    self.stats.append(stat)
                                    valid_count += 1
                                except Exception as e:
                                    logger.warning(f"Invalid statistic ignored: {e}")

                        # Limit number of statistics
                        if len(self.stats) > self.max_stats:
                            self.stats = self.stats[-self.max_stats:]
                            logger.debug(f"Statistics limited to last {self.max_stats} entries")
                        
                        self._invalidate_cache()
                        logger.debug(f"Loaded {valid_count} valid statistics")
                        return True
                    else:
                        logger.warning("Invalid statistics file format")
                        return False
                else:
                    logger.debug("No statistics file found, starting fresh")
                    return True
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in statistics file: {e}")
                return False
            except Exception as e:
                logger.error(f"Error loading statistics: {e}")
                return False
    
    def save_stats(self) -> bool:
        """Save statistics to file."""
        with self.stats_lock:
            try:
                # Create backup
                backup_file = self.stats_file.with_suffix('.json.bak')
                if self.stats_file.exists():
                    try:
                        import shutil
                        shutil.copy2(self.stats_file, backup_file)
                    except Exception as e:
                        logger.warning(f"Cannot create backup: {e}")

                # Write to temporary file first
                temp_file = self.stats_file.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump([stat.to_dict() for stat in self.stats], f, indent=2, ensure_ascii=False)

                # Move temporary file
                temp_file.replace(self.stats_file)

                logger.debug(f"Saved {len(self.stats)} statistics")
                return True
                
            except Exception as e:
                logger.error(f"Error saving statistics: {e}")
                # Clean up temporary file
                temp_file = self.stats_file.with_suffix('.tmp')
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass
                return False
    
    def add_stat(self, stat: ConversionStats) -> bool:
        """Add statistic."""
        if not isinstance(stat, ConversionStats):
            logger.error("Invalid statistic type")
            return False
            
        with self.stats_lock:
            try:
                self.stats.append(stat)

                # Limit number of entries
                if len(self.stats) > self.max_stats:
                    self.stats = self.stats[-self.max_stats:]
                    logger.debug(f"Statistics limited to last {self.max_stats} entries")
                
                self._invalidate_cache()
                return self.save_stats()

            except Exception as e:
                logger.error(f"Error adding statistic: {e}")
                return False
    
    def get_stats_summary(self) -> Dict:
        """Get statistics summary with cache."""
        with self.stats_lock:
            # Check cache
            current_time = datetime.now().timestamp()
            if (self._summary_cache and
                current_time - self._cache_timestamp < 60):  # Cache valid 1 minute
                return self._summary_cache
            
            if not self.stats:
                summary = {
                    'total_conversions': 0,
                    'successful_conversions': 0,
                    'failed_conversions': 0,
                    'success_rate': 0.0,
                    'total_space_saved': 0,
                    'average_compression': 0.0,
                    'average_attempts': 0.0,
                    'total_input_size': 0,
                    'total_output_size': 0,
                    'best_compression': 0.0,
                    'worst_compression': 0.0
                }
            else:
                successful_stats = [stat for stat in self.stats if stat.success]
                failed_stats = [stat for stat in self.stats if not stat.success]
                
                total_input_size = sum(stat.input_size for stat in self.stats)
                total_output_size = sum(stat.output_size for stat in successful_stats)
                total_space_saved = sum(stat.space_saved for stat in successful_stats)

                # Compression calculations
                compressions = [stat.space_saved_percentage for stat in successful_stats if stat.space_saved_percentage > 0]
                best_compression = max(compressions) if compressions else 0.0
                worst_compression = min(compressions) if compressions else 0.0
                avg_compression = sum(compressions) / len(compressions) if compressions else 0.0
                
                summary = {
                    'total_conversions': len(self.stats),
                    'successful_conversions': len(successful_stats),
                    'failed_conversions': len(failed_stats),
                    'success_rate': len(successful_stats) / len(self.stats) * 100 if self.stats else 0,
                    'total_space_saved': total_space_saved,
                    'average_compression': avg_compression,
                    'average_attempts': sum(stat.attempt_count for stat in self.stats) / len(self.stats),
                    'total_input_size': total_input_size,
                    'total_output_size': total_output_size,
                    'best_compression': best_compression,
                    'worst_compression': worst_compression
                }

            # Update cache
            self._summary_cache = summary
            self._cache_timestamp = current_time
            
            return summary
    
    def get_total_space_saved(self) -> int:
        """Returns total space saved in bytes."""
        with self.stats_lock:
            return sum(stat.space_saved for stat in self.stats if stat.success)
    
    def get_average_compression_ratio(self) -> float:
        """Returns average compression ratio."""
        with self.stats_lock:
            successful_stats = [stat for stat in self.stats if stat.success and stat.input_size > 0]
            if not successful_stats:
                return 0.0
            return sum(stat.compression_ratio for stat in successful_stats) / len(successful_stats)
    
    def get_success_rate(self) -> float:
        """Returns success rate as percentage."""
        with self.stats_lock:
            if not self.stats:
                return 0.0
            successful_count = sum(1 for stat in self.stats if stat.success)
            return (successful_count / len(self.stats)) * 100
    
    def get_average_attempts(self) -> float:
        """Returns average number of attempts."""
        with self.stats_lock:
            if not self.stats:
                return 0.0
            return sum(stat.attempt_count for stat in self.stats) / len(self.stats)
    
    def get_recent_stats(self, days: int = 30) -> List[ConversionStats]:
        """Get statistics for recent days."""
        with self.stats_lock:
            cutoff_date = datetime.now() - timedelta(days=days)

            recent_stats = []
            for stat in self.stats:
                try:
                    # Handle date formats with and without timezone
                    date_str = stat.date.replace('Z', '+00:00') if stat.date.endswith('Z') else stat.date
                    stat_date = datetime.fromisoformat(date_str.replace('+00:00', ''))
                    
                    if stat_date >= cutoff_date:
                        recent_stats.append(stat)
                except (ValueError, AttributeError):
                    # Ignore statistics with invalid dates
                    continue
            
            return recent_stats
    
    def get_stats_by_params(self) -> Dict[str, Dict]:
        """Get statistics grouped by settings."""
        with self.stats_lock:
            params_stats = {}

            for stat in self.stats:
                if not stat.success:
                    continue

                # Create key based on main settings
                crf = stat.params_used.get('crf', 'unknown')
                preset = stat.params_used.get('preset', 'unknown')
                key = f"CRF{crf}_{preset}"
                
                if key not in params_stats:
                    params_stats[key] = {
                        'count': 0,
                        'total_compression': 0.0,
                        'total_attempts': 0,
                        'total_space_saved': 0
                    }
                
                params_stats[key]['count'] += 1
                params_stats[key]['total_compression'] += stat.space_saved_percentage
                params_stats[key]['total_attempts'] += stat.attempt_count
                params_stats[key]['total_space_saved'] += stat.space_saved

            # Calculate averages
            for key, data in params_stats.items():
                if data['count'] > 0:
                    data['avg_compression'] = data['total_compression'] / data['count']
                    data['avg_attempts'] = data['total_attempts'] / data['count']
                else:
                    data['avg_compression'] = 0.0
                    data['avg_attempts'] = 0.0
            
            return params_stats
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict]:
        """Get statistics by hour."""
        with self.stats_lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            hourly_data = {}
            
            for stat in self.stats:
                try:
                    date_str = stat.date.replace('Z', '+00:00') if stat.date.endswith('Z') else stat.date
                    stat_date = datetime.fromisoformat(date_str.replace('+00:00', ''))
                    
                    if stat_date >= cutoff_time:
                        hour_key = stat_date.strftime('%Y-%m-%d %H:00')
                        
                        if hour_key not in hourly_data:
                            hourly_data[hour_key] = {
                                'hour': hour_key,
                                'total': 0,
                                'successful': 0,
                                'failed': 0,
                                'space_saved': 0
                            }
                        
                        hourly_data[hour_key]['total'] += 1
                        if stat.success:
                            hourly_data[hour_key]['successful'] += 1
                            hourly_data[hour_key]['space_saved'] += stat.space_saved
                        else:
                            hourly_data[hour_key]['failed'] += 1
                
                except (ValueError, AttributeError):
                    continue
            
            return sorted(hourly_data.values(), key=lambda x: x['hour'])
    
    def clear_stats(self) -> bool:
        """Clear all statistics."""
        with self.stats_lock:
            self.stats.clear()
            self._invalidate_cache()
            return self.save_stats()
    
    def export_stats(self, file_path: Path) -> bool:
        """Export statistics to file."""
        with self.stats_lock:
            try:
                export_data = {
                    'exported_at': datetime.now().isoformat(),
                    'export_version': '1.0.1',
                    'total_stats': len(self.stats),
                    'summary': self.get_stats_summary(),
                    'stats': [stat.to_dict() for stat in self.stats]
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                logger.info(f"Statistics exported to {file_path}")
                return True
            except Exception as e:
                logger.error(f"Error exporting statistics: {e}")
                return False
    
    def import_stats(self, file_path: Path, merge: bool = True) -> bool:
        """Import statistics from file."""
        with self.stats_lock:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Handle different export formats
                if 'stats' in data:
                    # New format with metadata
                    stats_data = data['stats']
                elif isinstance(data, list):
                    # Old format - direct list
                    stats_data = data
                else:
                    logger.error("Unrecognized import file format")
                    return False
                
                imported_stats = []
                for stat_data in stats_data:
                    if isinstance(stat_data, dict):
                        try:
                            stat = ConversionStats.from_dict(stat_data)
                            imported_stats.append(stat)
                        except Exception as e:
                            logger.warning(f"Invalid import statistic ignored: {e}")
                
                if merge:
                    self.stats.extend(imported_stats)

                    # Remove duplicates based on date and file
                    seen = set()
                    unique_stats = []
                    for stat in self.stats:
                        key = (stat.date, stat.input_file)
                        if key not in seen:
                            seen.add(key)
                            unique_stats.append(stat)
                    
                    self.stats = unique_stats
                else:
                    self.stats = imported_stats

                # Limit number of statistics
                if len(self.stats) > self.max_stats:
                    self.stats = sorted(self.stats, key=lambda x: x.date)[-self.max_stats:]
                
                self._invalidate_cache()
                success = self.save_stats()

                if success:
                    logger.info(f"Imported {len(imported_stats)} statistics from {file_path}")
                return success

            except Exception as e:
                logger.error(f"Error importing statistics: {e}")
                return False
    
    def cleanup_old_stats(self, days: int = 90) -> int:
        """Clean up old statistics."""
        with self.stats_lock:
            cutoff_date = datetime.now() - timedelta(days=days)
            original_count = len(self.stats)
            
            filtered_stats = []
            for stat in self.stats:
                try:
                    date_str = stat.date.replace('Z', '+00:00') if stat.date.endswith('Z') else stat.date
                    stat_date = datetime.fromisoformat(date_str.replace('+00:00', ''))
                    
                    if stat_date >= cutoff_date:
                        filtered_stats.append(stat)
                except (ValueError, AttributeError):
                    # Keep statistics with invalid dates (probably recent)
                    filtered_stats.append(stat)
            
            self.stats = filtered_stats
            removed_count = original_count - len(self.stats)
            
            if removed_count > 0:
                self._invalidate_cache()
                self.save_stats()
                logger.info(f"Cleaned {removed_count} old statistics")

            return removed_count
    
    def get_top_conversions(self, limit: int = 10, by: str = 'space_saved') -> List[ConversionStats]:
        """Get best conversions by criterion."""
        with self.stats_lock:
            successful_stats = [stat for stat in self.stats if stat.success]
            
            if by == 'space_saved':
                sorted_stats = sorted(successful_stats, key=lambda x: x.space_saved, reverse=True)
            elif by == 'compression_percentage':
                sorted_stats = sorted(successful_stats, key=lambda x: x.space_saved_percentage, reverse=True)
            elif by == 'size':
                sorted_stats = sorted(successful_stats, key=lambda x: x.input_size, reverse=True)
            else:
                sorted_stats = successful_stats
            
            return sorted_stats[:limit]
    
    def get_failure_analysis(self) -> Dict:
        """Analyze conversion failures."""
        with self.stats_lock:
            failed_stats = [stat for stat in self.stats if not stat.success]

            if not failed_stats:
                return {'total_failures': 0}

            # Analyze by number of attempts
            attempts_analysis = {}
            for stat in failed_stats:
                attempts = stat.attempt_count
                if attempts not in attempts_analysis:
                    attempts_analysis[attempts] = 0
                attempts_analysis[attempts] += 1

            # Analyze by settings
            params_analysis = {}
            for stat in failed_stats:
                crf = stat.params_used.get('crf', 'unknown')
                preset = stat.params_used.get('preset', 'unknown')
                key = f"CRF{crf}_{preset}"
                
                if key not in params_analysis:
                    params_analysis[key] = 0
                params_analysis[key] += 1
            
            return {
                'total_failures': len(failed_stats),
                'failure_rate': len(failed_stats) / len(self.stats) * 100 if self.stats else 0,
                'attempts_analysis': attempts_analysis,
                'params_analysis': params_analysis,
                'avg_attempts_on_failure': sum(stat.attempt_count for stat in failed_stats) / len(failed_stats)
            }
    
    def optimize_settings_recommendation(self) -> Dict:
        """Recommend optimal settings based on statistics."""
        with self.stats_lock:
            successful_stats = [stat for stat in self.stats if stat.success]

            if len(successful_stats) < 5:  # Not enough data
                return {
                    'recommendation': 'Not enough data for recommendation',
                    'min_data_needed': 5,
                    'current_data': len(successful_stats)
                }

            # Analyze best settings
            params_performance = {}
            
            for stat in successful_stats:
                crf = stat.params_used.get('crf', 28)
                preset = stat.params_used.get('preset', 'fast')
                key = f"{crf}_{preset}"
                
                if key not in params_performance:
                    params_performance[key] = {
                        'compression_sum': 0,
                        'attempts_sum': 0,
                        'count': 0,
                        'crf': crf,
                        'preset': preset
                    }
                
                params_performance[key]['compression_sum'] += stat.space_saved_percentage
                params_performance[key]['attempts_sum'] += stat.attempt_count
                params_performance[key]['count'] += 1

            # Calculate average performance
            best_params = None
            best_score = 0

            for key, data in params_performance.items():
                if data['count'] >= 3:  # Minimum data to be reliable
                    avg_compression = data['compression_sum'] / data['count']
                    avg_attempts = data['attempts_sum'] / data['count']

                    # Score based on compression and efficiency (fewer attempts = better)
                    score = avg_compression - (avg_attempts - 1) * 5  # Penalty for multiple attempts
                    
                    if score > best_score:
                        best_score = score
                        best_params = {
                            'crf': data['crf'],
                            'preset': data['preset'],
                            'avg_compression': avg_compression,
                            'avg_attempts': avg_attempts,
                            'sample_count': data['count']
                        }

            return {
                'recommendation': 'Optimal settings found' if best_params else 'No optimal settings identified',
                'best_params': best_params,
                'total_successful_conversions': len(successful_stats)
            }
