import cv2
import numpy as np
import os
import json
from src.core.logger import Logger
from enum import Enum

logger = Logger.get_logger('DuplicateFinder.VideoHasher')

class HashMethod(Enum):
    """Méthodes de hachage disponibles"""
    PHASH = "pHash"

class VideoHasher:
    """Classe pour calculer et comparer les hashs de vidéos"""
    
    # Constantes de configuration
    MIN_FRAMES = 3
    DEFAULT_SIMILARITY_THRESHOLD = 0.90  # 90% de similarité par défaut
    DEFAULT_STD_THRESHOLD = 0.1
    
    def __init__(self, method=HashMethod.PHASH.value):
        """Initialise le hasher de vidéos"""
        self.method = method if isinstance(method, str) else method.value
        self.plugin_dir = os.path.dirname(__file__)
        self.json_file = os.path.join(self.plugin_dir, 'video_hashes.json')
        self.hashes = {
            "pHash": {},  # Cache pour pHash uniquement
        }
        self.load_hashes()
        
        logger.debug(f"VideoHasher initialisé")
        if self.hashes:
            logger.info(f"{len(self.hashes['pHash'])} empreintes chargées")

    def load_hashes(self):
        """Charge les hashs depuis le fichier JSON"""
        try:
            if os.path.exists(self.json_file):
                with open(self.json_file, 'r') as f:
                    self.hashes = json.load(f)
        except Exception as e:
            logger.error(f"Erreur lors du chargement des hashs: {str(e)}")
            self.hashes = {"pHash": {}}

    def save_hashes(self):
        """Sauvegarde les hashs dans un fichier JSON"""
        try:
            with open(self.json_file, 'w') as f:
                json.dump(self.hashes, f, indent=4)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des hashs : {e}")

    def clear_cache(self):
        """Efface le cache des empreintes"""
        self.hashes = {"pHash": {}}
        if os.path.exists(self.json_file):
            os.remove(self.json_file)
        logger.info("Cache effacé")

    def compute_frame_hash(self, frame):
        """Calcule l'empreinte d'une frame avec pHash"""
        try:
            # 1. Conversion en niveaux de gris et redimensionnement
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
            
            # 2. Application d'un flou gaussien
            blurred = cv2.GaussianBlur(resized, (3, 3), 0)
            
            # 3. Calcul de la DCT
            dct = cv2.dct(np.float32(blurred))
            dct_low = dct[:8, :8]
            
            # 4. Calcul du hash binaire avec seuil adaptatif
            threshold = np.median(dct_low)
            return dct_low > threshold
                
        except Exception as e:
            logger.error(f"Erreur lors du calcul de l'empreinte d'une frame : {e}")
            return None

    def compute_similarity(self, hash1, hash2):
        """Calcule la similarité entre deux hashs de frames"""
        try:
            # Convertit les hashs en vecteurs binaires
            bin1 = hash1.flatten()
            bin2 = hash2.flatten()
            
            # Calcule la distance de Hamming (nombre de bits différents)
            # xor donne 1 quand les bits sont différents
            hamming_dist = np.sum(np.logical_xor(bin1, bin2))
            
            # Convertit en similarité (1 - distance normalisée)
            total_bits = bin1.size
            return 1.0 - (hamming_dist / total_bits)
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul de la similarité : {e}")
            return 0.0

    def compute_video_hash(self, video_path):
        """Calcule l'empreinte d'une vidéo"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("Impossible d'ouvrir la vidéo")

            # Récupère les informations de la vidéo
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
            duration = total_frames / fps
            
            # Sélectionne les frames à analyser
            frame_indices = [500, 1000, 1500, 2000, 2500]
            frame_indices = [idx for idx in frame_indices if idx < total_frames]
            
            hashes = []
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret:
                    frame_hash = self.compute_frame_hash(frame)
                    if frame_hash is not None:
                        hashes.append(frame_hash)
            
            cap.release()
            
            if len(hashes) < self.MIN_FRAMES:
                raise Exception(f"Pas assez de frames valides ({len(hashes)})")
            
            # Sauvegarde dans le cache
            hash_array = np.stack(hashes)
            self.hashes[self.method][video_path] = {
                'hash': hash_array.tolist(),
                'duration': duration
            }
            self.save_hashes()
            
            return hash_array, duration
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul de l'empreinte : {e}")
            return None, 0

    def has_hash(self, file_path):
        """Vérifie si un fichier a déjà une empreinte dans le cache"""
        return file_path in self.hashes[self.method]

    def compare_videos(self, video1_path, video2_path, duration_minutes=0, similarity_threshold=None):
        """Compare deux vidéos et retourne leur pourcentage de similarité"""
        try:
            # Récupère ou calcule les hashs
            if not self.has_hash(video1_path):
                hash1, duration1 = self.compute_video_hash(video1_path)
            else:
                hash1 = np.array(self.hashes[self.method][video1_path]['hash'])
                duration1 = self.hashes[self.method][video1_path]['duration']
                
            if not self.has_hash(video2_path):
                hash2, duration2 = self.compute_video_hash(video2_path)
            else:
                hash2 = np.array(self.hashes[self.method][video2_path]['hash'])
                duration2 = self.hashes[self.method][video2_path]['duration']
            
            if hash1 is None or hash2 is None:
                return 0.0
                
            # Vérifie la différence de durée
            if duration_minutes > 0:
                if abs(duration1 - duration2) > duration_minutes * 60:
                    return 0.0
            
            # Compare les frames en ignorant la première et la dernière
            similarities = []
            min_frames = min(len(hash1), len(hash2))
            
            for i in range(1, min_frames - 1):
                similarity = self.compute_similarity(hash1[i], hash2[i])
                similarities.append(similarity)
            
            # Convertit en array numpy pour les calculs
            similarities = np.array(similarities)
            
            # Enlève les outliers (valeurs aberrantes)
            # Utilise la médiane et l'écart absolu médian (MAD) qui sont plus robustes que moyenne/std
            median = np.median(similarities)
            mad = np.median(np.abs(similarities - median))
            
            if mad > 0:  # Si MAD est 0, pas d'outliers
                modified_z_scores = 0.6745 * (similarities - median) / mad
                similarities = similarities[np.abs(modified_z_scores) < 3.5]
            
            # Vérifie qu'il reste assez de frames après filtrage
            if len(similarities) < self.MIN_FRAMES:
                return 0.0
            
            # Calcule la similarité finale
            mean_similarity = np.mean(similarities)
            std_similarity = np.std(similarities)
            
            # Vérifie si la similarité dépasse le seuil
            threshold = similarity_threshold if similarity_threshold is not None else self.DEFAULT_SIMILARITY_THRESHOLD
            if mean_similarity >= threshold and std_similarity <= self.DEFAULT_STD_THRESHOLD:
                return mean_similarity * 100
            return 0.0
            
        except Exception as e:
            logger.error(f"Erreur lors de la comparaison : {e}")
            return 0.0