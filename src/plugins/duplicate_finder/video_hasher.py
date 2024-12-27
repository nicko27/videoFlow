import os
import cv2
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Augmenter la limite de tentatives de lecture pour OpenCV
os.environ['OPENCV_FFMPEG_READ_ATTEMPTS'] = '10000'

class VideoHasher:
    def __init__(self, precision_level: int = 3):
        """
        Initialise le hash de vidéo avec un niveau de précision
        :param precision_level: 1 (basse), 2 (moyenne), 3 (haute)
        """
        self.precision_level = precision_level
        self.hash_size = {1: 32, 2: 64, 3: 128}[precision_level]
        self.threshold = {1: 12, 2: 8, 3: 4}[precision_level]

    def compute_frame_hash(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Calcule le hash perceptuel d'une image"""
        try:
            # Convertir en niveaux de gris
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Redimensionner
            resized = cv2.resize(gray, (self.hash_size, self.hash_size))
            
            # Calculer la DCT
            dct = cv2.dct(np.float32(resized))
            
            # Prendre le coin supérieur gauche
            dct_low = dct[:8, :8]
            
            # Calculer la moyenne (sans le premier terme)
            med = np.median(dct_low[1:])
            
            # Générer le hash binaire
            return dct_low > med
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du hash de frame: {e}")
            return None

    def compute_video_hash(self, video_path: str) -> Optional[List[np.ndarray]]:
        """Calcule les hashs d'une vidéo"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Impossible d'ouvrir la vidéo: {video_path}")
                return None

            # Obtenir les informations de la vidéo
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            # Calculer l'intervalle pour obtenir 6 frames par minute
            interval = max(1, int(fps * 10))  # Une frame toutes les 10 secondes
            frame_positions = range(0, total_frames, interval)

            hashes = []
            for pos in frame_positions:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
                ret, frame = cap.read()
                if ret:
                    frame_hash = self.compute_frame_hash(frame)
                    if frame_hash is not None:
                        hashes.append(frame_hash)

            cap.release()
            return hashes if hashes else None

        except Exception as e:
            logger.error(f"Erreur lors du calcul du hash vidéo {video_path}: {e}")
            return None

    def are_similar(self, hash1: List[np.ndarray], hash2: List[np.ndarray]) -> bool:
        """Compare deux hashs de vidéos"""
        try:
            if not hash1 or not hash2:
                return False

            # Prendre le même nombre de frames pour la comparaison
            min_frames = min(len(hash1), len(hash2))
            hash1 = hash1[:min_frames]
            hash2 = hash2[:min_frames]

            # Calculer la différence moyenne entre les frames
            differences = []
            for h1, h2 in zip(hash1, hash2):
                diff = np.count_nonzero(h1 != h2)
                differences.append(diff)

            # Calculer la différence moyenne
            avg_diff = np.mean(differences) if differences else float('inf')
            
            logger.debug(f"Différence moyenne entre les hashs: {avg_diff}")
            return avg_diff < self.threshold

        except Exception as e:
            logger.error(f"Erreur lors de la comparaison des hashs: {e}")
            return False
