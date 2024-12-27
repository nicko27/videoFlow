from pathlib import Path
import re
from typing import List, Dict, Tuple
from .metadata_manager import MetadataManager
from .sequence_manager import SequenceManager, SequencePattern
from src.core.logger import Logger

logger = Logger.get_logger('RegexRenamer')

class RegexRenamer:
    """Plugin de renommage avec expressions régulières et gestion des séquences."""
    
    def __init__(self):
        self.metadata_manager = MetadataManager()
        self.sequence_manager = SequenceManager()
        self.history: Dict[str, List[str]] = {}  # Historique des renommages par fichier
        
    def preview_rename(self, file_path: Path, patterns: List[dict], 
                      sequences: List[SequencePattern]) -> Tuple[str, List[Tuple[int, int]]]:
        """
        Prévisualise les modifications sans les appliquer.
        
        Args:
            file_path: Chemin du fichier
            patterns: Liste des patterns regex à appliquer
            sequences: Liste des séquences à supprimer
            
        Returns:
            Tuple[str, List[Tuple[int, int]]]: Nouveau nom et positions des modifications
        """
        original_name = file_path.stem
        modified_name = original_name
        modifications = []
        
        # Appliquer les patterns regex
        for pattern in sorted(patterns, key=lambda x: x.get('priority', 0), reverse=True):
            if not pattern.get('enabled', True):
                continue
                
            regex = pattern['pattern']
            action = pattern.get('action', 'd')
            replace_with = pattern.get('replace_with', '')
            
            try:
                # Trouver toutes les occurrences
                for match in re.finditer(regex, modified_name, re.IGNORECASE):
                    modifications.append(match.span())
                    
                # Appliquer la modification
                if action == 'd':
                    modified_name = re.sub(regex, '', modified_name, flags=re.IGNORECASE)
                elif action == 'r':
                    modified_name = re.sub(regex, replace_with, modified_name, flags=re.IGNORECASE)
                
            except re.error as e:
                logger.error(f"Erreur dans le pattern '{regex}': {e}")
        
        # Appliquer les suppressions de séquences
        for seq_pattern in sequences:
            seq_pos = self.sequence_manager.detect_sequence(modified_name, seq_pattern)
            if seq_pos:
                modifications.append(seq_pos)
                modified_name = self.sequence_manager.remove_sequence(modified_name, seq_pattern)
        
        # Nettoyer les espaces multiples
        modified_name = re.sub(r'\s+', ' ', modified_name).strip()
        
        return modified_name, modifications
    
    def rename_file(self, file_path: Path, new_name: str) -> bool:
        """
        Renomme un fichier en sauvegardant son nom original.
        
        Args:
            file_path: Chemin du fichier
            new_name: Nouveau nom
            
        Returns:
            bool: True si le renommage a réussi
        """
        try:
            # Sauvegarder le nom original si pas déjà fait
            if not self.metadata_manager.has_original_name(file_path):
                self.metadata_manager.save_original_name(file_path, file_path.stem)
            
            # Construire le nouveau chemin
            new_path = file_path.with_name(new_name + file_path.suffix)
            
            # Vérifier si le nouveau nom est valide
            if not self._is_valid_filename(new_name):
                logger.error(f"Nom de fichier invalide : {new_name}")
                return False
            
            # Vérifier les conflits
            if new_path.exists() and new_path != file_path:
                logger.error(f"Le fichier {new_path} existe déjà")
                return False
            
            # Renommer le fichier
            file_path.rename(new_path)
            
            # Mettre à jour l'historique
            if str(file_path) not in self.history:
                self.history[str(file_path)] = []
            self.history[str(file_path)].append(str(new_path))
            
            logger.info(f"Fichier renommé : {file_path} -> {new_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du renommage : {e}")
            return False
    
    def restore_original_name(self, file_path: Path) -> bool:
        """
        Restaure le nom original d'un fichier.
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            bool: True si la restauration a réussi
        """
        try:
            original_name = self.metadata_manager.get_original_name(file_path)
            if not original_name:
                logger.error(f"Pas de nom original trouvé pour {file_path}")
                return False
            
            new_path = file_path.with_name(original_name + file_path.suffix)
            if new_path.exists() and new_path != file_path:
                logger.error(f"Le fichier {new_path} existe déjà")
                return False
            
            file_path.rename(new_path)
            self.metadata_manager.remove_original_name(new_path)
            
            logger.info(f"Nom original restauré : {file_path} -> {new_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la restauration : {e}")
            return False
    
    def _is_valid_filename(self, filename: str) -> bool:
        """
        Vérifie si un nom de fichier est valide sous macOS.
        
        Args:
            filename: Nom de fichier à vérifier
            
        Returns:
            bool: True si le nom est valide
        """
        # Caractères invalides sous macOS
        invalid_chars = ['/', '\x00', ':', '*', '?', '"', '<', '>', '|']
        return not any(char in filename for char in invalid_chars)
