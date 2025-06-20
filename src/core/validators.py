
"""
Validateurs pour les entrées utilisateur
"""

import os
import re
import mimetypes
from pathlib import Path
from typing import List, Optional, Union, Tuple, Dict, Any
from urllib.parse import urlparse

class ValidationError(Exception):
    """Exception de validation"""
    pass

class FileValidator:
    """Validateur de fichiers"""
    
    SUPPORTED_VIDEO_FORMATS = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', 
        '.m4v', '.3gp', '.ogv', '.ts', '.m2ts', '.mts'
    }
    
    SUPPORTED_AUDIO_FORMATS = {
        '.mp3', '.wav', '.aac', '.flac', '.ogg', '.wma', '.m4a'
    }
    
    @staticmethod
    def validate_video_file(file_path: Union[str, Path]) -> Tuple[bool, str]:
        """Valide un fichier vidéo"""
        try:
            file_path = Path(file_path)
            
            # Vérifier l'existence
            if not file_path.exists():
                return False, f"Fichier inexistant: {file_path}"
            
            # Vérifier que c'est un fichier
            if not file_path.is_file():
                return False, f"Pas un fichier: {file_path}"
            
            # Vérifier l'extension
            if file_path.suffix.lower() not in FileValidator.SUPPORTED_VIDEO_FORMATS:
                return False, f"Format non supporté: {file_path.suffix}"
            
            # Vérifier la taille (pas vide, pas trop gros)
            size = file_path.stat().st_size
            if size == 0:
                return False, "Fichier vide"
            
            if size > 50 * 1024 * 1024 * 1024:  # 50GB max
                return False, f"Fichier trop volumineux: {size / (1024**3):.1f}GB"
            
            # Vérifier le type MIME si possible
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and not mime_type.startswith('video/'):
                return False, f"Type MIME incorrect: {mime_type}"
            
            return True, "Fichier valide"
            
        except Exception as e:
            return False, f"Erreur validation: {e}"
    
    @staticmethod
    def validate_directory(dir_path: Union[str, Path], 
                          must_exist: bool = True,
                          check_writable: bool = False) -> Tuple[bool, str]:
        """Valide un répertoire"""
        try:
            dir_path = Path(dir_path)
            
            if must_exist and not dir_path.exists():
                return False, f"Répertoire inexistant: {dir_path}"
            
            if dir_path.exists() and not dir_path.is_dir():
                return False, f"Pas un répertoire: {dir_path}"
            
            if check_writable and dir_path.exists():
                if not os.access(dir_path, os.W_OK):
                    return False, f"Répertoire non accessible en écriture: {dir_path}"
            
            return True, "Répertoire valide"
            
        except Exception as e:
            return False, f"Erreur validation répertoire: {e}"
    
    @staticmethod
    def get_available_space(path: Union[str, Path]) -> int:
        """Retourne l'espace disponible en bytes"""
        try:
            statvfs = os.statvfs(path)
            return statvfs.f_frsize * statvfs.f_avail
        except AttributeError:
            # Windows
            import shutil
            return shutil.disk_usage(path).free
        except Exception:
            return 0

class ParameterValidator:
    """Validateur de paramètres"""
    
    @staticmethod
    def validate_numeric_range(value: Union[int, float], 
                             min_val: Optional[Union[int, float]] = None,
                             max_val: Optional[Union[int, float]] = None,
                             name: str = "valeur") -> Tuple[bool, str]:
        """Valide une valeur numérique dans une plage"""
        try:
            if not isinstance(value, (int, float)):
                return False, f"{name} doit être numérique"
            
            if min_val is not None and value < min_val:
                return False, f"{name} doit être >= {min_val}"
            
            if max_val is not None and value > max_val:
                return False, f"{name} doit être <= {max_val}"
            
            return True, f"{name} valide"
            
        except Exception as e:
            return False, f"Erreur validation {name}: {e}"
    
    @staticmethod
    def validate_string_pattern(value: str, pattern: str, 
                              name: str = "chaîne") -> Tuple[bool, str]:
        """Valide une chaîne contre un pattern regex"""
        try:
            if not isinstance(value, str):
                return False, f"{name} doit être une chaîne"
            
            if not re.match(pattern, value):
                return False, f"{name} ne correspond pas au pattern attendu"
            
            return True, f"{name} valide"
            
        except Exception as e:
            return False, f"Erreur validation {name}: {e}"
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """Valide une URL"""
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False, "URL invalide"
            
            if result.scheme not in ['http', 'https', 'ftp', 'rtsp', 'rtmp']:
                return False, f"Schéma URL non supporté: {result.scheme}"
            
            return True, "URL valide"
            
        except Exception as e:
            return False, f"Erreur validation URL: {e}"

class ConversionValidator:
    """Validateur spécifique aux conversions"""
    
    VALID_CODECS = {
        'video': ['libx264', 'libx265', 'libvpx-vp9', 'mpeg4'],
        'audio': ['aac', 'mp3', 'libvorbis', 'flac']
    }
    
    @staticmethod
    def validate_conversion_params(params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Valide les paramètres de conversion"""
        errors = []
        
        # Valider CRF
        if 'crf' in params:
            valid, msg = ParameterValidator.validate_numeric_range(
                params['crf'], 0, 51, "CRF"
            )
            if not valid:
                errors.append(msg)
        
        # Valider codec vidéo
        if 'video_codec' in params:
            if params['video_codec'] not in ConversionValidator.VALID_CODECS['video']:
                errors.append(f"Codec vidéo non supporté: {params['video_codec']}")
        
        # Valider codec audio
        if 'audio_codec' in params:
            if params['audio_codec'] not in ConversionValidator.VALID_CODECS['audio']:
                errors.append(f"Codec audio non supporté: {params['audio_codec']}")
        
        # Valider résolution
        if 'width' in params and 'height' in params:
            for dim, name in [(params['width'], 'largeur'), (params['height'], 'hauteur')]:
                valid, msg = ParameterValidator.validate_numeric_range(
                    dim, 1, 7680, name
                )
                if not valid:
                    errors.append(msg)
        
        return len(errors) == 0, errors

def validate_batch_operation(files: List[str], 
                           operation: str,
                           max_files: int = 1000) -> Tuple[bool, List[str]]:
    """Valide une opération par lot"""
    errors = []
    
    # Vérifier le nombre de fichiers
    if len(files) == 0:
        errors.append("Aucun fichier sélectionné")
    elif len(files) > max_files:
        errors.append(f"Trop de fichiers ({len(files)} > {max_files})")
    
    # Valider chaque fichier
    valid_files = 0
    for file_path in files:
        valid, msg = FileValidator.validate_video_file(file_path)
        if not valid:
            errors.append(f"{os.path.basename(file_path)}: {msg}")
        else:
            valid_files += 1
    
    if valid_files == 0 and len(files) > 0:
        errors.append("Aucun fichier valide trouvé")
    
    return len(errors) == 0, errors
