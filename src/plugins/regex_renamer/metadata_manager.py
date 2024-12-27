import xattr
import json
from pathlib import Path
from src.core.logger import Logger

logger = Logger.get_logger('MetadataManager')

class MetadataManager:
    """Gestionnaire de métadonnées personnalisées pour VideoFlow."""
    
    # Attribut étendu spécifique à VideoFlow pour stocker les noms originaux
    VIDEOFLOW_ORIGINAL_NAME = "user.videoflow.original_name"
    
    @staticmethod
    def save_original_name(file_path: Path, original_name: str) -> bool:
        """
        Sauvegarde le nom original du fichier dans un attribut étendu.
        
        Args:
            file_path: Chemin du fichier
            original_name: Nom original à sauvegarder
            
        Returns:
            bool: True si la sauvegarde a réussi, False sinon
        """
        try:
            metadata = {
                "original_name": original_name,
                "timestamp": str(Path(file_path).stat().st_mtime)
            }
            xattr.setxattr(str(file_path), MetadataManager.VIDEOFLOW_ORIGINAL_NAME, 
                          json.dumps(metadata).encode())
            logger.debug(f"Nom original sauvegardé pour {file_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du nom original : {e}")
            return False
    
    @staticmethod
    def get_original_name(file_path: Path) -> str:
        """
        Récupère le nom original du fichier depuis l'attribut étendu.
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            str: Nom original ou chaîne vide si non trouvé
        """
        try:
            metadata_bytes = xattr.getxattr(str(file_path), MetadataManager.VIDEOFLOW_ORIGINAL_NAME)
            metadata = json.loads(metadata_bytes.decode())
            return metadata.get("original_name", "")
        except Exception as e:
            logger.debug(f"Pas de nom original trouvé pour {file_path}: {e}")
            return ""
    
    @staticmethod
    def has_original_name(file_path: Path) -> bool:
        """
        Vérifie si un fichier a un nom original stocké.
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            bool: True si un nom original existe, False sinon
        """
        try:
            return MetadataManager.VIDEOFLOW_ORIGINAL_NAME.encode() in xattr.listxattr(str(file_path))
        except Exception:
            return False
    
    @staticmethod
    def remove_original_name(file_path: Path) -> bool:
        """
        Supprime le nom original stocké.
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        try:
            if MetadataManager.has_original_name(file_path):
                xattr.removexattr(str(file_path), MetadataManager.VIDEOFLOW_ORIGINAL_NAME)
                logger.debug(f"Nom original supprimé pour {file_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du nom original : {e}")
            return False
