import json
import os
from typing import Dict, List, Set
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.DataManager')

class DataManager:
    def __init__(self):
        """Initialise le gestionnaire de données"""
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data')
        self.data_file = os.path.join(self.data_dir, 'duplicate_finder.json')
        self.ignored_pairs_file = os.path.join(self.data_dir, 'duplicate_finder_ignored.json')
        self.analyzed_files = {}
        self.ignored_pairs = set()  # Ensemble des paires de fichiers ignorées
        self.load_data()

    def load_data(self):
        """Charge les données depuis les fichiers JSON"""
        try:
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
            
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.analyzed_files = json.load(f)
                # Nettoyer les fichiers qui n'existent plus
                self.clean_missing_files()

            if os.path.exists(self.ignored_pairs_file):
                with open(self.ignored_pairs_file, 'r', encoding='utf-8') as f:
                    # Convertir la liste de paires en ensemble pour une recherche plus rapide
                    self.ignored_pairs = set(tuple(pair) for pair in json.load(f))
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données : {e}")
            self.analyzed_files = {}
            self.ignored_pairs = set()

    def save_data(self):
        """Sauvegarde les données dans les fichiers JSON"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.analyzed_files, f, indent=2, ensure_ascii=False)
            
            with open(self.ignored_pairs_file, 'w', encoding='utf-8') as f:
                # Convertir l'ensemble en liste pour la sérialisation JSON
                json.dump([list(pair) for pair in self.ignored_pairs], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données : {e}")

    def add_analyzed_file(self, file_path: str, file_hash: str):
        """Ajoute un fichier analysé"""
        self.analyzed_files[file_path] = file_hash
        self.save_data()

    def clean_missing_files(self):
        """Supprime les fichiers qui n'existent plus"""
        to_remove = []
        for file_path in self.analyzed_files:
            if not os.path.exists(file_path):
                to_remove.append(file_path)
        
        for file_path in to_remove:
            del self.analyzed_files[file_path]
        
        if to_remove:
            self.save_data()

    def add_ignored_pair(self, file1: str, file2: str, permanent: bool = True):
        """Ajoute une paire de fichiers à ignorer"""
        if permanent:
            self.ignored_pairs.add(tuple(sorted([file1, file2])))
            self.save_data()

    def is_pair_ignored(self, file1: str, file2: str) -> bool:
        """Vérifie si une paire de fichiers est ignorée"""
        return tuple(sorted([file1, file2])) in self.ignored_pairs

    def clear_data(self):
        """Efface toutes les données"""
        self.analyzed_files = {}
        self.ignored_pairs = set()
        for file in [self.data_file, self.ignored_pairs_file]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression du fichier {file} : {e}")
        logger.info("Données effacées avec succès")

    def get_analyzed_files(self) -> Dict[str, str]:
        """Retourne les fichiers analysés"""
        return self.analyzed_files

    def find_duplicates(self) -> List[Set[str]]:
        """Trouve les groupes de fichiers en double"""
        from .video_hasher import VideoHasher
        hasher = VideoHasher()
        
        # Grouper les fichiers par hash
        hash_groups = {}
        for file_path, file_hash in self.analyzed_files.items():
            if not os.path.exists(file_path):
                continue
                
            found_group = False
            # Comparer avec les groupes existants
            for group_hash, group in hash_groups.items():
                if hasher.are_similar(file_hash, group_hash):
                    group.add(file_path)
                    found_group = True
                    break
            
            if not found_group:
                hash_groups[file_hash] = {file_path}

        # Retourner uniquement les groupes avec des doublons
        return [group for group in hash_groups.values() if len(group) > 1]
