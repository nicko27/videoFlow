"""Handling des settings optimisée pour VideoConverter plugin."""

from dataclasses import dataclass
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
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
            logger.warning(f"Invalid CRF type: {type(crf)}, using default value")
            return 28
        return max(18, min(35, crf))  # Plage réduite pour de meilleurs results
    
    @staticmethod
    def validate_preset(preset: str) -> str:
        """Valider la valeur preset."""
        valid_presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", 
                        "medium", "slow", "slower", "veryslow"]
        if preset not in valid_presets:
            logger.warning(f"Invalid preset: {preset}, using 'fast'")
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
    """Settings de conversion optimisés with valeurs par défaut améliorées."""
    
    def __init__(self):
        """Initialiser with des settings optimisés."""
        # Options de size - seuil plus raisonnable
        self.use_size_threshold = True
        self.size_threshold = 500 * 1024 * 1024  # 500 MB par défaut (plus raisonnable)

        # Compression itérative avec taille cible
        self.use_target_size = False  # Mode compression progressive activé
        self.target_size = 300 * 1024 * 1024  # Taille cible: 300 MB par défaut
        self.max_compression_attempts = 5  # Nombre max de tentatives itératives
        self.initial_crf = 28  # CRF de départ pour compression itérative
        self.crf_step = 2  # Augmentation CRF à chaque itération
        self.max_crf = 40  # CRF maximum (au-delà, qualité trop dégradée)

        # Mode manuel with settings équilibrés
        self.manual_mode = False
        self.crf = 28  # Équilibre qualité/size
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

        # Handling des suffixes
        self.converted_suffix = '_cvt'
        self.failed_suffix = '_nocomp'
        
        # Options de gestion des files traités
        self.ignore_converted_files = True
        self.mark_non_compressible = False
        self.ignore_non_compressible = False
        
        # Extensions supportées
        self.video_extensions = 'mp4,avi,mkv,mov,flv,webm,wmv'
        
        # Options audio et compatibilité
        self.audio_copy = True
        self.faststart = True
        self.avoid_negative_ts = True

        # Simple mode settings
        self.simple_mode = False  # Mode simple désactivé par défaut
        self.simple_strategy = 'balanced'  # Stratégie par défaut: balanced
        self.balanced_auto_crf = False  # CRF auto calculé selon résolution
        self.balanced_quality_factor = 1.0  # Facteur qualité (0.5-2.0, 1.0=neutre)

        # FFmpeg configuration
        self.ffmpeg_path = self._detect_ffmpeg()
        self.ffprobe_path = self._detect_ffprobe()

    @staticmethod
    def _detect_ffmpeg() -> str:
        """
        Detect FFmpeg executable path.

        Returns:
            Path to ffmpeg or 'ffmpeg' if using system PATH
        """
        import shutil

        # Try to find ffmpeg in PATH
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            logger.debug(f"FFmpeg found at: {ffmpeg_path}")
            return ffmpeg_path

        # Fallback to system PATH (let subprocess handle it)
        logger.warning("FFmpeg not found in PATH, will try system PATH")
        return 'ffmpeg'

    @staticmethod
    def _detect_ffprobe() -> str:
        """
        Detect FFprobe executable path.

        Returns:
            Path to ffprobe or 'ffprobe' if using system PATH
        """
        import shutil

        # Try to find ffprobe in PATH
        ffprobe_path = shutil.which('ffprobe')
        if ffprobe_path:
            logger.debug(f"FFprobe found at: {ffprobe_path}")
            return ffprobe_path

        # Fallback to system PATH
        logger.warning("FFprobe not found in PATH, will try system PATH")
        return 'ffprobe'

    def validate_and_fix(self):
        """Valider et corriger tous les settings."""
        # Valider le seuil de size
        if not isinstance(self.size_threshold, (int, float)) or self.size_threshold <= 0:
            logger.warning("Invalid size threshold, using default 500MB")
            self.size_threshold = 500 * 1024 * 1024

        # Limiter le seuil maximum pour éviter les valeurs aberrantes
        max_threshold = 10 * 1024 * 1024 * 1024  # 10GB max
        if self.size_threshold > max_threshold:
            logger.warning(f"Size threshold too high, limiting to {max_threshold // (1024*1024*1024)}GB")
            self.size_threshold = max_threshold

        # Valider la taille cible
        if not isinstance(self.target_size, (int, float)) or self.target_size <= 0:
            logger.warning("Invalid target size, using default 300MB")
            self.target_size = 300 * 1024 * 1024

        if self.target_size > max_threshold:
            logger.warning(f"Target size too high, limiting to {max_threshold // (1024*1024*1024)}GB")
            self.target_size = max_threshold

        # Valider les paramètres de compression itérative
        if not isinstance(self.max_compression_attempts, int) or self.max_compression_attempts < 1:
            logger.warning("Invalid max attempts, using default 5")
            self.max_compression_attempts = 5

        self.max_compression_attempts = max(1, min(10, self.max_compression_attempts))

        if not isinstance(self.initial_crf, int) or not (18 <= self.initial_crf <= 35):
            logger.warning("Invalid initial CRF, using default 28")
            self.initial_crf = 28

        if not isinstance(self.crf_step, int) or self.crf_step < 1:
            logger.warning("Invalid CRF step, using default 2")
            self.crf_step = 2

        self.crf_step = max(1, min(5, self.crf_step))

        if not isinstance(self.max_crf, int) or not (18 <= self.max_crf <= 51):
            logger.warning("Invalid max CRF, using default 40")
            self.max_crf = 40
        
        # Valider CRF et preset
        self.crf = ConversionAttempt.validate_crf(self.crf)
        self.preset = ConversionAttempt.validate_preset(self.preset)
        
        # Valider les settings booléens
        bool_settings = [
            'use_size_threshold', 'manual_mode', 'delete_if_smaller',
            'delete_if_threshold', 'replace_original', 'ignore_converted',
            'multiple_attempts'
        ]
        
        for setting in bool_settings:
            value = getattr(self, setting, False)
            if not isinstance(value, bool):
                logger.warning(f"Invalid boolean parameter {setting}, using False")
                setattr(self, setting, False)
        
        # Valider le number de conversions simultanées
        if not isinstance(self.max_concurrent_conversions, int) or self.max_concurrent_conversions < 1:
            import os
            cpu_count = os.cpu_count() or 1
            self.max_concurrent_conversions = min(cpu_count, 4)
            logger.warning(f"Invalid thread count, using {self.max_concurrent_conversions}")
        
        # Limiter entre 1 et 8 threads
        self.max_concurrent_conversions = max(1, min(8, self.max_concurrent_conversions))
        
        # Valider et corriger les tentatives
        if not isinstance(self.attempts, list) or len(self.attempts) == 0:
            logger.warning("Invalid attempts configuration, using default values")
            self.attempts = [
                ConversionAttempt(28, "fast"),
                ConversionAttempt(30, "medium"),
                ConversionAttempt(32, "slow")
            ]
        
        # S'asoner d'avoir exactement 3 tentatives
        while len(self.attempts) < 3:
            self.attempts.append(ConversionAttempt(32, "slow"))

        # Cross-validation: Check for incompatible setting combinations
        self._validate_cross_settings()
        
        if len(self.attempts) > 3:
            self.attempts = self.attempts[:3]
            logger.warning("Too many attempts configured, using first 3")
        
        # Valider chaque tentative
        for i, attempt in enumerate(self.attempts):
            if not isinstance(attempt, ConversionAttempt):
                logger.warning(f"Attempt {i+1} invalid, replacing with default")
                self.attempts[i] = ConversionAttempt(28 + i*2, ["fast", "medium", "slow"][i])

    def _validate_cross_settings(self):
        """
        Validate cross-dependencies between settings.

        Checks for incompatible or illogical setting combinations and fixes them.
        """
        # 1. Check iterative compression settings
        if self.use_target_size:
            # Ensure initial_crf < max_crf for iterative compression
            if self.initial_crf >= self.max_crf:
                logger.warning(
                    f"Initial CRF ({self.initial_crf}) >= Max CRF ({self.max_crf}). "
                    "Adjusting max_crf to initial_crf + 10"
                )
                self.max_crf = min(51, self.initial_crf + 10)

            # Ensure crf_step makes sense
            range_available = self.max_crf - self.initial_crf
            if range_available < self.crf_step:
                logger.warning(
                    f"CRF step ({self.crf_step}) too large for CRF range ({range_available}). "
                    "Reducing to 1"
                )
                self.crf_step = 1

        # 2. Check threshold vs target size
        if self.use_target_size and self.use_size_threshold:
            if self.target_size >= self.size_threshold:
                logger.warning(
                    f"Target size ({self.target_size/1024/1024:.0f}MB) >= "
                    f"Size threshold ({self.size_threshold/1024/1024:.0f}MB). "
                    "This combination doesn't make sense. Disabling size threshold."
                )
                self.use_size_threshold = False

        # 3. Check delete options sanity
        if self.delete_if_smaller and self.replace_original:
            logger.warning(
                "Both 'delete_if_smaller' and 'replace_original' are enabled. "
                "'replace_original' takes precedence."
            )
            self.delete_if_smaller = False

        # 4. Warn about extreme CRF/preset combinations
        if self.manual_mode:
            slow_presets = ['slow', 'slower', 'veryslow']
            if self.crf >= 33 and self.preset in slow_presets:
                logger.warning(
                    f"High CRF ({self.crf}) with slow preset ('{self.preset}'): "
                    "This will be very slow and produce poor quality. "
                    "Consider using CRF <= 32 or a faster preset."
                )

        # 5. Validate balanced mode quality factor
        if self.balanced_auto_crf:
            if not isinstance(self.balanced_quality_factor, (int, float)):
                logger.warning("Invalid quality factor, using default 1.0")
                self.balanced_quality_factor = 1.0
            else:
                # Clamp to reasonable range
                if self.balanced_quality_factor < 0.5 or self.balanced_quality_factor > 2.0:
                    logger.warning(
                        f"Quality factor ({self.balanced_quality_factor}) out of range [0.5, 2.0]. "
                        "Clamping to valid range."
                    )
                    self.balanced_quality_factor = max(0.5, min(2.0, self.balanced_quality_factor))

        # 6. Check multiple attempts with manual mode
        if self.manual_mode and self.multiple_attempts:
            logger.info(
                "Manual mode with multiple attempts: all attempts will use the same settings "
                "(CRF={}, preset='{}')".format(self.crf, self.preset)
            )

    def to_dict(self) -> dict:
        """Convertir les settings en dictionnaire."""
        return {
            'use_size_threshold': self.use_size_threshold,
            'size_threshold': self.size_threshold,
            'use_target_size': self.use_target_size,
            'target_size': self.target_size,
            'max_compression_attempts': self.max_compression_attempts,
            'initial_crf': self.initial_crf,
            'crf_step': self.crf_step,
            'max_crf': self.max_crf,
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
            'simple_mode': self.simple_mode,
            'simple_strategy': self.simple_strategy,
            'balanced_auto_crf': self.balanced_auto_crf,
            'balanced_quality_factor': self.balanced_quality_factor,
            'ffmpeg_path': self.ffmpeg_path,
            'ffprobe_path': self.ffprobe_path,

            'version': '2.3.0'  # Incremented version for configurable FFmpeg paths
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Créer une instance depuis un dictionnaire."""
        settings = cls()
        
        # Load les settings de base with valeurs par défaut
        settings.use_size_threshold = data.get('use_size_threshold', True)
        settings.size_threshold = data.get('size_threshold', 500 * 1024 * 1024)
        settings.use_target_size = data.get('use_target_size', False)
        settings.target_size = data.get('target_size', 300 * 1024 * 1024)
        settings.max_compression_attempts = data.get('max_compression_attempts', 5)
        settings.initial_crf = data.get('initial_crf', 28)
        settings.crf_step = data.get('crf_step', 2)
        settings.max_crf = data.get('max_crf', 40)
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
        settings.simple_mode = data.get('simple_mode', False)
        settings.simple_strategy = data.get('simple_strategy', 'balanced')
        settings.balanced_auto_crf = data.get('balanced_auto_crf', False)
        settings.balanced_quality_factor = data.get('balanced_quality_factor', 1.0)

        # Load FFmpeg paths (with auto-detection fallback)
        settings.ffmpeg_path = data.get('ffmpeg_path', cls._detect_ffmpeg())
        settings.ffprobe_path = data.get('ffprobe_path', cls._detect_ffprobe())

        # Load le number de threads with valeur par défaut
        import os
        cpu_count = os.cpu_count() or 1
        settings.max_concurrent_conversions = data.get('max_concurrent_conversions', min(cpu_count, 4))
        
        # Load les settings de tentatives
        attempts_data = data.get('attempts', [])
        settings.attempts = []
        
        for attempt_data in attempts_data:
            if isinstance(attempt_data, dict):
                settings.attempts.append(ConversionAttempt.from_dict(attempt_data))
        
        # Valider et corriger
        settings.validate_and_fix()
        
        return settings
    
    def get_size_threshold_mb(self) -> float:
        """Obtenir le seuil de size en MB."""
        return self.size_threshold / (1024 * 1024)

    def set_size_threshold_mb(self, mb: float):
        """Définir le seuil de size en MB."""
        self.size_threshold = int(max(1, mb) * 1024 * 1024)

    def get_target_size_mb(self) -> float:
        """Obtenir la taille cible en MB."""
        return self.target_size / (1024 * 1024)

    def set_target_size_mb(self, mb: float):
        """Définir la taille cible en MB."""
        self.target_size = int(max(1, mb) * 1024 * 1024)
    
    def is_valid(self) -> bool:
        """Checksr si les settings sont valides."""
        try:
            # Checksr les attributs requis
            required_attrs = [
                'use_size_threshold', 'size_threshold', 'manual_mode', 'crf', 'preset',
                'delete_if_smaller', 'delete_if_threshold', 'replace_original',
                'ignore_converted', 'multiple_attempts', 'attempts', 'max_concurrent_conversions'
            ]
            
            for attr in required_attrs:
                if not hasattr(self, attr):
                    return False
            
            # Checksr les plages de valeurs
            if not (18 <= self.crf <= 35):
                return False
            
            if self.size_threshold <= 0:
                return False
            
            if not isinstance(self.attempts, list) or len(self.attempts) == 0:
                return False
            
            # Checksr que tous les attempts sont valides
            for attempt in self.attempts:
                if not isinstance(attempt, ConversionAttempt):
                    return False
            
            return True
        except:
            return False
    
    def get_summary(self) -> str:
        """Obtenir un résumé lisible des settings."""
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
            options.append("Remove original si plus petit")
        if self.replace_original:
            options.append("Remplacer original")
        if self.ignore_converted:
            options.append("Ignorer déjà convertis")
        
        if options:
            summary += f"Options: {', '.join(options)}"
        
        return summary

class SettingsManager:
    """Handlingnaire de settings optimisé with gestion d'error robuste."""
    
    CONFIG_DIR = Path.home() / '.videoflow'
    CONFIG_FILE = CONFIG_DIR / 'converter_settings.json'
    BACKUP_FILE = CONFIG_DIR / 'converter_settings.json.bak'
    
    # Cache pour éviter les lectures répétées
    _cached_settings = None
    _cache_timestamp = 0
    
    @staticmethod
    def ensure_config_dir():
        """S'asoner que le folder de configuration existe."""
        try:
            SettingsManager.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Cannot create configuration folder: {e}")
            return False
    
    @staticmethod
    def load_settings() -> ConversionSettings:
        """Load les settings with cache et gestion d'error."""
        # Checksr le cache
        try:
            if (SettingsManager._cached_settings and 
                SettingsManager.CONFIG_FILE.exists() and
                SettingsManager.CONFIG_FILE.stat().st_mtime <= SettingsManager._cache_timestamp):
                return SettingsManager._cached_settings
        except:
            pass  # Ignorer les erreurs de cache
        
        # Commencer with les settings par défaut
        settings = ConversionSettings()
        
        if not SettingsManager.CONFIG_FILE.exists():
            logger.debug("No configuration file found, using default settings")
            SettingsManager._cached_settings = settings
            SettingsManager._cache_timestamp = 0
            return settings
        
        try:
            # Load le file principal
            with open(SettingsManager.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Valider la structure JSON
            if not isinstance(data, dict):
                raise ValueError("Configuration file is not a valid JSON object")
            
            settings = ConversionSettings.from_dict(data)
            
            # Valider les settings chargés
            if not settings.is_valid():
                logger.warning("Loaded settings invalid, using default settings")
                settings = ConversionSettings()
            else:
                logger.debug("Settings loaded successfully")
            
            # Mettre à jour le cache
            SettingsManager._cached_settings = settings
            SettingsManager._cache_timestamp = SettingsManager.CONFIG_FILE.stat().st_mtime
            
            return settings
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
        
        # Essayer le file de sauvegarde
        if SettingsManager.BACKUP_FILE.exists():
            try:
                logger.info("Attempting to load backup file")
                with open(SettingsManager.BACKUP_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                settings = ConversionSettings.from_dict(data)
                if settings.is_valid():
                    logger.info("Backup settings loaded successfully")
                    SettingsManager._cached_settings = settings
                    return settings

            except Exception as e:
                logger.error(f"Error loading backup: {e}")
        
        logger.warning("Using default settings due to configuration errors")
        SettingsManager._cached_settings = settings
        return settings
    
    @staticmethod
    def save_settings(settings: ConversionSettings) -> bool:
        """Save les settings with vérification d'intégrité."""
        if not SettingsManager.ensure_config_dir():
            return False
        
        try:
            # Valider avant sauvegarde
            if not settings.is_valid():
                logger.error("Cannot save invalid settings")
                return False
            
            # Créer une sauvegarde du file existant
            if SettingsManager.CONFIG_FILE.exists():
                try:
                    import shutil
                    shutil.copy2(SettingsManager.CONFIG_FILE, SettingsManager.BACKUP_FILE)
                except Exception as e:
                    logger.warning(f"Cannot create backup: {e}")
            
            # Convertir en dictionnaire
            data = settings.to_dict()
            
            # Écrire in un file temporaire d'abord
            temp_file = SettingsManager.CONFIG_FILE.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Checksr le file temporaire
            with open(temp_file, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
                test_settings = ConversionSettings.from_dict(test_data)
                if not test_settings.is_valid():
                    raise ValueError("Validation of saved settings failed")
            
            # Déplacer le file temporaire vers l'emplacement final
            temp_file.replace(SettingsManager.CONFIG_FILE)
            
            # Mettre à jour le cache
            SettingsManager._cached_settings = settings
            SettingsManager._cache_timestamp = SettingsManager.CONFIG_FILE.stat().st_mtime

            logger.debug("Settings saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            # Nettoyer le file temporaire
            temp_file = SettingsManager.CONFIG_FILE.with_suffix('.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            return False
    
    @staticmethod
    def reset_settings() -> ConversionSettings:
        """Réinitialiser les settings aux valeurs par défaut."""
        settings = ConversionSettings()
        
        # Save les nouveaux settings
        if SettingsManager.save_settings(settings):
            logger.info("Settings reset to default values")
        else:
            logger.warning("Failed to save after reset")
        
        return settings
    
    @staticmethod
    def export_settings(file_path: Path, settings: ConversionSettings) -> bool:
        """Exporter les settings vers un file."""
        try:
            data = settings.to_dict()
            data['exported_at'] = str(datetime.now().isoformat())
            data['export_version'] = '1.0.1'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Settings exported to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error during settings export: {e}")
            return False
    
    @staticmethod
    def import_settings(file_path: Path) -> ConversionSettings:
        """Importer les settings depuis un file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Remove les métadonnées d'exportation
            data.pop('exported_at', None)
            data.pop('export_version', None)
            
            settings = ConversionSettings.from_dict(data)
            if settings.is_valid():
                if SettingsManager.save_settings(settings):
                    logger.info(f"Settings imported from {file_path}")
                    return settings
                else:
                    raise ValueError("Failed to save imported settings")
            else:
                raise ValueError("Imported settings invalid")
                
        except Exception as e:
            logger.error(f"Error during settings import: {e}")
            return SettingsManager.load_settings()  # Return current settings on error
    
    @staticmethod
    def clear_cache():
        """Vider le cache des settings."""
        SettingsManager._cached_settings = None
        SettingsManager._cache_timestamp = 0
