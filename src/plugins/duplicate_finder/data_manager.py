
import json
import tempfile
import shutil
from pathlib import Path

class SafeJSONManager:
    """Gestionnaire JSON sécurisé avec sauvegarde atomique"""
    
    @staticmethod
    def safe_save(data, file_path, backup=True):
        """Sauvegarde JSON de manière atomique"""
        file_path = Path(file_path)
        
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.json.tmp',
            dir=file_path.parent,
            delete=False,
            encoding='utf-8'
        ) as tmp_file:
            try:
                json.dump(data, tmp_file, indent=4, ensure_ascii=False)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())  # Force l'écriture sur disque
                tmp_path = tmp_file.name
            except Exception as e:
                os.unlink(tmp_file.name)
                raise VideoFlowError(
                    f"Erreur écriture JSON temporaire: {e}",
                    ErrorType.FILE_IO,
                    ErrorSeverity.HIGH
                )
        
        # Sauvegarder l'ancien fichier si demandé
        if backup and file_path.exists():
            backup_path = file_path.with_suffix('.json.bak')
            try:
                shutil.copy2(file_path, backup_path)
            except Exception as e:
                logger.warning(f"Impossible de créer la sauvegarde: {e}")
        
        # Remplacer atomiquement
        try:
            shutil.move(tmp_path, file_path)
        except Exception as e:
            os.unlink(tmp_path)
            raise VideoFlowError(
                f"Erreur remplacement atomique: {e}",
                ErrorType.FILE_IO,
                ErrorSeverity.HIGH
            )
    
    @staticmethod
    def safe_load(file_path, default=None):
        """Charge JSON de manière sécurisée"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return default
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # Tenter de charger la sauvegarde
            backup_path = file_path.with_suffix('.json.bak')
            if backup_path.exists():
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        logger.warning(f"JSON corrompu, restauration depuis sauvegarde: {file_path}")
                        return json.load(f)
                except Exception:
                    pass
            
            raise VideoFlowError(
                f"Erreur parsing JSON: {e}",
                ErrorType.FILE_IO,
                ErrorSeverity.HIGH,
                {"file_path": str(file_path)}
            )
        except Exception as e:
            raise VideoFlowError(
                f"Erreur lecture JSON: {e}",
                ErrorType.FILE_IO,
                ErrorSeverity.HIGH,
                {"file_path": str(file_path)}
            )


import os
import json
import numpy as np
from typing import Dict, Set, List, Any
import logging

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self):
        """Initialise le gestionnaire de données"""
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.data_file = os.path.join(self.data_dir, "duplicate_finder.json")
        self.analyzed_files: Dict[str, List[bool]] = {}  # Chemin -> Hash
        self.ignored_pairs: Set[tuple] = set()  # Paires de fichiers ignorées
        
        self.load_data()

    def add_analyzed_file(self, file_path: str, file_hash: List[np.ndarray]) -> None:
        """
        Ajoute un fichier analysé à la base de données
        :param file_path: Chemin du fichier
        :param file_hash: Hash du fichier
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"Le fichier {file_path} n'existe pas")
                return
                
            # Convertir le hash numpy en liste de booléens pour la sérialisation JSON
            hash_list = [h.tolist() for h in file_hash]
            self.analyzed_files[file_path] = hash_list
            self.save_data()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du fichier {file_path}: {e}")

    def get_analyzed_files(self) -> Dict[str, List[np.ndarray]]:
        """Retourne les fichiers analysés"""
        try:
            # Ne retourne que les fichiers qui existent encore
            return {
                path: [np.array(h) for h in hash_list] 
                for path, hash_list in self.analyzed_files.items()
                if os.path.exists(path)
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des fichiers analysés: {e}")
            return {}

    def add_ignored_pair(self, file1: str, file2: str) -> None:
        """
        Ajoute une paire de fichiers à ignorer
        :param file1: Premier fichier
        :param file2: Deuxième fichier
        """
        # Toujours stocker dans l'ordre alphabétique pour la cohérence
        pair = tuple(sorted([file1, file2]))
        self.ignored_pairs.add(pair)

    def is_pair_ignored(self, file1: str, file2: str) -> bool:
        """
        Vérifie si une paire de fichiers est ignorée
        :param file1: Premier fichier
        :param file2: Deuxième fichier
        :return: True si la paire est ignorée
        """
        pair = tuple(sorted([file1, file2]))
        return pair in self.ignored_pairs

    def save_data(self) -> None:
        """Sauvegarde les données dans un fichier JSON"""
        try:
            data = {
                "analyzed_files": self.analyzed_files,
                "ignored_pairs": list(self.ignored_pairs)  # Convertir le set en liste
            }
            
            with open(self.data_file, "w") as f:
                SafeJSONManager.safe_save(data, f.name)
            
            logger.info(f"Données sauvegardées dans {self.data_file}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données: {e}")

    def load_data(self) -> None:
        """Charge les données depuis le fichier JSON"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    data = SafeJSONManager.safe_load(f.name)
                
                self.analyzed_files = data.get("analyzed_files", {})
                # Convertir la liste en set de tuples
                self.ignored_pairs = set(tuple(pair) for pair in data.get("ignored_pairs", []))
                
                logger.info(f"Données chargées depuis {self.data_file}")
            else:
                logger.info("Aucun fichier de données trouvé, création d'une nouvelle base")
        
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données: {e}")
            self.analyzed_files = {}
            self.ignored_pairs = set()

    def clear_data(self) -> None:
        """Efface toutes les données"""
        self.analyzed_files.clear()
        self.ignored_pairs.clear()
        
        try:
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
            logger.info("Données effacées avec succès")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'effacement des données: {e}")
