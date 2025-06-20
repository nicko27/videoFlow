
"""
Utilitaires pour la compatibilité cross-platform
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

class PlatformInfo:
    """Informations sur la plateforme"""
    
    @staticmethod
    def is_windows() -> bool:
        return os.name == 'nt'
    
    @staticmethod
    def is_macos() -> bool:
        return sys.platform == 'darwin'
    
    @staticmethod
    def is_linux() -> bool:
        return sys.platform.startswith('linux')
    
    @staticmethod
    def get_platform_name() -> str:
        return platform.system().lower()
    
    @staticmethod
    def get_architecture() -> str:
        return platform.machine().lower()

class PathUtils:
    """Utilitaires de chemins cross-platform"""
    
    @staticmethod
    def normalize_path(path: Union[str, Path]) -> Path:
        """Normalise un chemin pour la plateforme actuelle"""
        return Path(path).resolve()
    
    @staticmethod
    def get_config_dir() -> Path:
        """Retourne le répertoire de configuration"""
        if PlatformInfo.is_windows():
            return Path(os.environ.get('APPDATA', '')) / 'VideoFlow'
        elif PlatformInfo.is_macos():
            return Path.home() / 'Library' / 'Application Support' / 'VideoFlow'
        else:  # Linux
            return Path.home() / '.config' / 'videoflow'
    
    @staticmethod
    def get_cache_dir() -> Path:
        """Retourne le répertoire de cache"""
        if PlatformInfo.is_windows():
            return Path(os.environ.get('LOCALAPPDATA', '')) / 'VideoFlow' / 'Cache'
        elif PlatformInfo.is_macos():
            return Path.home() / 'Library' / 'Caches' / 'VideoFlow'
        else:  # Linux
            return Path.home() / '.cache' / 'videoflow'
    
    @staticmethod
    def get_temp_dir() -> Path:
        """Retourne le répertoire temporaire"""
        import tempfile
        return Path(tempfile.gettempdir()) / 'videoflow'
    
    @staticmethod
    def ensure_directory(path: Path) -> bool:
        """Crée un répertoire s'il n'existe pas"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Impossible de créer le répertoire {path}: {e}")
            return False

class FFmpegUtils:
    """Utilitaires FFmpeg cross-platform"""
    
    @staticmethod
    def find_ffmpeg() -> Optional[Path]:
        """Trouve l'exécutable FFmpeg"""
        executable_name = 'ffmpeg.exe' if PlatformInfo.is_windows() else 'ffmpeg'
        
        # Chercher dans PATH
        for path_dir in os.environ.get('PATH', '').split(os.pathsep):
            ffmpeg_path = Path(path_dir) / executable_name
            if ffmpeg_path.exists() and ffmpeg_path.is_file():
                return ffmpeg_path
        
        # Chemins spécifiques par plateforme
        if PlatformInfo.is_windows():
            search_paths = [
                Path('C:/Program Files/ffmpeg/bin'),
                Path('C:/ffmpeg/bin'),
                Path.home() / 'ffmpeg' / 'bin'
            ]
        elif PlatformInfo.is_macos():
            search_paths = [
                Path('/usr/local/bin'),
                Path('/opt/homebrew/bin'),
                Path('/usr/bin')
            ]
        else:  # Linux
            search_paths = [
                Path('/usr/bin'),
                Path('/usr/local/bin'),
                Path('/snap/bin')
            ]
        
        for search_path in search_paths:
            ffmpeg_path = search_path / executable_name
            if ffmpeg_path.exists():
                return ffmpeg_path
        
        return None
    
    @staticmethod
    def get_ffmpeg_version() -> Optional[str]:
        """Retourne la version de FFmpeg"""
        ffmpeg_path = FFmpegUtils.find_ffmpeg()
        if not ffmpeg_path:
            return None
        
        try:
            result = subprocess.run(
                [str(ffmpeg_path), '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Extraire la version de la première ligne
                first_line = result.stdout.split('
')[0]
                import re
                version_match = re.search(r'ffmpeg version (\S+)', first_line)
                if version_match:
                    return version_match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur vérification version FFmpeg: {e}")
            return None

class SystemUtils:
    """Utilitaires système cross-platform"""
    
    @staticmethod
    def get_cpu_count() -> int:
        """Retourne le nombre de CPU"""
        return os.cpu_count() or 1
    
    @staticmethod
    def get_memory_info() -> Dict[str, int]:
        """Retourne les informations mémoire"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percentage': memory.percent
            }
        except ImportError:
            logger.warning("psutil non disponible, informations mémoire limitées")
            return {'total': 0, 'available': 0, 'used': 0, 'percentage': 0}
    
    @staticmethod
    def open_file_manager(path: Path):
        """Ouvre le gestionnaire de fichiers"""
        try:
            if PlatformInfo.is_windows():
                os.startfile(str(path))
            elif PlatformInfo.is_macos():
                subprocess.run(['open', str(path)])
            else:  # Linux
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            logger.error(f"Impossible d'ouvrir le gestionnaire de fichiers: {e}")
    
    @staticmethod
    def get_file_associations() -> Dict[str, str]:
        """Retourne les associations de fichiers vidéo"""
        associations = {}
        
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']
        
        for ext in video_extensions:
            try:
                if PlatformInfo.is_windows():
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ext) as key:
                        file_type = winreg.QueryValue(key, None)
                        associations[ext] = file_type
                elif PlatformInfo.is_macos():
                    # Utiliser UTI sur macOS
                    result = subprocess.run(
                        ['mdls', '-name', 'kMDItemContentType', '/System/Library/CoreServices/Applications/QuickTime Player.app'],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        associations[ext] = 'QuickTime Player'
                else:  # Linux
                    result = subprocess.run(
                        ['xdg-mime', 'query', 'default', f'video/{ext[1:]}'],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        associations[ext] = result.stdout.strip()
            except Exception as e:
                logger.debug(f"Impossible de déterminer l'association pour {ext}: {e}")
        
        return associations

class NotificationUtils:
    """Utilitaires de notification cross-platform"""
    
    @staticmethod
    def show_notification(title: str, message: str, icon: Optional[str] = None):
        """Affiche une notification système"""
        try:
            if PlatformInfo.is_windows():
                # Windows 10+ toast notification
                try:
                    from plyer import notification
                    notification.notify(
                        title=title,
                        message=message,
                        timeout=5
                    )
                except ImportError:
                    # Fallback avec messagebox
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
            
            elif PlatformInfo.is_macos():
                # macOS notification
                subprocess.run([
                    'osascript', '-e',
                    f'display notification "{message}" with title "{title}"'
                ])
            
            else:  # Linux
                # notify-send
                subprocess.run(['notify-send', title, message])
        
        except Exception as e:
            logger.error(f"Erreur notification: {e}")

# Initialisation des répertoires
def initialize_platform_dirs():
    """Initialise les répertoires spécifiques à la plateforme"""
    dirs_to_create = [
        PathUtils.get_config_dir(),
        PathUtils.get_cache_dir(),
        PathUtils.get_temp_dir()
    ]
    
    for directory in dirs_to_create:
        PathUtils.ensure_directory(directory)
    
    logger.info(f"Répertoires plateforme initialisés pour {PlatformInfo.get_platform_name()}")

# Auto-initialisation
initialize_platform_dirs()
