"""Gestion des métadonnées optimisée pour VideoConverter plugin."""

import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any
from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.Metadata')

@dataclass
class ConversionMetadata:
    """Métadonnées de conversion optimisées."""
    original_path: Path
    converted_path: Path
    conversion_date: datetime
    conversion_params: Dict[str, Any]
    original_size: int
    converted_size: int
    compression_ratio: float  # en pourcentage
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConversionMetadata':
        """Créer une instance depuis un dictionnaire."""
        return cls(
            original_path=Path(data['original_path']),
            converted_path=Path(data['converted_path']),
            conversion_date=datetime.fromisoformat(data['conversion_date']),
            conversion_params=data['conversion_params'],
            original_size=data['original_size'],
            converted_size=data['converted_size'],
            compression_ratio=data['compression_ratio']
        )
    
    def to_dict(self) -> dict:
        """Convertir l'instance en dictionnaire."""
        return {
            'original_path': str(self.original_path),
            'converted_path': str(self.converted_path),
            'conversion_date': self.conversion_date.isoformat(),
            'conversion_params': self.conversion_params,
            'original_size': self.original_size,
            'converted_size': self.converted_size,
            'compression_ratio': self.compression_ratio
        }

class MetadataManager:
    """Gestionnaire de métadonnées optimisé pour performance."""
    
    CONVERSION_TAG = "com.videoflow.conversion"
    
    # Cache pour éviter les lectures répétées
    _metadata_cache = {}
    _cache_timestamps = {}
    
    @staticmethod
    def _get_cache_key(file_path: Path) -> str:
        """Générer une clé de cache pour un fichier."""
        return str(file_path.resolve())
    
    @staticmethod
    def _is_cache_valid(file_path: Path) -> bool:
        """Vérifier si le cache est valide pour un fichier."""
        cache_key = MetadataManager._get_cache_key(file_path)
        
        if cache_key not in MetadataManager._metadata_cache:
            return False
        
        try:
            current_mtime = file_path.stat().st_mtime
            cached_mtime = MetadataManager._cache_timestamps.get(cache_key, 0)
            return current_mtime <= cached_mtime
        except OSError:
            return False
    
    @staticmethod
    def _update_cache(file_path: Path, metadata: Optional[ConversionMetadata]):
        """Mettre à jour le cache pour un fichier."""
        cache_key = MetadataManager._get_cache_key(file_path)
        
        try:
            MetadataManager._metadata_cache[cache_key] = metadata
            MetadataManager._cache_timestamps[cache_key] = file_path.stat().st_mtime
        except OSError:
            # Si on ne peut pas obtenir mtime, on cache quand même
            MetadataManager._metadata_cache[cache_key] = metadata
            MetadataManager._cache_timestamps[cache_key] = datetime.now().timestamp()
    
    @staticmethod
    def get_metadata(file_path: Path) -> Optional[ConversionMetadata]:
        """Obtenir les métadonnées de conversion d'un fichier avec cache."""
        if not file_path.exists():
            return None
        
        # Vérifier le cache
        if MetadataManager._is_cache_valid(file_path):
            cache_key = MetadataManager._get_cache_key(file_path)
            return MetadataManager._metadata_cache.get(cache_key)
        
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                tags = data.get('format', {}).get('tags', {})
                
                metadata = None
                if MetadataManager.CONVERSION_TAG in tags:
                    try:
                        meta_dict = json.loads(tags[MetadataManager.CONVERSION_TAG])
                        metadata = ConversionMetadata.from_dict(meta_dict)
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning(f"Métadonnées invalides dans {file_path}: {e}")
                        metadata = None
                
                # Mettre à jour le cache
                MetadataManager._update_cache(file_path, metadata)
                return metadata
            
            # Pas de métadonnées, mettre à jour le cache
            MetadataManager._update_cache(file_path, None)
            return None
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout lors de la lecture des métadonnées de {file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON invalide dans la sortie ffprobe pour {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la lecture des métadonnées de {file_path}: {e}")
            return None
    
    @staticmethod
    def set_metadata(file_path: Path, metadata: ConversionMetadata) -> bool:
        """Définir les métadonnées de conversion pour un fichier avec gestion cross-device."""
        if not file_path.exists():
            logger.error(f"Impossible de définir les métadonnées: fichier inexistant: {file_path}")
            return False
        
        temp_path = None
        try:
            # Valider les métadonnées
            meta_json = json.dumps(metadata.to_dict(), separators=(',', ':'))  # Format compact
            if len(meta_json) > 7000:  # Limite de sécurité FFmpeg
                logger.warning(f"Métadonnées trop volumineuses pour {file_path}, ignorées")
                return False
            
            # Créer un fichier temporaire dans le même dossier pour éviter cross-device
            parent_dir = file_path.parent
            temp_name = f"metadata_temp_{file_path.stem}_{datetime.now().strftime('%H%M%S')}{file_path.suffix}"
            temp_path = parent_dir / temp_name
            
            cmd = [
                'ffmpeg',
                '-i', str(file_path),
                '-c', 'copy',  # Copier sans réencodage
                '-metadata', f'{MetadataManager.CONVERSION_TAG}={meta_json}',
                '-y',  # Écraser le fichier de sortie
                str(temp_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                # Vérifier que le fichier temporaire a été créé correctement
                if temp_path.exists() and temp_path.stat().st_size > 0:
                    # Remplacer le fichier original (même device, pas de cross-device link)
                    file_path.unlink()
                    temp_path.rename(file_path)
                    
                    # Invalider le cache
                    cache_key = MetadataManager._get_cache_key(file_path)
                    MetadataManager._metadata_cache.pop(cache_key, None)
                    MetadataManager._cache_timestamps.pop(cache_key, None)
                    
                    logger.debug(f"Métadonnées mises à jour pour {file_path}")
                    return True
                else:
                    logger.error(f"Fichier temporaire vide ou inexistant: {temp_path}")
                    return False
            else:
                logger.error(f"Erreur ffmpeg lors de la mise à jour des métadonnées pour {file_path}: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout lors de la mise à jour des métadonnées pour {file_path}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métadonnées pour {file_path}: {e}")
            return False
        finally:
            # Nettoyer le fichier temporaire
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as e:
                    logger.warning(f"Impossible de nettoyer le fichier temporaire {temp_path}: {e}")
    
    @staticmethod
    def mark_as_converted(input_path: Path, output_path: Path, params: Dict[str, Any]) -> bool:
        """Marquer un fichier comme converti avec gestion d'erreur robuste."""
        try:
            if not input_path.exists():
                logger.error(f"Fichier d'entrée inexistant: {input_path}")
                return False
            
            # Obtenir la taille originale
            try:
                original_size = input_path.stat().st_size
            except OSError as e:
                logger.error(f"Impossible d'obtenir la taille du fichier original: {e}")
                return False
            
            # Déterminer quel fichier utiliser pour la taille convertie
            if output_path.exists():
                try:
                    new_size = output_path.stat().st_size
                    metadata_target = output_path
                except OSError as e:
                    logger.error(f"Impossible d'obtenir la taille du fichier converti: {e}")
                    return False
            else:
                # Le fichier pourrait avoir été remplacé
                if input_path.exists():
                    try:
                        new_size = input_path.stat().st_size
                        metadata_target = input_path
                    except OSError as e:
                        logger.error(f"Impossible d'obtenir la taille après remplacement: {e}")
                        return False
                else:
                    logger.error("Aucun fichier de sortie trouvé")
                    return False
            
            # Calculer le ratio de compression
            if original_size > 0:
                ratio = ((original_size - new_size) / original_size) * 100
            else:
                ratio = 0.0
            
            # Créer les métadonnées
            metadata = ConversionMetadata(
                original_path=input_path,
                converted_path=output_path,
                conversion_date=datetime.now(),
                conversion_params=params,
                original_size=original_size,
                converted_size=new_size,
                compression_ratio=ratio
            )
            
            # Essayer de définir les métadonnées
            success = MetadataManager.set_metadata(metadata_target, metadata)
            if success:
                logger.info(f"Métadonnées définies pour {metadata_target}: {ratio:.1f}% de compression")
            else:
                logger.warning(f"Échec de la définition des métadonnées pour {metadata_target}, conversion toujours réussie")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors du marquage du fichier comme converti: {e}")
            return False
    
    @staticmethod
    def has_conversion_metadata(file_path: Path) -> bool:
        """Vérifier si un fichier a des métadonnées de conversion."""
        metadata = MetadataManager.get_metadata(file_path)
        return metadata is not None and metadata.compression_ratio > 0
    
    @staticmethod
    def get_compression_ratio(file_path: Path) -> float:
        """Obtenir le ratio de compression depuis les métadonnées."""
        metadata = MetadataManager.get_metadata(file_path)
        return metadata.compression_ratio if metadata else 0.0
    
    @staticmethod
    def remove_metadata(file_path: Path) -> bool:
        """Supprimer les métadonnées de conversion d'un fichier."""
        if not file_path.exists():
            logger.error(f"Fichier inexistant: {file_path}")
            return False
        
        temp_path = None
        try:
            # Créer un fichier temporaire sans métadonnées
            temp_fd, temp_path_str = tempfile.mkstemp(
                suffix=file_path.suffix, 
                prefix=f"remove_meta_{file_path.stem}_"
            )
            temp_path = Path(temp_path_str)
            
            import os
            os.close(temp_fd)
            
            cmd = [
                'ffmpeg',
                '-i', str(file_path),
                '-c', 'copy',
                '-map_metadata', '-1',  # Supprimer toutes les métadonnées
                '-y',
                str(temp_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and temp_path.exists() and temp_path.stat().st_size > 0:
                file_path.unlink()
                temp_path.rename(file_path)
                
                # Invalider le cache
                cache_key = MetadataManager._get_cache_key(file_path)
                MetadataManager._metadata_cache.pop(cache_key, None)
                MetadataManager._cache_timestamps.pop(cache_key, None)
                
                logger.debug(f"Métadonnées supprimées de {file_path}")
                return True
            else:
                logger.error(f"Échec de la suppression des métadonnées de {file_path}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout lors de la suppression des métadonnées de {file_path}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des métadonnées de {file_path}: {e}")
            return False
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as e:
                    logger.warning(f"Impossible de nettoyer le fichier temporaire {temp_path}: {e}")
    
    @staticmethod
    def clear_cache():
        """Vider le cache des métadonnées."""
        MetadataManager._metadata_cache.clear()
        MetadataManager._cache_timestamps.clear()
        logger.debug("Cache des métadonnées vidé")
    
    @staticmethod
    def get_cache_stats() -> Dict[str, int]:
        """Obtenir les statistiques du cache."""
        return {
            'cached_files': len(MetadataManager._metadata_cache),
            'files_with_metadata': sum(1 for meta in MetadataManager._metadata_cache.values() if meta is not None)
        }