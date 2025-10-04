import cv2
import numpy as np
import os
import time
from datetime import datetime
from enum import Enum
from .database_manager import VideoDatabase
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.VideoHasher')

class HashMethod(Enum):
    """Méthodes de hachage disponibles"""
    PHASH = "pHash"
    DHASH = "dHash"  # Plus rapide que pHash
    AHASH = "aHash"  # Le plus rapide

class VideoHasher:
    """VideoHasher optimisé avec positions absolues et cache mémoire permanent"""
    
    def __init__(self, method=HashMethod.PHASH.value):
        self.method = method if isinstance(method, str) else method.value
        self.plugin_dir = os.path.dirname(__file__)
        self.db = VideoDatabase()
        
        # Cache mémoire PERMANENT pour toute la session
        self.hash_cache = {}  # file_path -> (hash, duration, mtime)
        self.comparison_cache = {}  # (file1, file2) -> similarity
        
        # Positions ABSOLUES fixes pour cohérence
        # Frame indices exacts pour toutes les vidéos
        self.absolute_positions = [
            30,    # 1 seconde à 30fps
            150,   # 5 secondes
            300,   # 10 secondes
            600,   # 20 secondes
            900,   # 30 secondes
            1500,  # 50 secondes
            2100,  # 70 secondes
            3000   # 100 secondes
        ]
        
        # Précharge tous les hashs existants en mémoire au démarrage
        self._preload_cache()
        
        logger.debug(f"VideoHasher initialisé avec cache mémoire permanent")

    def _preload_cache(self):
        """Précharge tous les hashs de la DB en mémoire au démarrage"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Charge d'abord les hashs
                cursor.execute('''
                    SELECT file_path, hash_data, duration, modification_time 
                    FROM video_files
                ''')
                
                loaded_hashes = 0
                for row in cursor.fetchall():
                    file_path, hash_blob, duration, mtime = row
                    if os.path.exists(file_path):
                        import pickle
                        hash_data = pickle.loads(hash_blob)
                        self.hash_cache[file_path] = {
                            'hash': hash_data,
                            'duration': duration,
                            'mtime': mtime
                        }
                        loaded_hashes += 1
                
                # Charge ensuite les comparaisons (limite à 50k pour éviter l'overflow mémoire)
                cursor.execute('''
                    SELECT v1.file_path, v2.file_path, c.similarity
                    FROM comparisons c
                    JOIN video_files v1 ON c.file1_id = v1.id
                    JOIN video_files v2 ON c.file2_id = v2.id
                    ORDER BY c.created_at DESC
                    LIMIT 50000
                ''')
                
                loaded_comparisons = 0
                for row in cursor.fetchall():
                    file1, file2, similarity = row
                    cache_key = tuple(sorted([file1, file2]))
                    self.comparison_cache[cache_key] = similarity
                    loaded_comparisons += 1
                
                if loaded_hashes > 0 or loaded_comparisons > 0:
                    logger.info(f"Cache préchargé: {loaded_hashes} hashs, {loaded_comparisons} comparaisons")
                    
        except Exception as e:
            logger.debug(f"Préchargement cache: {e}")

    def compute_frame_hash(self, frame):
        """Calcule l'empreinte d'une frame - version optimisée"""
        try:
            # Conversion en gris directement
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if self.method == "pHash":
                resized = cv2.resize(gray, (32, 32))
                dct = cv2.dct(np.float32(resized))
                dct_low = dct[:8, :8]
                avg = (dct_low[1:, :].mean() + dct_low[0, 1:].mean()) / 2
                return dct_low > avg
                
            elif self.method == "dHash":
                # Difference Hash - plus rapide
                resized = cv2.resize(gray, (9, 8))
                diff = resized[:, 1:] > resized[:, :-1]
                return diff
                
            elif self.method == "aHash":
                # Average Hash - le plus rapide
                resized = cv2.resize(gray, (8, 8))
                avg = resized.mean()
                return resized > avg
                
        except Exception as e:
            logger.error(f"Erreur calcul hash frame: {e}")
            return None

    def compute_video_hash_fast(self, video_path):
        """Version optimisée du calcul de hash avec positions absolues"""
        try:
            # 1. Check cache mémoire (ultra rapide)
            if video_path in self.hash_cache:
                cache_entry = self.hash_cache[video_path]
                current_mtime = os.path.getmtime(video_path)
                # Vérifie si le fichier a changé
                if abs(current_mtime - cache_entry['mtime']) < 1:
                    return cache_entry['hash'], cache_entry['duration']
            
            # 2. Calcul du hash nécessaire
            cv2.setLogLevel(0)
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise Exception("Impossible d'ouvrir la vidéo")
            
            try:
                # Récupère les infos de base
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                # Validation rapide
                if total_frames <= 0:
                    # Estimation rapide sans parcourir toute la vidéo
                    count = 0
                    while count < 500 and cap.grab():  # Max 500 frames
                        count += 1
                    total_frames = count * 10  # Estimation
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                
                if fps <= 0:
                    fps = 25.0
                
                duration = total_frames / fps
                
                # Filtre les positions selon la longueur de la vidéo
                valid_positions = [pos for pos in self.absolute_positions if pos < total_frames]
                
                # Minimum 3 positions, maximum 8
                if len(valid_positions) < 3:
                    # Pour les très courtes vidéos, positions adaptées
                    if total_frames < 90:
                        valid_positions = [0, total_frames // 2, total_frames - 1]
                    else:
                        valid_positions = [0, 30, 60, total_frames - 1]
                
                hashes = []
                
                for frame_idx in valid_positions:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    
                    if ret and frame is not None:
                        frame_hash = self.compute_frame_hash(frame)
                        if frame_hash is not None:
                            hashes.append(frame_hash)
                    else:
                        # Si échec, essaie la frame suivante
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx + 1)
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            frame_hash = self.compute_frame_hash(frame)
                            if frame_hash is not None:
                                hashes.append(frame_hash)
                
                if len(hashes) < 2:
                    raise Exception(f"Seulement {len(hashes)} frames lues")
                
                final_hash = np.stack(hashes)
                
                # Met à jour TOUS les caches
                current_mtime = os.path.getmtime(video_path)
                self.hash_cache[video_path] = {
                    'hash': final_hash,
                    'duration': duration,
                    'mtime': current_mtime
                }
                
                # Stocke aussi en DB pour persistance
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                self.db.store_video_hash(
                    video_path, 
                    final_hash, 
                    duration,
                    width=width,
                    height=height,
                    hash_method=self.method,
                    frames_indices=valid_positions,
                    sampling_method="absolute_optimized"
                )
                
                logger.info(f"Hash créé: {os.path.basename(video_path)} ({len(hashes)} frames aux positions {valid_positions[:3]}...)")
                return final_hash, duration
                
            finally:
                cap.release()
                cv2.setLogLevel(1)
                
        except Exception as e:
            logger.error(f"Erreur hash {os.path.basename(video_path)}: {e}")
            self.db.mark_file_as_corrupted(video_path, str(e))
            raise

    def compute_video_hash(self, video_path, sample_interval=500):
        """Méthode principale"""
        return self.compute_video_hash_fast(video_path)

    def compare_videos_cached(self, video1_path: str, video2_path: str) -> float:
        """Compare deux vidéos avec cache mémoire permanent"""
        
        # 1. Check cache mémoire de comparaison (instantané)
        cache_key = tuple(sorted([video1_path, video2_path]))
        if cache_key in self.comparison_cache:
            return self.comparison_cache[cache_key]
        
        # 2. Check cache DB (rapide)
        cached_result = self.db.get_cached_comparison(video1_path, video2_path)
        if cached_result is not None:
            # Met en cache mémoire pour la prochaine fois
            self.comparison_cache[cache_key] = cached_result
            return cached_result
        
        # 3. Comparaison réelle nécessaire
        start_time = time.time()
        
        try:
            # Récupère les hashs (depuis cache mémoire si possible)
            hash1, duration1 = self.compute_video_hash_fast(video1_path)
            hash2, duration2 = self.compute_video_hash_fast(video2_path)
            
            # Comparaison simple mais efficace
            min_frames = min(len(hash1), len(hash2))
            
            if min_frames == 0:
                similarity = 0.0
            else:
                # Compare bit à bit
                total_bits = 0
                matching_bits = 0
                
                for i in range(min_frames):
                    frame1 = hash1[i]
                    frame2 = hash2[i]
                    
                    # Comparaison optimisée avec numpy
                    matches = np.sum(frame1 == frame2)
                    matching_bits += matches
                    total_bits += frame1.size
                
                similarity = (matching_bits / total_bits * 100) if total_bits > 0 else 0
            
            # Met en cache PARTOUT
            computation_time = time.time() - start_time
            
            # Cache mémoire
            self.comparison_cache[cache_key] = similarity
            
            # Cache DB
            self.db.store_comparison(
                video1_path, 
                video2_path, 
                similarity,
                comparison_method="cached_absolute",
                computation_time=computation_time
            )
            
            return similarity
            
        except Exception as e:
            logger.error(f"Erreur comparaison: {e}")
            # Met en cache l'échec aussi
            self.comparison_cache[cache_key] = 0.0
            return 0.0

    def compare_videos_optimized(self, video1_path: str, video2_path: str) -> float:
        """Alias pour la méthode cachée"""
        return self.compare_videos_cached(video1_path, video2_path)

    def compare_videos(self, video1_path: str, video2_path: str) -> float:
        """Méthode principale de comparaison"""
        return self.compare_videos_cached(video1_path, video2_path)

    def get_cache_stats(self):
        """Retourne les statistiques du cache mémoire"""
        return {
            'hash_cache_size': len(self.hash_cache),
            'comparison_cache_size': len(self.comparison_cache),
            'total_memory_items': len(self.hash_cache) + len(self.comparison_cache)
        }

    def clear_memory_cache(self):
        """Vide uniquement le cache mémoire (garde la DB)"""
        self.hash_cache.clear()
        self.comparison_cache.clear()
        logger.info("Cache mémoire vidé")

    def clear_cache(self):
        """Vide tous les caches (mémoire + DB)"""
        self.clear_memory_cache()
        return self.db.clear_all_data()

    def preload_comparisons_batch(self, file_pairs):
        """Précharge un batch de comparaisons depuis la DB avec limite"""
        try:
            # Limite le préchargement pour éviter l'overflow mémoire
            max_preload = 5000
            if len(file_pairs) > max_preload:
                logger.debug(f"Préchargement limité à {max_preload} paires sur {len(file_pairs)}")
                file_pairs = file_pairs[:max_preload]
            
            loaded = 0
            for file1, file2 in file_pairs:
                cache_key = tuple(sorted([file1, file2]))
                if cache_key not in self.comparison_cache:
                    result = self.db.get_cached_comparison(file1, file2)
                    if result is not None:
                        self.comparison_cache[cache_key] = result
                        loaded += 1
            
            if loaded > 0:
                logger.debug(f"Préchargé {loaded} comparaisons en mémoire")
                
        except Exception as e:
            logger.error(f"Erreur préchargement comparaisons: {e}")

    # Méthodes de compatibilité
    def has_hash(self, file_path):
        # Check cache mémoire d'abord (instantané)
        if file_path in self.hash_cache:
            current_mtime = os.path.getmtime(file_path)
            cache_mtime = self.hash_cache[file_path]['mtime']
            if abs(current_mtime - cache_mtime) < 1:
                return True
        return not self.db.file_needs_reanalysis(file_path)
    
    def is_pair_ignored(self, file1, file2):
        return self.db.is_pair_ignored(file1, file2)
    
    def add_ignored_pair(self, file1, file2):
        return self.db.add_ignored_pair(file1, file2, reason="user_choice")
    
    def get_cached_comparison(self, file1, file2):
        # Check mémoire d'abord
        cache_key = tuple(sorted([file1, file2]))
        if cache_key in self.comparison_cache:
            return self.comparison_cache[cache_key]
        return self.db.get_cached_comparison(file1, file2)
    
    def get_statistics(self):
        db_stats = self.db.get_statistics()
        cache_stats = self.get_cache_stats()
        return {**db_stats, **cache_stats}

    # Optimisations supplémentaires
    def quick_similarity_test(self, file1, file2):
        """Test rapide avec une seule frame à position fixe"""
        try:
            # Position absolue fixe pour cohérence
            test_position = 300  # 10 secondes
            
            cv2.setLogLevel(0)
            cap1 = cv2.VideoCapture(file1)
            cap2 = cv2.VideoCapture(file2)
            
            if not cap1.isOpened() or not cap2.isOpened():
                return -1
            
            # Ajuste si nécessaire
            total1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
            total2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
            
            pos1 = min(test_position, total1 - 1) if total1 > 0 else 0
            pos2 = min(test_position, total2 - 1) if total2 > 0 else 0
            
            cap1.set(cv2.CAP_PROP_POS_FRAMES, pos1)
            cap2.set(cv2.CAP_PROP_POS_FRAMES, pos2)
            
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()
            
            cap1.release()
            cap2.release()
            cv2.setLogLevel(1)
            
            if not ret1 or not ret2:
                return -1
            
            hash1 = self.compute_frame_hash(frame1)
            hash2 = self.compute_frame_hash(frame2)
            
            if hash1 is None or hash2 is None:
                return -1
            
            # Calcul de similarité
            similarity = np.sum(hash1 == hash2) / hash1.size * 100
            
            return similarity
            
        except Exception:
            return -1