"""Gestion des paramètres optimisée pour VideoConverter plugin."""

from dataclasses import dataclass
from typing import Dict, Any, List
from pathlib import Path
import json
from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.Settings')

class ConversionAttempt:
    """Configuration d'une tentative de conversion."""
    
    def __init__(self, crf: int = 28, preset: str = "fast"):
        self.crf = self.validate_crf(crf)
        self.preset = self.validate_preset(preset)
    
    @staticmethod
    def validate_crf(crf: int) -> int:
        """Valider la valeur CRF."""
        if not isinstance(crf, int):
            logger.warning(f"Type CRF invalide: {type(crf)}, utilisation de la valeur par défaut")
            return 28
        return max(18, min(35, crf))  # Plage réduite pour de meilleurs résultats
    
    @staticmethod
    def validate_preset(preset: str) -> str:
        """Valider la valeur preset."""
        valid_presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", 
                        "medium", "slow", "slower", "veryslow"]
        if preset not in valid_presets:
            logger.warning(f"Preset invalide: {preset}, utilisation de 'fast'")
            return "fast"
        return preset
    
    def to_dict(self) -> dict:
        """Convertir en dictionnaire."""
        return {
            'crf': self.crf,
            'preset': self.preset
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Créer depuis un dictionnaire."""
        return cls(
            crf=data.get('crf', 28),
            preset=data.get('preset', "fast")
        )

class ConversionSettings:
    """Paramètres de conversion optimisés avec valeurs par défaut améliorées."""
    
    def __init__(self):
        """Initialiser avec des paramètres optimisés."""
        # Options de taille - seuil plus raisonnable
        self.use_size_threshold = True
        self.size_threshold = 500 * 1024 * 1024  # 500 MB par défaut (plus raisonnable)
        
        # Mode manuel avec paramètres équilibrés
        self.manual_mode = False
        self.crf = 28  # Équilibre qualité/taille
        self.preset = "fast"  # Plus rapide que medium
        
        # Options de suppression - plus conservatrices
        self.delete_if_smaller = False
        self.delete_if_threshold = False
        self.replace_original = False
        
        # Options de conversion - plus permissives
        self.ignore_converted = True
        self.multiple_attempts = True
        
        # Paramètre de concurrence
        import os
        cpu_count = os.cpu_count() or 1
        self.max_concurrent_conversions = min(cpu_count, 4)  # Par défaut: min(CPU, 4)
        
        # Tentatives optimisées pour efficacité
        self.attempts = [
            ConversionAttempt(28, "fast"),      # Tentative 1: rapide et équilibré
            ConversionAttempt(30, "medium"),    # Tentative 2: compression plus forte
            ConversionAttempt(32, "slow")       # Tentative 3: compression maximale
        ]

        # Gestion des suffixes
        self.converted_suffix = '_cvt'
        self.failed_suffix = '_nocomp'
        
        # Options de gestion des fichiers traités
        self.ignore_converted_files = True
        self.mark_non_compressible = False
        self.ignore_non_compressible = False
        
        # Extensions supportées
        self.video_extensions = 'mp4,avi,mkv,mov,flv,webm,wmv'
        
        # Options audio et compatibilité
        self.audio_copy = True
        self.faststart = True
        self.avoid_negative_ts = True
    
    def validate_and_fix(self):
        """Valider et corriger tous les paramètres."""
        # Valider le seuil de taille
        if not isinstance(self.size_threshold, (int, float)) or self.size_threshold <= 0:
            logger.warning("Seuil de taille invalide, utilisation de 500MB par défaut")
            self.size_threshold = 500 * 1024 * 1024
        
        # Limiter le seuil maximum pour éviter les valeurs aberrantes
        max_threshold = 10 * 1024 * 1024 * 1024  # 10GB max
        if self.size_threshold > max_threshold:
            logger.warning(f"Seuil de taille trop élevé, limitation à {max_threshold // (1024*1024*1024)}GB")
            self.size_threshold = max_threshold
        
        # Valider CRF et preset
        self.crf = ConversionAttempt.validate_crf(self.crf)
        self.preset = ConversionAttempt.validate_preset(self.preset)
        
        # Valider les paramètres booléens
        bool_settings = [
            'use_size_threshold', 'manual_mode', 'delete_if_smaller',
            'delete_if_threshold', 'replace_original', 'ignore_converted',
            'multiple_attempts'
        ]
        
        for setting in bool_settings:
            value = getattr(self, setting, False)
            if not isinstance(value, bool):
                logger.warning(f"Paramètre booléen invalide {setting}, utilisation de False")
                setattr(self, setting, False)
        
        # Valider le nombre de conversions simultanées
        if not isinstance(self.max_concurrent_conversions, int) or self.max_concurrent_conversions < 1:
            import os
            cpu_count = os.cpu_count() or 1
            self.max_concurrent_conversions = min(cpu_count, 4)
            logger.warning(f"Nombre de threads invalide, utilisation de {self.max_concurrent_conversions}")
        
        # Limiter entre 1 et 8 threads
        self.max_concurrent_conversions = max(1, min(8, self.max_concurrent_conversions))
        
        # Valider et corriger les tentatives
        if not isinstance(self.attempts, list) or len(self.attempts) == 0:
            logger.warning("Configuration des tentatives invalide, utilisation des valeurs par défaut")
            self.attempts = [
                ConversionAttempt(28, "fast"),
                ConversionAttempt(30, "medium"),
                ConversionAttempt(32, "slow")
            ]
        
        # S'assurer d'avoir exactement 3 tentatives
        while len(self.attempts) < 3:
            self.attempts.append(ConversionAttempt(32, "slow"))
        
        if len(self.attempts) > 3:
            self.attempts = self.attempts[:3]
            logger.warning("Trop de tentatives configurées, utilisation des 3 premières")
        
        # Valider chaque tentative
        for i, attempt in enumerate(self.attempts):
            if not isinstance(attempt, ConversionAttempt):
                logger.warning(f"Tentative {i+1} invalide, remplacement par défaut")
                self.attempts[i] = ConversionAttempt(28 + i*2, ["fast", "medium", "slow"][i])
    
    def to_dict(self) -> dict:
        """Convertir les paramètres en dictionnaire."""
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
            'max_concurrent_conversions': self.max_concurrent_conversions,
            'attempts': [attempt.to_dict() for attempt in self.attempts],
            'converted_suffix': self.converted_suffix,
            'failed_suffix': self.failed_suffix,
            'ignore_converted_files': self.ignore_converted_files,
            'mark_non_compressible': self.mark_non_compressible,
            'ignore_non_compressible': self.ignore_non_compressible,
            'video_extensions': self.video_extensions,
            'audio_copy': self.audio_copy,
            'faststart': self.faststart,
            'avoid_negative_ts': self.avoid_negative_ts,
            
            'version': '2.0.0'  # Incrémenter la version
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Créer une instance depuis un dictionnaire."""
        settings = cls()
        
        # Charger les paramètres de base avec valeurs par défaut
        settings.use_size_threshold = data.get('use_size_threshold', True)
        settings.size_threshold = data.get('size_threshold', 500 * 1024 * 1024)
        settings.manual_mode = data.get('manual_mode', False)
        settings.crf = data.get('crf', 28)
        settings.preset = data.get('preset', "fast")
        settings.delete_if_smaller = data.get('delete_if_smaller', False)
        settings.delete_if_threshold = data.get('delete_if_threshold', False)
        settings.replace_original = data.get('replace_original', False)
        settings.ignore_converted = data.get('ignore_converted', True)
        settings.multiple_attempts = data.get('multiple_attempts', True)
        settings.converted_suffix = data.get('converted_suffix', '_cvt')
        settings.failed_suffix = data.get('failed_suffix', '_nocomp')
        settings.ignore_converted_files = data.get('ignore_converted_files', True)
        settings.mark_non_compressible = data.get('mark_non_compressible', False)
        settings.ignore_non_compressible = data.get('ignore_non_compressible', False)
        settings.video_extensions = data.get('video_extensions', 'mp4,avi,mkv,mov,flv,webm,wmv')
        settings.audio_copy = data.get('audio_copy', True)
        settings.faststart = data.get('faststart', True)
        settings.avoid_negative_ts = data.get('avoid_negative_ts', True)
    

        
        # Charger le nombre de threads avec valeur par défaut
        import os
        cpu_count = os.cpu_count() or 1
        settings.max_concurrent_conversions = data.get('max_concurrent_conversions', min(cpu_count, 4))
        
        # Charger les paramètres de tentatives
        attempts_data = data.get('attempts', [])
        settings.attempts = []
        
        for attempt_data in attempts_data:
            if isinstance(attempt_data, dict):
                settings.attempts.append(ConversionAttempt.from_dict(attempt_data))
        
        # Valider et corriger
        settings.validate_and_fix()
        
        return settings
    
    def get_size_threshold_mb(self) -> float:
        """Obtenir le seuil de taille en MB."""
        return self.size_threshold / (1024 * 1024)
    
    def set_size_threshold_mb(self, mb: float):
        """Définir le seuil de taille en MB."""
        self.size_threshold = int(max(1, mb) * 1024 * 1024)
    
    def is_valid(self) -> bool:
        """Vérifier si les paramètres sont valides."""
        try:
            # Vérifier les attributs requis
            required_attrs = [
                'use_size_threshold', 'size_threshold', 'manual_mode', 'crf', 'preset',
                'delete_if_smaller', 'delete_if_threshold', 'replace_original',
                'ignore_converted', 'multiple_attempts', 'attempts', 'max_concurrent_conversions'
            ]
            
            for attr in required_attrs:
                if not hasattr(self, attr):
                    return False
            
            # Vérifier les plages de valeurs
            if not (18 <= self.crf <= 35):
                return False
            
            if self.size_threshold <= 0:
                return False
            
            if not isinstance(self.attempts, list) or len(self.attempts) == 0:
                return False
            
            # Vérifier que tous les attempts sont valides
            for attempt in self.attempts:
                if not isinstance(attempt, ConversionAttempt):
                    return False
            
            return True
        except:
            return False
    
    def get_summary(self) -> str:
        """Obtenir un résumé lisible des paramètres."""
        threshold_mb = int(self.size_threshold / (1024 * 1024))
        mode = "Manuel" if self.manual_mode else "Automatique"
        
        summary = f"Mode: {mode}\n"
        summary += f"Seuil: {'Activé' if self.use_size_threshold else 'Désactivé'} ({threshold_mb} MB)\n"
        
        if self.manual_mode:
            summary += f"CRF: {self.crf}, Preset: {self.preset}\n"
        else:
            summary += f"Tentatives multiples: {'Oui' if self.multiple_attempts else 'Non'}\n"
            if self.multiple_attempts:
                for i, attempt in enumerate(self.attempts, 1):
                    summary += f"  Tentative {i}: CRF {attempt.crf}, {attempt.preset}\n"
        
        options = []
        if self.delete_if_smaller:
            options.append("Supprimer original si plus petit")
        if self.replace_original:
            options.append("Remplacer original")
        if self.ignore_converted:
            options.append("Ignorer déjà convertis")
        
        if options:
            summary += f"Options: {', '.join(options)}"
        
        return summary

class SettingsManager:
    """Gestionnaire de paramètres optimisé avec gestion d'erreur robuste."""
    
    CONFIG_DIR = Path.home() / '.videoflow'
    CONFIG_FILE = CONFIG_DIR / 'converter_settings.json'
    BACKUP_FILE = CONFIG_DIR / 'converter_settings.json.bak'
    
    # Cache pour éviter les lectures répétées
    _cached_settings = None
    _cache_timestamp = 0
    
    @staticmethod
    def ensure_config_dir():
        """S'assurer que le dossier de configuration existe."""
        try:
            SettingsManager.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Impossible de créer le dossier de configuration: {e}")
            return False
    
    @staticmethod
    def load_settings() -> ConversionSettings:
        """Charger les paramètres avec cache et gestion d'erreur."""
        # Vérifier le cache
        try:
            if (SettingsManager._cached_settings and 
                SettingsManager.CONFIG_FILE.exists() and
                SettingsManager.CONFIG_FILE.stat().st_mtime <= SettingsManager._cache_timestamp):
                return SettingsManager._cached_settings
        except:
            pass  # Ignorer les erreurs de cache
        
        # Commencer avec les paramètres par défaut
        settings = ConversionSettings()
        
        if not SettingsManager.CONFIG_FILE.exists():
            logger.debug("Aucun fichier de configuration trouvé, utilisation des paramètres par défaut")
            SettingsManager._cached_settings = settings
            SettingsManager._cache_timestamp = 0
            return settings
        
        try:
            # Charger le fichier principal
            with open(SettingsManager.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Valider la structure JSON
            if not isinstance(data, dict):
                raise ValueError("Le fichier de configuration n'est pas un objet JSON valide")
            
            settings = ConversionSettings.from_dict(data)
            
            # Valider les paramètres chargés
            if not settings.is_valid():
                logger.warning("Paramètres chargés invalides, utilisation des paramètres par défaut")
                settings = ConversionSettings()
            else:
                logger.debug("Paramètres chargés avec succès")
            
            # Mettre à jour le cache
            SettingsManager._cached_settings = settings
            SettingsManager._cache_timestamp = SettingsManager.CONFIG_FILE.stat().st_mtime
            
            return settings
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON invalide dans le fichier de configuration: {e}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des paramètres: {e}")
        
        # Essayer le fichier de sauvegarde
        if SettingsManager.BACKUP_FILE.exists():
            try:
                logger.info("Tentative de chargement du fichier de sauvegarde")
                with open(SettingsManager.BACKUP_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                settings = ConversionSettings.from_dict(data)
                if settings.is_valid():
                    logger.info("Paramètres de sauvegarde chargés avec succès")
                    SettingsManager._cached_settings = settings
                    return settings
                    
            except Exception as e:
                logger.error(f"Erreur lors du chargement de la sauvegarde: {e}")
        
        logger.warning("Utilisation des paramètres par défaut en raison d'erreurs de configuration")
        SettingsManager._cached_settings = settings
        return settings
    
    @staticmethod
    def save_settings(settings: ConversionSettings) -> bool:
        """Sauvegarder les paramètres avec vérification d'intégrité."""
        if not SettingsManager.ensure_config_dir():
            return False
        
        try:
            # Valider avant sauvegarde
            if not settings.is_valid():
                logger.error("Impossible de sauvegarder des paramètres invalides")
                return False
            
            # Créer une sauvegarde du fichier existant
            if SettingsManager.CONFIG_FILE.exists():
                try:
                    import shutil
                    shutil.copy2(SettingsManager.CONFIG_FILE, SettingsManager.BACKUP_FILE)
                except Exception as e:
                    logger.warning(f"Impossible de créer une sauvegarde: {e}")
            
            # Convertir en dictionnaire
            data = settings.to_dict()
            
            # Écrire dans un fichier temporaire d'abord
            temp_file = SettingsManager.CONFIG_FILE.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Vérifier le fichier temporaire
            with open(temp_file, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
                test_settings = ConversionSettings.from_dict(test_data)
                if not test_settings.is_valid():
                    raise ValueError("Échec de la validation des paramètres sauvegardés")
            
            # Déplacer le fichier temporaire vers l'emplacement final
            temp_file.replace(SettingsManager.CONFIG_FILE)
            
            # Mettre à jour le cache
            SettingsManager._cached_settings = settings
            SettingsManager._cache_timestamp = SettingsManager.CONFIG_FILE.stat().st_mtime
            
            logger.debug("Paramètres sauvegardés avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des paramètres: {e}")
            # Nettoyer le fichier temporaire
            temp_file = SettingsManager.CONFIG_FILE.with_suffix('.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            return False
    
    @staticmethod
    def reset_settings() -> ConversionSettings:
        """Réinitialiser les paramètres aux valeurs par défaut."""
        settings = ConversionSettings()
        
        # Sauvegarder les nouveaux paramètres
        if SettingsManager.save_settings(settings):
            logger.info("Paramètres réinitialisés aux valeurs par défaut")
        else:
            logger.warning("Échec de la sauvegarde après réinitialisation")
        
        return settings
    
    @staticmethod
    def export_settings(file_path: Path, settings: ConversionSettings) -> bool:
        """Exporter les paramètres vers un fichier."""
        try:
            data = settings.to_dict()
            data['exported_at'] = str(datetime.now().isoformat())
            data['export_version'] = '1.0.1'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Paramètres exportés vers {file_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'exportation des paramètres: {e}")
            return False
    
    @staticmethod
    def import_settings(file_path: Path) -> ConversionSettings:
        """Importer les paramètres depuis un fichier."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Supprimer les métadonnées d'exportation
            data.pop('exported_at', None)
            data.pop('export_version', None)
            
            settings = ConversionSettings.from_dict(data)
            if settings.is_valid():
                if SettingsManager.save_settings(settings):
                    logger.info(f"Paramètres importés depuis {file_path}")
                    return settings
                else:
                    raise ValueError("Échec de la sauvegarde des paramètres importés")
            else:
                raise ValueError("Paramètres importés invalides")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'importation des paramètres: {e}")
            return SettingsManager.load_settings()  # Retourner les paramètres actuels en cas d'erreur
    
    @staticmethod
    def clear_cache():
        """Vider le cache des paramètres."""
        SettingsManager._cached_settings = None
        SettingsManager._cache_timestamp = 0