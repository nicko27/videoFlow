import os
import shutil
from osxmetadata import OSXMetaData
from src.core.logger import Logger

logger = Logger.get_logger('CopyManager')

class CopyManager:
    def __init__(self):
        pass
    
    def count_items(self, path):
        """Compte le nombre total d'éléments à copier"""
        total = 0
        for root, dirs, files in os.walk(path):
            total += len(dirs)  # Compter les dossiers
            total += len(files)  # Compter les fichiers
        return max(total, 1)  # Au moins 1 pour éviter division par zéro
    
    def get_unique_name(self, path):
        """Génère un nom unique pour un fichier"""
        if not os.path.exists(path):
            return path
        
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)
        
        counter = 1
        while True:
            new_name = os.path.join(directory, f"{name} ({counter}){ext}")
            if not os.path.exists(new_name):
                return new_name
            counter += 1
    
    def copy_metadata(self, source, destination):
        """Copie toutes les métadonnées macOS d'un fichier vers un autre"""
        try:
            # Créer les objets OSXMetaData
            src_meta = OSXMetaData(source)
            dst_meta = OSXMetaData(destination)
            
            # Copier les tags
            if src_meta.tags:
                dst_meta.tags = src_meta.tags
                logger.debug(f"Tags copiés : {src_meta.tags}")
            
            # Copier les commentaires Finder
            if src_meta.findercomment:
                dst_meta.findercomment = src_meta.findercomment
                logger.debug(f"Commentaire copié : {src_meta.findercomment}")
            
            # Copier les étiquettes de couleur
            if src_meta.finder_color:
                dst_meta.finder_color = src_meta.finder_color
                logger.debug(f"Couleur copiée : {src_meta.finder_color}")
            
            # Copier les dates personnalisées
            if src_meta.dateadded:
                dst_meta.dateadded = src_meta.dateadded
            if src_meta.lastuseddate:
                dst_meta.lastuseddate = src_meta.lastuseddate
            
            # Copier les métadonnées Spotlight
            if src_meta.authors:
                dst_meta.authors = src_meta.authors
            if src_meta.keywords:
                dst_meta.keywords = src_meta.keywords
            if src_meta.title:
                dst_meta.title = src_meta.title
            if src_meta.copyright:
                dst_meta.copyright = src_meta.copyright
            
            logger.debug(f"Métadonnées copiées de {source} vers {destination}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la copie des métadonnées : {str(e)}")
