"""Handling des statistics de conversion optimisée."""

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
    """Statistics pour une conversion individuelle."""
    input_size: int
    output_size: int
    duration: float  # en secondes
    attempt_count: int
    params_used: Dict
    success: bool
    date: str = field(default_factory=lambda: datetime.now().isoformat())
    input_file: str = ""
    output_file: str = ""
    
    def __post_init__(self):
        """Validation des données après initialization."""
        # Validation et correction des valeurs
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
        """Returnsr le ratio de compression (0.0 à 1.0)."""
        if self.input_size > 0:
            return self.output_size / self.input_size
        return 1.0
    
    @property
    def compression_percentage(self) -> float:
        """Returnsr le pourcentage de compression (négatif = réduction)."""
        if self.input_size > 0:
            return ((self.output_size - self.input_size) / self.input_size) * 100
        return 0.0
    
    @property
    def space_saved(self) -> int:
        """Returnsr l'espace économisé en octets."""
        return max(0, self.input_size - self.output_size)
    
    @property
    def space_saved_percentage(self) -> float:
        """Returnsr l'espace économisé en pourcentage."""
        if self.input_size > 0:
            return (self.space_saved / self.input_size) * 100
        return 0.0
    
    def to_dict(self) -> dict:
        """Convertir en dictionnaire pour sérialisation JSON."""
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
        """Créer une instance depuis un dictionnaire."""
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
    """Handlingnaire de statistics thread-safe et optimisé."""
    
    _instance: Optional['StatsManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implémentation du pattern Singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialiser le gestionnaire de statistics."""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.stats_file = Path.home() / '.videoflow' / 'converter_stats.json'
        self.stats_lock = threading.RLock()  # Verrou réentrant
        self.stats: List[ConversionStats] = []
        self.max_stats = 1000  # Limite pour éviter la croissance excessive
        
        # Cache pour les statistics calculées
        self._summary_cache = None
        self._cache_timestamp = 0
        
        # S'asoner que le folder existe
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load les statistics existantes
        self.load_stats()
    
    def _invalidate_cache(self):
        """Invalider le cache des statistics calculées."""
        self._summary_cache = None
        self._cache_timestamp = 0
    
    def load_stats(self) -> bool:
        """Load les statistics depuis le file."""
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
                                    logger.warning(f"Statistique invalide ignorée: {e}")
                        
                        # Limiter le number de statistics
                        if len(self.stats) > self.max_stats:
                            self.stats = self.stats[-self.max_stats:]
                            logger.debug(f"Statistics limitées aux {self.max_stats} dernières entrées")
                        
                        self._invalidate_cache()
                        logger.debug(f"Chargé {valid_count} statistics valides")
                        return True
                    else:
                        logger.warning("Format de file de statistics invalide")
                        return False
                else:
                    logger.debug("Aucun file de statistics found, démarrage à neuf")
                    return True
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON invalide in le file de statistics: {e}")
                return False
            except Exception as e:
                logger.error(f"Error loading des statistics: {e}")
                return False
    
    def save_stats(self) -> bool:
        """Save les statistics in le file."""
        with self.stats_lock:
            try:
                # Créer une sauvegarde
                backup_file = self.stats_file.with_suffix('.json.bak')
                if self.stats_file.exists():
                    try:
                        import shutil
                        shutil.copy2(self.stats_file, backup_file)
                    except Exception as e:
                        logger.warning(f"Cannot créer une sauvegarde: {e}")
                
                # Écrire in un file temporaire d'abord
                temp_file = self.stats_file.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump([stat.to_dict() for stat in self.stats], f, indent=2, ensure_ascii=False)
                
                # Déplacer le file temporaire
                temp_file.replace(self.stats_file)
                
                logger.debug(f"Sauvegardé {len(self.stats)} statistics")
                return True
                
            except Exception as e:
                logger.error(f"Error saving des statistics: {e}")
                # Nettoyer le file temporaire
                temp_file = self.stats_file.with_suffix('.tmp')
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass
                return False
    
    def add_stat(self, stat: ConversionStats) -> bool:
        """Add une statistique."""
        if not isinstance(stat, ConversionStats):
            logger.error("Type de statistique invalide")
            return False
            
        with self.stats_lock:
            try:
                self.stats.append(stat)
                
                # Limiter le number d'entrées
                if len(self.stats) > self.max_stats:
                    self.stats = self.stats[-self.max_stats:]
                    logger.debug(f"Statistics limitées aux {self.max_stats} dernières entrées")
                
                self._invalidate_cache()
                return self.save_stats()
                
            except Exception as e:
                logger.error(f"Error during l'ajout de statistique: {e}")
                return False
    
    def get_stats_summary(self) -> Dict:
        """Obtenir un résumé des statistics with cache."""
        with self.stats_lock:
            # Checksr le cache
            current_time = datetime.now().timestamp()
            if (self._summary_cache and 
                current_time - self._cache_timestamp < 60):  # Cache valide 1 minute
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
                
                # Calculs de compression
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
            
            # Mettre à jour le cache
            self._summary_cache = summary
            self._cache_timestamp = current_time
            
            return summary
    
    def get_total_space_saved(self) -> int:
        """Returnsr l'espace total économisé en octets."""
        with self.stats_lock:
            return sum(stat.space_saved for stat in self.stats if stat.success)
    
    def get_average_compression_ratio(self) -> float:
        """Returnsr le ratio de compression moyen."""
        with self.stats_lock:
            successful_stats = [stat for stat in self.stats if stat.success and stat.input_size > 0]
            if not successful_stats:
                return 0.0
            return sum(stat.compression_ratio for stat in successful_stats) / len(successful_stats)
    
    def get_success_rate(self) -> float:
        """Returnsr le rate de réussite en pourcentage."""
        with self.stats_lock:
            if not self.stats:
                return 0.0
            successful_count = sum(1 for stat in self.stats if stat.success)
            return (successful_count / len(self.stats)) * 100
    
    def get_average_attempts(self) -> float:
        """Returnsr le number moyen de tentatives."""
        with self.stats_lock:
            if not self.stats:
                return 0.0
            return sum(stat.attempt_count for stat in self.stats) / len(self.stats)
    
    def get_recent_stats(self, days: int = 30) -> List[ConversionStats]:
        """Obtenir les statistics des derniers jours."""
        with self.stats_lock:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            recent_stats = []
            for stat in self.stats:
                try:
                    # Gérer les formats de date with et sans timezone
                    date_str = stat.date.replace('Z', '+00:00') if stat.date.endswith('Z') else stat.date
                    stat_date = datetime.fromisoformat(date_str.replace('+00:00', ''))
                    
                    if stat_date >= cutoff_date:
                        recent_stats.append(stat)
                except (ValueError, AttributeError):
                    # Ignorer les statistics with des dates invalides
                    continue
            
            return recent_stats
    
    def get_stats_by_params(self) -> Dict[str, Dict]:
        """Obtenir les statistics groupées par settings."""
        with self.stats_lock:
            params_stats = {}
            
            for stat in self.stats:
                if not stat.success:
                    continue
                
                # Créer une clé basée on les settings principaux
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
            
            # Calculatesr les moyennes
            for key, data in params_stats.items():
                if data['count'] > 0:
                    data['avg_compression'] = data['total_compression'] / data['count']
                    data['avg_attempts'] = data['total_attempts'] / data['count']
                else:
                    data['avg_compression'] = 0.0
                    data['avg_attempts'] = 0.0
            
            return params_stats
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict]:
        """Obtenir les statistics par heure."""
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
        """Vider toutes les statistics."""
        with self.stats_lock:
            self.stats.clear()
            self._invalidate_cache()
            return self.save_stats()
    
    def export_stats(self, file_path: Path) -> bool:
        """Exporter les statistics vers un file."""
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
                
                logger.info(f"Statistics exportées vers {file_path}")
                return True
            except Exception as e:
                logger.error(f"Error during l'exportation des statistics: {e}")
                return False
    
    def import_stats(self, file_path: Path, merge: bool = True) -> bool:
        """Importer les statistics depuis un file."""
        with self.stats_lock:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Gérer différents formats d'export
                if 'stats' in data:
                    # Nouveau format with métadonnées
                    stats_data = data['stats']
                elif isinstance(data, list):
                    # Ancien format - liste directe
                    stats_data = data
                else:
                    logger.error("Format de file d'importation non reconnu")
                    return False
                
                imported_stats = []
                for stat_data in stats_data:
                    if isinstance(stat_data, dict):
                        try:
                            stat = ConversionStats.from_dict(stat_data)
                            imported_stats.append(stat)
                        except Exception as e:
                            logger.warning(f"Statistique d'importation invalide ignorée: {e}")
                
                if merge:
                    self.stats.extend(imported_stats)
                    
                    # Remove les doublons basés on la date et le file
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
                
                # Limiter le number de statistics
                if len(self.stats) > self.max_stats:
                    self.stats = sorted(self.stats, key=lambda x: x.date)[-self.max_stats:]
                
                self._invalidate_cache()
                success = self.save_stats()
                
                if success:
                    logger.info(f"Importé {len(imported_stats)} statistics depuis {file_path}")
                return success
                
            except Exception as e:
                logger.error(f"Error during l'importation des statistics: {e}")
                return False
    
    def cleanup_old_stats(self, days: int = 90) -> int:
        """Nettoyer les statistics anciennes."""
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
                    # Garder les statistics with des dates invalides (récentes probablement)
                    filtered_stats.append(stat)
            
            self.stats = filtered_stats
            removed_count = original_count - len(self.stats)
            
            if removed_count > 0:
                self._invalidate_cache()
                self.save_stats()
                logger.info(f"Nettoyé {removed_count} anciennes statistics")
            
            return removed_count
    
    def get_top_conversions(self, limit: int = 10, by: str = 'space_saved') -> List[ConversionStats]:
        """Obtenir les meilleures conversions selon un critère."""
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
        """Analyze les échecs de conversion."""
        with self.stats_lock:
            failed_stats = [stat for stat in self.stats if not stat.success]
            
            if not failed_stats:
                return {'total_failures': 0}
            
            # Analyze par number de tentatives
            attempts_analysis = {}
            for stat in failed_stats:
                attempts = stat.attempt_count
                if attempts not in attempts_analysis:
                    attempts_analysis[attempts] = 0
                attempts_analysis[attempts] += 1
            
            # Analyze par settings
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
        """Recommander des settings optimaux basés on les statistics."""
        with self.stats_lock:
            successful_stats = [stat for stat in self.stats if stat.success]
            
            if len(successful_stats) < 5:  # Pas assez de données
                return {
                    'recommendation': 'Pas assez de données pour une recommandation',
                    'min_data_needed': 5,
                    'current_data': len(successful_stats)
                }
            
            # Analyze les meilleurs settings
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
            
            # Calculatesr les performances moyennes
            best_params = None
            best_score = 0
            
            for key, data in params_performance.items():
                if data['count'] >= 3:  # Minimum de données pour être fiable
                    avg_compression = data['compression_sum'] / data['count']
                    avg_attempts = data['attempts_sum'] / data['count']
                    
                    # Score basé on compression et efficacité (moins de tentatives = mieux)
                    score = avg_compression - (avg_attempts - 1) * 5  # Pénalité pour les tentatives multiples
                    
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
                'recommendation': 'Settings optimaux found' if best_params else 'Pas de settings optimaux identifiés',
                'best_params': best_params,
                'total_successful_conversions': len(successful_stats)
            }