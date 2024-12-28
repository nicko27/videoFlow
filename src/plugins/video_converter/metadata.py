"""Gestion des métadonnées pour le plugin VideoConverter."""

import json
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any
from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.Metadata')

@dataclass
class ConversionMetadata:
    """Métadonnées de conversion."""
    original_path: Path
    converted_path: Path
    conversion_date: datetime
    conversion_params: Dict[str, Any]
    original_size: int
    converted_size: int
    compression_ratio: float  # en pourcentage
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConversionMetadata':
        """Crée une instance à partir d'un dictionnaire."""
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
        """Convertit l'instance en dictionnaire."""
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
    """Gestionnaire de métadonnées."""
    
    CONVERSION_TAG = "com.videoflow.conversion"
    
    @staticmethod
    def get_metadata(file_path: Path) -> ConversionMetadata:
        """Récupère les métadonnées de conversion d'un fichier."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                tags = data.get('format', {}).get('tags', {})
                
                if MetadataManager.CONVERSION_TAG in tags:
                    meta_dict = json.loads(tags[MetadataManager.CONVERSION_TAG])
                    return ConversionMetadata.from_dict(meta_dict)
            
            return ConversionMetadata(
                original_path=file_path,
                converted_path=file_path,
                conversion_date=datetime.now(),
                conversion_params={},
                original_size=0,
                converted_size=0,
                compression_ratio=0.0
            )
        except Exception as e:
            logger.error(f"Erreur lors de la lecture des métadonnées de {file_path}: {e}")
            return ConversionMetadata(
                original_path=file_path,
                converted_path=file_path,
                conversion_date=datetime.now(),
                conversion_params={},
                original_size=0,
                converted_size=0,
                compression_ratio=0.0
            )
    
    @staticmethod
    def set_metadata(file_path: Path, metadata: ConversionMetadata):
        """Définit les métadonnées de conversion d'un fichier."""
        try:
            meta_json = json.dumps(metadata.to_dict())
            
            # Créer un fichier temporaire avec les métadonnées
            temp_path = file_path.with_suffix('.temp' + file_path.suffix)
            
            cmd = [
                'ffmpeg',
                '-i', str(file_path),
                '-c', 'copy',
                '-metadata', f'{MetadataManager.CONVERSION_TAG}={meta_json}',
                str(temp_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Remplacer le fichier original
                temp_path.replace(file_path)
                logger.debug(f"Métadonnées mises à jour pour {file_path}")
            else:
                logger.error(f"Erreur lors de la mise à jour des métadonnées: {result.stderr}")
                if temp_path.exists():
                    temp_path.unlink()
        
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métadonnées de {file_path}: {e}")
            if temp_path.exists():
                temp_path.unlink()
    
    @staticmethod
    def mark_as_converted(input_path: Path, output_path: Path, params: Dict[str, Any]):
        """Marque un fichier comme converti."""
        try:
            original_size = input_path.stat().st_size
            new_size = output_path.stat().st_size
            ratio = ((original_size - new_size) / original_size) * 100  # Pourcentage de réduction
            
            metadata = ConversionMetadata(
                original_path=input_path,
                converted_path=output_path,
                conversion_date=datetime.now(),
                conversion_params=params,
                original_size=original_size,
                converted_size=new_size,
                compression_ratio=ratio
            )
            
            MetadataManager.set_metadata(input_path, metadata)
            logger.debug(f"Métadonnées mises à jour pour {input_path}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métadonnées : {e}")
            # Ne pas lever l'erreur, la conversion est réussie même si les métadonnées échouent
    
    @staticmethod
    def _save_metadata(file_path: Path, metadata: ConversionMetadata):
        try:
            meta_json = json.dumps(metadata.to_dict())
            
            # Créer un fichier temporaire avec les métadonnées
            temp_path = file_path.with_suffix('.temp' + file_path.suffix)
            
            cmd = [
                'ffmpeg',
                '-i', str(file_path),
                '-c', 'copy',
                '-metadata', f'{MetadataManager.CONVERSION_TAG}={meta_json}',
                str(temp_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Remplacer le fichier original
                temp_path.replace(file_path)
            else:
                logger.error(f"Erreur lors de la mise à jour des métadonnées: {result.stderr}")
                if temp_path.exists():
                    temp_path.unlink()
        
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métadonnées de {file_path}: {e}")
            if temp_path.exists():
                temp_path.unlink()
    
    @staticmethod
    def increment_attempt(file_path: Path):
        """Incrémente le compteur de tentatives."""
        metadata = MetadataManager.get_metadata(file_path)
        # TODO: implémenter l'incrémentation du compteur de tentatives
        MetadataManager.set_metadata(file_path, metadata)
