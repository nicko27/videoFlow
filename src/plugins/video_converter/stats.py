"""Gestion des statistiques de conversion."""

from dataclasses import dataclass
from typing import Dict, List
from pathlib import Path
import json
from datetime import datetime
from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.Stats')

@dataclass
class ConversionStats:
    """Statistiques d'une conversion."""
    input_size: int
    output_size: int
    duration: float  # en secondes
    attempt_count: int
    params_used: Dict
    success: bool
    date: str = None
    
    def __post_init__(self):
        if self.date is None:
            self.date = datetime.now().isoformat()
    
    @property
    def compression_ratio(self) -> float:
        """Retourne le ratio de compression."""
        return self.output_size / self.input_size if self.input_size > 0 else 0
    
    @property
    def space_saved(self) -> int:
        """Retourne l'espace économisé en octets."""
        return self.input_size - self.output_size

class StatsManager:
    """Gestionnaire des statistiques."""
    
    def __init__(self):
        """Initialise le gestionnaire de statistiques."""
        self.stats_file = Path.home() / '.videoflow' / 'converter_stats.json'
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self.stats: List[ConversionStats] = []
        self.load_stats()
    
    def load_stats(self):
        """Charge les statistiques depuis le fichier."""
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    self.stats = [ConversionStats(**stat) for stat in data]
        except Exception as e:
            logger.error(f"Erreur lors du chargement des statistiques: {e}")
    
    def save_stats(self):
        """Sauvegarde les statistiques dans le fichier."""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump([stat.__dict__ for stat in self.stats], f, indent=2)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des statistiques: {e}")
    
    def add_stat(self, stat: ConversionStats):
        """Ajoute une statistique."""
        self.stats.append(stat)
        self.save_stats()
    
    def get_total_space_saved(self) -> int:
        """Retourne l'espace total économisé."""
        return sum(stat.space_saved for stat in self.stats if stat.success)
    
    def get_average_compression_ratio(self) -> float:
        """Retourne le ratio de compression moyen."""
        successful_stats = [stat for stat in self.stats if stat.success]
        if not successful_stats:
            return 0
        return sum(stat.compression_ratio for stat in successful_stats) / len(successful_stats)
    
    def get_success_rate(self) -> float:
        """Retourne le taux de réussite."""
        if not self.stats:
            return 0
        return len([stat for stat in self.stats if stat.success]) / len(self.stats)
    
    def get_average_attempts(self) -> float:
        """Retourne le nombre moyen de tentatives."""
        if not self.stats:
            return 0
        return sum(stat.attempt_count for stat in self.stats) / len(self.stats)
