import os
import shutil
from pathlib import Path
import osxmetadata
from src.core.logger import Logger

logger = Logger.get_logger('CopyManager')

class CopyManager:
    def __init__(self):
        self.total_size = 0
        self.copied_size = 0
    
    def calculate_total_size(self, source_path):
        """Calcule la taille totale des éléments à copier"""
        total_size = 0
        try:
            if os.path.isfile(source_path):
                total_size = os.path.getsize(source_path)
            else:
                for root, dirs, files in os.walk(source_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            total_size += os.path.getsize(file_path)
                        except OSError as e:
                            logger.warning(f"Impossible de calculer la taille de {file_path}: {e}")
                            continue
            
            return total_size
        except Exception as e:
            logger.error(f"Erreur lors du calcul de la taille totale : {e}")
            return 0
    
    def copy_with_progress(self, source_path, dest_path, progress_callback=None):
        """Copie un fichier ou dossier avec suivi de la progression"""
        try:
            # Calculer la taille totale
            self.total_size = self.calculate_total_size(source_path)
            self.copied_size = 0
            
            if self.total_size == 0:
                logger.warning("Taille totale nulle, impossible de suivre la progression")
                return self.copy_file(source_path, dest_path)
            
            if os.path.isfile(source_path):
                return self._copy_file_with_progress(source_path, dest_path, progress_callback)
            else:
                return self._copy_dir_with_progress(source_path, dest_path, progress_callback)
                
        except Exception as e:
            logger.error(f"Erreur lors de la copie : {e}")
            return None
    
    def _copy_file_with_progress(self, source_path, dest_path, progress_callback):
        """Copie un fichier avec suivi de la progression"""
        try:
            # Créer le dossier de destination si nécessaire
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Copier le fichier par blocs
            with open(source_path, 'rb') as fsrc:
                with open(dest_path, 'wb') as fdst:
                    while True:
                        buffer = fsrc.read(8388608)  # 8MB par bloc
                        if not buffer:
                            break
                        fdst.write(buffer)
                        self.copied_size += len(buffer)
                        if progress_callback:
                            progress = min(100, int((self.copied_size / self.total_size) * 100))
                            progress_callback(progress)
            
            # Copier les métadonnées
            self.copy_metadata(source_path, dest_path)
            return dest_path
            
        except Exception as e:
            logger.error(f"Erreur lors de la copie du fichier {source_path}: {e}")
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except:
                    pass
            return None
    
    def _copy_dir_with_progress(self, source_path, dest_path, progress_callback):
        """Copie un dossier avec suivi de la progression"""
        try:
            # Créer le dossier de destination
            os.makedirs(dest_path, exist_ok=True)
            
            # Copier chaque fichier
            for root, dirs, files in os.walk(source_path):
                # Créer les sous-dossiers
                for dir_name in dirs:
                    src_dir = os.path.join(root, dir_name)
                    dst_dir = os.path.join(dest_path, os.path.relpath(src_dir, source_path))
                    os.makedirs(dst_dir, exist_ok=True)
                
                # Copier les fichiers
                for file_name in files:
                    src_file = os.path.join(root, file_name)
                    dst_file = os.path.join(dest_path, os.path.relpath(src_file, source_path))
                    
                    # Copier le fichier
                    self._copy_file_with_progress(src_file, dst_file, progress_callback)
            
            return dest_path
            
        except Exception as e:
            logger.error(f"Erreur lors de la copie du dossier {source_path}: {e}")
            if os.path.exists(dest_path):
                try:
                    shutil.rmtree(dest_path)
                except:
                    pass
            return None
    
    def copy_metadata(self, source_path, dest_path):
        """Copie les métadonnées d'un fichier vers un autre"""
        try:
            # Obtenir les métadonnées source
            source_meta = osxmetadata.OSXMetaData(source_path)
            dest_meta = osxmetadata.OSXMetaData(dest_path)
            
            # Liste des attributs à copier
            attributes = [
                'kMDItemWhereFroms',
                'kMDItemDownloadedDate',
                'kMDItemCreator',
                '_kMDItemUserTags',
                'kMDItemFinderComment'
            ]
            
            # Copier chaque attribut
            for attr in attributes:
                try:
                    if hasattr(source_meta, attr):
                        value = getattr(source_meta, attr)
                        if value:
                            setattr(dest_meta, attr, value)
                except Exception as e:
                    logger.warning(f"Impossible de copier l'attribut {attr}: {e}")
                    continue
            
            logger.debug("Métadonnées copiées avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la copie des métadonnées : {str(e)}")
            return False
            
    def get_unique_name(self, path):
        """Génère un nom unique si le fichier existe déjà"""
        if not os.path.exists(path):
            return path
            
        base, ext = os.path.splitext(path)
        counter = 1
        
        while True:
            new_name = f"{base} ({counter}){ext}"
            if not os.path.exists(new_name):
                return new_name
            counter += 1
            
    def count_items(self, path):
        """Compte le nombre total d'éléments à copier"""
        total = 0
        for root, dirs, files in os.walk(path):
            total += len(dirs)  # Compter les dossiers
            total += len(files)  # Compter les fichiers
        return max(total, 1)  # Au moins 1 pour éviter division par zéro
