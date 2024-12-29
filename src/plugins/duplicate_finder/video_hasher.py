import cv2
import numpy as np
import os
import json
from datetime import datetime
from src.core.logger import Logger
from enum import Enum

logger = Logger.get_logger('DuplicateFinder.VideoHasher')

class HashMethod(Enum):
    """Méthodes de hachage disponibles"""
    PHASH = "pHash"

class VideoInfo:
    def __init__(self, hash_array, duration):
        self.hash_array = hash_array
        self.duration = duration  # durée en secondes

class VideoHasher:
    """Classe pour calculer et comparer les hashs de vidéos"""
    
    def __init__(self, method=HashMethod.PHASH.value):
        """Initialise le hasher de vidéos"""
        self.method = method if isinstance(method, str) else method.value
        self.plugin_dir = os.path.dirname(__file__)
        self.json_file = os.path.join(self.plugin_dir, 'video_hashes.json')
        self.ignored_pairs_file = os.path.join(self.plugin_dir, 'ignored_pairs.json')
        self.hashes = {
            "pHash": {},  # Cache pour pHash uniquement
        }
        self.ignored_pairs = set()
        self.duration = 300  # Durée par défaut : 5 minutes
        self.load_hashes()
        self.load_ignored_pairs()
        
        logger.debug(f"VideoHasher initialisé")
        if self.hashes:
            logger.info(f"Empreintes chargées :")
            for file_path in self.hashes["pHash"]:
                logger.info(f"  - {os.path.basename(file_path)}")

    def load_hashes(self):
        """Charge les hashs depuis le fichier JSON"""
        try:
            if os.path.exists(self.json_file):
                with open(self.json_file, 'r') as f:
                    self.hashes = json.load(f)
                logger.info(f"Hashs chargés depuis {self.json_file}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des hashs: {str(e)}")

    def save_hashes(self):
        """Sauvegarde les hashs dans un fichier JSON"""
        try:
            with open(self.json_file, 'w') as f:
                json.dump(self.hashes, f, indent=4)
            logger.debug(f"Hashs sauvegardés dans {self.json_file}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des hashs : {e}")

    def load_ignored_pairs(self):
        """Charge les paires ignorées depuis le fichier JSON"""
        try:
            if os.path.exists(self.ignored_pairs_file):
                with open(self.ignored_pairs_file, 'r') as f:
                    pairs = json.load(f)
                    # Ne charge que les paires dont les deux fichiers existent encore
                    self.ignored_pairs = {
                        tuple(pair) for pair in pairs 
                        if os.path.exists(pair[0]) and os.path.exists(pair[1])
                    }
                logger.debug(f"Paires ignorées chargées depuis {self.ignored_pairs_file}")
                logger.info(f"{len(self.ignored_pairs)} paires ignorées chargées")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des paires ignorées : {e}")
            self.ignored_pairs = set()

    def save_ignored_pairs(self):
        """Sauvegarde les paires ignorées dans un fichier JSON"""
        try:
            # Sauvegarde uniquement les paires dont les fichiers existent encore
            pairs = [
                list(pair) for pair in self.ignored_pairs 
                if os.path.exists(pair[0]) and os.path.exists(pair[1])
            ]
            
            with open(self.ignored_pairs_file, 'w') as f:
                json.dump(pairs, f, indent=4)
            logger.debug(f"Paires ignorées sauvegardées dans {self.ignored_pairs_file}")
            logger.info(f"{len(pairs)} paires ignorées sauvegardées")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des paires ignorées : {e}")

    def add_ignored_pair(self, file1, file2):
        """Ajoute une paire de fichiers à ignorer"""
        # Toujours stocker dans le même ordre pour éviter les doublons
        pair = tuple(sorted([file1, file2]))
        self.ignored_pairs.add(pair)
        self.save_ignored_pairs()

    def is_pair_ignored(self, file1, file2):
        """Vérifie si une paire de fichiers est ignorée"""
        pair = tuple(sorted([file1, file2]))
        return pair in self.ignored_pairs

    def clear_cache(self):
        """Efface le cache des empreintes"""
        self.hashes = {
            "pHash": {}
        }
        self.save_hashes()
        logger.info("Cache effacé")

    def list_to_numpy(self, hash_list):
        """Convertit une liste de hashes en tableau numpy"""
        return np.array(hash_list)

    def numpy_to_list(self, hash_array):
        """Convertit un tableau numpy en liste"""
        return hash_array.tolist()

    def compute_frame_hash(self, frame):
        """Calcule l'empreinte d'une frame selon la méthode choisie"""
        try:
            if self.method == "pHash":  
                # Méthode pHash (Perceptual Hash)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                resized = cv2.resize(gray, (32, 32))
                dct = cv2.dct(np.float32(resized))
                dct_low = dct[:8, :8]
                avg = (dct_low[1:, :].mean() + dct_low[0, 1:].mean()) / 2
                return dct_low > avg
                
            else:
                raise ValueError(f"Méthode de hash inconnue : {self.method}")
                
        except Exception as e:
            logger.error(f"Erreur lors du calcul de l'empreinte d'une frame : {e}")
            return None

    def compute_video_hash(self, video_path, sample_interval=500):
        """Calcule l'empreinte d'une vidéo"""
        try:
            # Vérifie que le fichier existe
            if not os.path.exists(video_path):
                raise Exception(f"Le fichier {video_path} n'existe pas")
                
            # Vérifie le cache
            if video_path in self.hashes[self.method]:
                logger.info(f"Utilisation de l'empreinte en cache pour {os.path.basename(video_path)}")
                return self.list_to_numpy(self.hashes[self.method][video_path]['hash']), self.hashes[self.method][video_path]['duration']

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.warning(f"Impossible d'ouvrir la vidéo {video_path}")
                raise Exception("Impossible d'ouvrir la vidéo")

            try:
                # Récupère les informations de la vidéo
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                
                if total_frames <= 0:
                    # Compte manuellement les frames
                    total_frames = 0
                    while cap.grab():
                        total_frames += 1
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                
                if fps <= 0:
                    fps = 30  # Valeur par défaut
                
                duration = total_frames / fps
                
                # Prend une frame tous les 500 frames jusqu'à 2500
                frame_indices = [500, 1000, 1500, 2000, 2500]
                # Ne garde que les indices valides (inférieurs au nombre total de frames)
                frame_indices = [idx for idx in frame_indices if idx < total_frames]
                
                # Ajoute toujours la première et la dernière frame
                if 0 not in frame_indices:
                    frame_indices.insert(0, 0)
                if total_frames - 1 not in frame_indices:
                    frame_indices.append(total_frames - 1)
                
                hashes = []
                frames_read = 0
                
                for frame_idx in frame_indices:
                    # Positionne sur la frame exacte
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    success = False
                    
                    # Essaie de lire la frame avec plusieurs tentatives
                    for _ in range(3):  # 3 tentatives maximum
                        ret, frame = cap.read()
                        if ret:
                            frame_hash = self.compute_frame_hash(frame)
                            if frame_hash is not None:
                                hashes.append(frame_hash)
                                frames_read += 1
                                success = True
                                break
                        # Si échec, essaie de se repositionner
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    
                    if not success:
                        logger.warning(f"Impossible de lire la frame {frame_idx} de {video_path}")
                
                if frames_read < 3:
                    raise Exception(f"Pas assez de frames valides ({frames_read} lues)")
                
                final_hash = np.stack(hashes)
                
                # Sauvegarde dans le cache
                self.hashes[self.method][video_path] = {
                    'hash': self.numpy_to_list(final_hash),
                    'duration': duration,
                    'frames': frame_indices  # Sauvegarde les indices utilisés pour debug
                }
                self.save_hashes()
                
                logger.info(f"Empreinte créée pour {os.path.basename(video_path)} avec {frames_read} frames")
                logger.debug(f"Indices des frames utilisées : {frame_indices}")
                
                return final_hash, duration
                
            finally:
                cap.release()

        except Exception as e:
            logger.error(f"Erreur lors du calcul de l'empreinte de {video_path}: {e}")
            raise

    def has_hash(self, file_path):
        """Vérifie si un fichier a déjà une empreinte dans le cache"""
        return file_path in self.hashes[self.method]

    def compute_hamming_similarity(self, hash1, hash2):
        """Calcule la similarité de Hamming entre deux empreintes
        
        La similarité est le nombre de bits identiques divisé par le nombre total de bits.
        Pour le pHash et dHash, il faut comparer bit à bit.
        """
        if self.method == "pHash":  
            # Convertit en binaire et compare bit à bit
            bin1 = np.unpackbits(hash1.astype(np.uint8))
            bin2 = np.unpackbits(hash2.astype(np.uint8))
            return np.sum(bin1 == bin2) / bin1.size
        else:
            # Pour les autres méthodes, compare directement les valeurs
            return np.sum(hash1 == hash2) / hash1.size
            
    def are_similar(self, hash1, hash2, duration1, duration2, threshold=0.85, std_threshold=0.1, ignore_duration=False):
        """Compare deux empreintes de vidéos
        
        Args:
            hash1: Première empreinte
            hash2: Deuxième empreinte
            duration1: Durée de la première vidéo
            duration2: Durée de la deuxième vidéo
            threshold: Seuil de similarité (0-1)
            std_threshold: Seuil d'écart-type (0-1)
            ignore_duration: Si True, ignore les différences de durée importantes
            
        Returns:
            (bool, float, str): (True si similaires, similarité en %, message d'avertissement)
        """
        try:
            if hash1 is None or hash2 is None:
                return False, 0, "Une des empreintes est invalide"
                
            # Compare les durées
            duration_diff = abs(duration1 - duration2)
            warning_message = ""
            
            # Si la différence est de plus de 5 minutes et qu'on ne l'ignore pas
            if duration_diff > 300 and not ignore_duration:  # 300 secondes = 5 minutes
                return False, 0, f"Les durées diffèrent de {int(duration_diff/60)} minutes"
            elif duration_diff > 300:
                warning_message = f"⚠️ Les durées diffèrent de {int(duration_diff/60)} minutes"
            elif duration_diff > 10:
                warning_message = f"Les durées diffèrent de {int(duration_diff)} secondes"
            
            # Vérifie que les dimensions correspondent
            if hash1.shape[1:] != hash2.shape[1:]:
                return False, 0, "Les dimensions des empreintes ne correspondent pas"
            
            # Calcule la similarité entre les frames
            min_frames = min(len(hash1), len(hash2))
            if min_frames < 3:
                return False, 0, "Pas assez de frames pour comparer"
                
            similarities = []
            for i in range(min_frames):
                similarity = self.compute_hamming_similarity(hash1[i], hash2[i])
                similarities.append(similarity)
            
            # Calcule la moyenne et l'écart-type
            mean_similarity = np.mean(similarities)
            std_similarity = np.std(similarities)
            
            # Les vidéos sont similaires si :
            # 1. La similarité moyenne est supérieure au seuil
            # 2. L'écart-type est inférieur au seuil (variation constante)
            is_similar = mean_similarity >= threshold and std_similarity <= std_threshold
            
            # Convertit la similarité en pourcentage
            similarity_percent = mean_similarity * 100
            
            if is_similar:
                if warning_message:
                    logger.warning(f"Similarité : {mean_similarity:.2f}, écart-type : {std_similarity:.2f} - {warning_message}")
                else:
                    logger.info(f"Similarité : {mean_similarity:.2f}, écart-type : {std_similarity:.2f}")
            
            return is_similar, similarity_percent, warning_message
            
        except Exception as e:
            logger.error(f"Erreur lors de la comparaison des empreintes : {e}")
            return False, 0, str(e)

    def get_video_hash(self, file_path):
        """Récupère ou calcule l'empreinte d'une vidéo"""
        try:
            # Vérifie si l'empreinte existe dans le cache pour la méthode actuelle
            if file_path in self.hashes[self.method]:
                logger.debug(f"Empreinte trouvée dans le cache pour {os.path.basename(file_path)}")
                return self.hashes[self.method][file_path]
            
            # Sinon, calcule la nouvelle empreinte
            hash_data = self.compute_video_hash(file_path)
            if hash_data:
                # Sauvegarde dans le cache pour la méthode actuelle
                self.hashes[self.method][file_path] = hash_data
                self.save_hashes()
            return hash_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'empreinte : {e}")
            return None

    def compare_videos(self, video1_path: str, video2_path: str) -> float:
        """Compare deux vidéos et retourne leur pourcentage de similarité

        Args:
            video1_path (str): Chemin de la première vidéo
            video2_path (str): Chemin de la deuxième vidéo

        Returns:
            float: Pourcentage de similarité entre 0 et 100
        """
        # Vérifie que les deux vidéos ont des hashs
        if not self.has_hash(video1_path) or not self.has_hash(video2_path):
            logger.error(f"Une des vidéos n'a pas de hash : {video1_path} ou {video2_path}")
            return 0.0

        # Récupère les hashs et les durées
        hash1 = self.hashes[self.method][video1_path]["hash"]
        hash2 = self.hashes[self.method][video2_path]["hash"]
        duration1 = self.hashes[self.method][video1_path]["duration"]
        duration2 = self.hashes[self.method][video2_path]["duration"]

        # Vérifie la différence de durée
        duration_diff = abs(duration1 - duration2)
        if duration_diff > 300:  # 300 secondes = 5 minutes
            logger.info(f"Différence de durée trop importante : {duration_diff:.1f}s > 300s")
            return 0.0

        # Compare les hashs frame par frame
        total_bits = 0
        matching_bits = 0

        # Prend le minimum de frames entre les deux vidéos
        min_frames = min(len(hash1), len(hash2))

        for frame_idx in range(min_frames):
            frame1 = hash1[frame_idx]
            frame2 = hash2[frame_idx]

            # Compare chaque bit des frames
            for i in range(8):
                for j in range(8):
                    total_bits += 1
                    if frame1[i][j] == frame2[i][j]:
                        matching_bits += 1

        # Calcule le pourcentage de similarité
        similarity = (matching_bits / total_bits) * 100 if total_bits > 0 else 0
        logger.debug(f"Similarité entre {video1_path} et {video2_path} : {similarity:.2f}%")
        
        return similarity
