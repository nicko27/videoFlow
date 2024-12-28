"""Gestion des paramètres pour le plugin VideoConverter."""

from dataclasses import dataclass, field
from typing import Dict, Any
from pathlib import Path
import json
from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.Settings')

def default_progressive_params() -> Dict[int, Dict[str, Any]]:
    """Retourne les paramètres progressifs par défaut."""
    return {
        1: {  # Première tentative - compression modérée
            "codec": "libx264",
            "crf": 23,
            "preset": "medium"
        },
        2: {  # Deuxième tentative - compression forte
            "codec": "libx264",
            "crf": 28,
            "preset": "slow"
        },
        3: {  # Troisième tentative - compression maximale
            "codec": "libx265",
            "crf": 32,
            "preset": "veryslow"
        }
    }

class ConversionAttempt:
    def __init__(self, crf: int = 28, preset: str = "medium"):
        self.crf = crf
        self.preset = preset
    
    def to_dict(self) -> dict:
        return {
            'crf': self.crf,
            'preset': self.preset
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            crf=data.get('crf', 28),
            preset=data.get('preset', "medium")
        )

class ConversionSettings:
    """Paramètres de conversion."""
    
    def __init__(self):
        """Initialise les paramètres par défaut."""
        # Options de taille
        self.use_size_threshold = True
        self.size_threshold = 100 * 1024 * 1024  # 100 MB par défaut
        
        # Mode manuel
        self.manual_mode = False
        self.crf = 28
        self.preset = "medium"
        
        # Options de suppression
        self.delete_if_smaller = False
        self.delete_if_threshold = False
        self.replace_original = False
        
        # Options de conversion
        self.ignore_converted = True
        self.multiple_attempts = True
        
        # Paramètres des tentatives
        self.attempts = [
            ConversionAttempt(28, "medium"),    # Tentative 1
            ConversionAttempt(30, "slow"),      # Tentative 2
            ConversionAttempt(32, "veryslow")   # Tentative 3
        ]
    
    def to_dict(self) -> dict:
        """Convertit les paramètres en dictionnaire."""
        return {
            'use_size_threshold': self.use_size_threshold,
            'size_threshold': self.size_threshold,
            'manual_mode': self.manual_mode,
            'crf': self.crf,
            'preset': self.preset,
            'delete_if_smaller': self.delete_if_smaller,
            'delete_if_threshold': self.delete_if_threshold,
            'replace_original': self.replace_original,
            'ignore_converted': self.ignore_converted,
            'multiple_attempts': self.multiple_attempts,
            'attempts': [attempt.to_dict() for attempt in self.attempts]
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Crée une instance à partir d'un dictionnaire."""
        settings = cls()
        settings.use_size_threshold = data.get('use_size_threshold', True)
        settings.size_threshold = data.get('size_threshold', 100 * 1024 * 1024)
        settings.manual_mode = data.get('manual_mode', False)
        settings.crf = data.get('crf', 28)
        settings.preset = data.get('preset', "medium")
        settings.delete_if_smaller = data.get('delete_if_smaller', False)
        settings.delete_if_threshold = data.get('delete_if_threshold', False)
        settings.replace_original = data.get('replace_original', False)
        settings.ignore_converted = data.get('ignore_converted', True)
        settings.multiple_attempts = data.get('multiple_attempts', True)
        
        # Charger les paramètres des tentatives
        attempts_data = data.get('attempts', [])
        settings.attempts = []
        for attempt_data in attempts_data:
            settings.attempts.append(ConversionAttempt.from_dict(attempt_data))
        
        # Si pas de tentatives dans les données, créer les valeurs par défaut
        if not settings.attempts:
            settings.attempts = [
                ConversionAttempt(28, "medium"),
                ConversionAttempt(30, "slow"),
                ConversionAttempt(32, "veryslow")
            ]
        return settings

class SettingsManager:
    """Gestionnaire des paramètres."""
    
    @staticmethod
    def load_settings() -> ConversionSettings:
        """Charge les paramètres depuis le fichier de configuration."""
        config_path = Path.home() / '.videoflow' / 'converter_settings.json'
        settings = ConversionSettings()
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                
                # Charger les paramètres de base
                settings = ConversionSettings.from_dict(data)
                
                logger.debug("Paramètres chargés avec succès")
                return settings
            
            except Exception as e:
                logger.error(f"Erreur lors du chargement des paramètres: {e}")
                return ConversionSettings()
        
        logger.debug("Utilisation des paramètres par défaut")
        return settings
    
    @staticmethod
    def save_settings(settings: ConversionSettings):
        """Sauvegarde les paramètres dans le fichier de configuration."""
        config_path = Path.home() / '.videoflow' / 'converter_settings.json'
        
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convertir en dictionnaire
            data = settings.to_dict()
            
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("Paramètres sauvegardés")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des paramètres: {e}")
