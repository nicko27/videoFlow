
@contextmanager
def safe_video_capture(video_path, timeout=30):
    """Gestionnaire de contexte sécurisé pour VideoCapture"""
    cap = None
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Impossible d'ouvrir la vidéo: {video_path}")
        
        # Vérifier si la vidéo est valide
        ret, frame = cap.read()
        if not ret:
            raise ValueError(f"Impossible de lire la première frame: {video_path}")
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Revenir au début
        
        yield cap
    except Exception as e:
        logger.error(f"Erreur VideoCapture {video_path}: {e}")
        raise
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception as e:
                logger.error(f"Erreur libération VideoCapture: {e}")


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
        self.duration = 0  # Durée maximale en secondes (0 = pas de limite)
        self.load_hashes()
        
        # Configurer les paramètres de lecture vidéo
        try:
            # Essayer de configurer les paramètres OpenCV pour améliorer la compatibilité
            # Ces paramètres peuvent aider avec certains fichiers problématiques
            cv2.setNumThreads(4)  # Utiliser 4 threads pour le décodage
        except Exception as e:
            logger.warning(f"Impossible de configurer les paramètres OpenCV: {str(e)}")
        
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
            # Vérifie si le fichier existe
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Le fichier {video_path} n'existe pas")
                
            # Vérifie si le fichier a été modifié depuis le dernier calcul
            if video_path in self.hashes[self.method]:
                last_modified = os.path.getmtime(video_path)
                if 'last_modified' in self.hashes[self.method][video_path]:
                    if last_modified <= self.hashes[self.method][video_path]['last_modified']:
                        # Le fichier n'a pas été modifié, on retourne le hash existant
                        hash_data = np.array(self.hashes[self.method][video_path]['hash'])
                        duration = self.hashes[self.method][video_path]['duration']
                        logger.debug(f"Utilisation du hash existant pour {video_path}")
                        return hash_data, duration

            # cap = cv2.VideoCapture(video_path)  # Remplacé par safe_video_capture
            if not cap.isOpened():
                raise Exception(f"Impossible d'ouvrir la vidéo: {video_path}")
                
            # Vérifie si on peut lire au moins une frame
            ret, frame = cap.read()
            if not ret or frame is None:
                cap.release()
                raise Exception(f"Vidéo corrompue ou format non supporté: {video_path}")
                
            # Remet la position à 0
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            # Récupère les informations de la vidéo
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
            
            # Si le nombre de frames est invalide, essayons de l'estimer
            if total_frames <= 0:
                logger.warning(f"Nombre de frames invalide pour {video_path}, estimation manuelle")
                # Essayons de lire quelques frames pour estimer la durée
                sample_frames = 0
                max_samples = 100
                while ret and sample_frames < max_samples:
                    ret, _ = cap.read()
                    if ret:
                        sample_frames += 1
                
                if sample_frames > 0:
                    total_frames = sample_frames
                    logger.info(f"Estimation: au moins {sample_frames} frames dans {video_path}")
                else:
                    cap.release()
                    raise Exception(f"Impossible de lire des frames de {video_path}")
                    
            duration = total_frames / fps
            
            # Sélectionne les frames à analyser en fonction de la durée
            # Pour les vidéos courtes, on prend moins de frames
            if total_frames < 1000:
                # Vidéo courte: prendre des frames à 10%, 30%, 50%, 70%, 90%
                frame_indices = [
                    int(total_frames * 0.1),
                    int(total_frames * 0.3),
                    int(total_frames * 0.5),
                    int(total_frames * 0.7),
                    int(total_frames * 0.9)
                ]
            else:
                # Vidéo longue: prendre des frames à intervalles réguliers
                num_samples = min(10, total_frames // 500)  # Max 10 échantillons
                frame_indices = [int(i * total_frames / num_samples) for i in range(num_samples)]
                
            # S'assurer que les indices sont valides et uniques
            frame_indices = sorted(set([max(0, min(idx, total_frames - 1)) for idx in frame_indices if idx < total_frames]))
            
            # Si on a moins de 3 indices, ajoutons-en quelques-uns
            if len(frame_indices) < self.MIN_FRAMES:
                logger.warning(f"Pas assez d'indices de frames pour {video_path}, ajout d'indices supplémentaires")
                # Réinitialiser la position
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                # Lire les 5 premières frames
                additional_indices = []
                for i in range(min(5, total_frames)):
                    ret, _ = cap.read()
                    if ret:
                        additional_indices.append(i)
                
                # Ajouter les nouveaux indices
                frame_indices.extend(additional_indices)
                frame_indices = sorted(set(frame_indices))
                logger.info(f"Nouveaux indices: {frame_indices}")
            
            hashes = []
            error_count = 0
            max_errors = 5
            
            for frame_idx in frame_indices:
                try:
                    # Essayer de positionner à l'index spécifié
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    
                    if ret and frame is not None:
                        frame_hash = self.compute_frame_hash(frame)
                        if frame_hash is not None:
                            hashes.append(frame_hash)
                    else:
                        error_count += 1
                        logger.warning(f"Impossible de lire la frame {frame_idx} de {video_path}")
                        
                        if error_count >= max_errors:
                            logger.error(f"Trop d'erreurs de lecture pour {video_path}")
                            break
                except Exception as e:
                    error_count += 1
                    logger.error(f"Erreur lors de la lecture de la frame {frame_idx}: {str(e)}")
                    
                    if error_count >= max_errors:
                        logger.error(f"Trop d'erreurs de lecture pour {video_path}")
                        break
            
            cap.release()
            
            if len(hashes) < self.MIN_FRAMES:
                raise Exception(f"Pas assez de frames valides ({len(hashes)}/{len(frame_indices)})")
            
            # Sauvegarde dans le cache
            hash_array = np.stack(hashes)
            self.hashes[self.method][video_path] = {
                'hash': hash_array.tolist(),
                'duration': duration,
                'last_modified': os.path.getmtime(video_path),
                'frame_indices': frame_indices
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