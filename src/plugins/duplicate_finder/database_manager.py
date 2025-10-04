import sqlite3
import os
import json
import pickle
import hashlib
from datetime import datetime
import numpy as np
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.DatabaseManager')

class VideoDatabase:
    """Gestionnaire de base de données optimisé pour les hashs et comparaisons de vidéos - Version avec migration corrigée"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            # Place la DB dans le même dossier que le plugin
            plugin_dir = os.path.dirname(__file__)
            db_path = os.path.join(plugin_dir, 'video_duplicates.db')
        
        self.db_path = db_path
        self._initialized = False  # Flag pour éviter les vérifications répétées
        self._tables_exist = {}  # Cache pour l'existence des tables
        self._ensure_database_exists()
        logger.info(f"Base de données initialisée: {self.db_path}")
    
    def _ensure_database_exists(self):
        """S'assure que la base de données et ses tables existent - UNE SEULE FOIS"""
        if self._initialized:
            return
            
        try:
            # Crée le répertoire parent si nécessaire
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            # Initialise la structure
            self.init_database()
            self._initialized = True
            
            # Marque toutes les tables comme existantes
            self._tables_exist = {
                'video_files': True,
                'comparisons': True,
                'ignored_pairs': True,
                'corrupted_files': True,
                'found_duplicates': True
            }
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la DB: {e}")
            raise
    
    def init_database(self):
        """Initialise la structure de la base de données - AVEC MIGRATION CORRIGÉE"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Active les optimisations SQLite
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.execute("PRAGMA foreign_keys=ON")
                
                # ÉTAPE 1: Crée les tables de base SANS ignore_type
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS video_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT UNIQUE NOT NULL,
                        file_name TEXT NOT NULL,
                        file_size INTEGER,
                        modification_time REAL,
                        duration REAL,
                        width INTEGER,
                        height INTEGER,
                        hash_method TEXT,
                        hash_data BLOB,
                        frames_indices TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS comparisons (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file1_id INTEGER,
                        file2_id INTEGER,
                        similarity REAL,
                        comparison_method TEXT,
                        is_early_exit BOOLEAN DEFAULT 0,
                        computation_time REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (file1_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        FOREIGN KEY (file2_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        UNIQUE(file1_id, file2_id)
                    )
                ''')
                
                # ÉTAPE 2: Crée la table ignored_pairs SANS ignore_type d'abord
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ignored_pairs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file1_id INTEGER,
                        file2_id INTEGER,
                        reason TEXT DEFAULT 'user_choice',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (file1_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        FOREIGN KEY (file2_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        UNIQUE(file1_id, file2_id)
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS corrupted_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT UNIQUE NOT NULL,
                        error_message TEXT,
                        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS found_duplicates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file1_id INTEGER,
                        file2_id INTEGER,
                        similarity REAL,
                        status TEXT DEFAULT 'pending',
                        action_taken TEXT,
                        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP,
                        FOREIGN KEY (file1_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        FOREIGN KEY (file2_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        UNIQUE(file1_id, file2_id)
                    )
                ''')
                
                # ÉTAPE 3: Vérifie et ajoute la colonne ignore_type si nécessaire
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'ignore_type' not in columns:
                    logger.info("Ajout de la colonne ignore_type à la table ignored_pairs")
                    cursor.execute("ALTER TABLE ignored_pairs ADD COLUMN ignore_type TEXT DEFAULT 'permanent'")
                    
                    # Met à jour les entrées existantes
                    cursor.execute("UPDATE ignored_pairs SET ignore_type = 'permanent' WHERE ignore_type IS NULL")
                    
                    logger.info("Migration de la base de données terminée")
                
                # ÉTAPE 4: Crée les index
                index_commands = [
                    "CREATE INDEX IF NOT EXISTS idx_file_path ON video_files(file_path)",
                    "CREATE INDEX IF NOT EXISTS idx_file_size ON video_files(file_size)",
                    "CREATE INDEX IF NOT EXISTS idx_duration ON video_files(duration)",
                    "CREATE INDEX IF NOT EXISTS idx_modification_time ON video_files(modification_time)",
                    "CREATE INDEX IF NOT EXISTS idx_comparison_files ON comparisons(file1_id, file2_id)",
                    "CREATE INDEX IF NOT EXISTS idx_similarity ON comparisons(similarity)",
                    "CREATE INDEX IF NOT EXISTS idx_corrupted_path ON corrupted_files(file_path)",
                    "CREATE INDEX IF NOT EXISTS idx_duplicates_status ON found_duplicates(status)",
                    "CREATE INDEX IF NOT EXISTS idx_duplicates_files ON found_duplicates(file1_id, file2_id)",
                    "CREATE INDEX IF NOT EXISTS idx_ignored_pairs ON ignored_pairs(file1_id, file2_id)",
                    "CREATE INDEX IF NOT EXISTS idx_ignored_type ON ignored_pairs(ignore_type)"
                ]
                
                for cmd in index_commands:
                    cursor.execute(cmd)
                
                conn.commit()
                logger.debug("Structure de base de données créée/vérifiée avec migration")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
            raise
    
    def _table_exists(self, table_name):
        """Vérifie si une table existe - AVEC CACHE"""
        # Utilise le cache en premier
        if table_name in self._tables_exist:
            return self._tables_exist[table_name]
            
        # Sinon vérifie une seule fois
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                ''', (table_name,))
                exists = cursor.fetchone() is not None
                self._tables_exist[table_name] = exists
                return exists
        except Exception:
            return False
    
    def get_connection(self):
        """Retourne une connexion à la base optimisée"""
        conn = sqlite3.connect(self.db_path)
        # Active les optimisations pour cette connexion
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn
    
    def file_needs_reanalysis(self, file_path):
        """Vérifie si un fichier a été modifié - OPTIMISÉ"""
        if not os.path.exists(file_path):
            return True
            
        try:
            current_mtime = os.path.getmtime(file_path)
            current_size = os.path.getsize(file_path)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT modification_time, file_size FROM video_files 
                    WHERE file_path = ?
                ''', (file_path,))
                
                result = cursor.fetchone()
                if not result:
                    return True  # Fichier pas en base
                
                stored_mtime, stored_size = result
                
                # Vérifie si modifié (tolérance de 1 seconde pour les systèmes de fichiers)
                return (abs(current_mtime - stored_mtime) > 1.0 or 
                       current_size != stored_size)
                
        except Exception as e:
            logger.error(f"Erreur vérification modification {file_path}: {e}")
            return True
    
    def store_video_hash(self, file_path, hash_data, duration, width=None, height=None, 
                        hash_method="pHash", frames_indices=None, sampling_method=None):
        """Stocke l'empreinte d'une vidéo - OPTIMISÉ"""
        try:
            file_stats = os.stat(file_path)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Sérialise le hash numpy en binaire
                hash_blob = pickle.dumps(hash_data)
                frames_json = json.dumps(frames_indices) if frames_indices else None
                
                # Combine la méthode de hash et d'échantillonnage si fournie
                full_method = hash_method
                if sampling_method:
                    full_method += f"_{sampling_method}"
                
                cursor.execute('''
                    INSERT OR REPLACE INTO video_files 
                    (file_path, file_name, file_size, modification_time, duration, 
                     width, height, hash_method, hash_data, frames_indices, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    file_path,
                    os.path.basename(file_path),
                    file_stats.st_size,
                    file_stats.st_mtime,
                    duration,
                    width,
                    height,
                    full_method,
                    hash_blob,
                    frames_json
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erreur stockage hash {file_path}: {e}")
            return False
    
    def get_video_hash(self, file_path):
        """Récupère l'empreinte d'une vidéo - OPTIMISÉ"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT hash_data, duration, frames_indices FROM video_files 
                    WHERE file_path = ?
                ''', (file_path,))
                
                result = cursor.fetchone()
                if result:
                    hash_blob, duration, frames_json = result
                    
                    # Désérialise le hash
                    hash_data = pickle.loads(hash_blob)
                    frames_indices = json.loads(frames_json) if frames_json else None
                    
                    return {
                        'hash': hash_data,
                        'duration': duration,
                        'frames': frames_indices
                    }
                    
        except Exception as e:
            logger.error(f"Erreur récupération hash {file_path}: {e}")
            
        return None
    
    def get_cached_comparison(self, file1_path, file2_path):
        """Récupère un résultat de comparaison - OPTIMISÉ"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Requête optimisée avec index
                cursor.execute('''
                    SELECT c.similarity
                    FROM comparisons c
                    JOIN video_files v1 ON c.file1_id = v1.id
                    JOIN video_files v2 ON c.file2_id = v2.id
                    WHERE (v1.file_path = ? AND v2.file_path = ?)
                       OR (v1.file_path = ? AND v2.file_path = ?)
                ''', (file1_path, file2_path, file2_path, file1_path))
                
                result = cursor.fetchone()
                if result:
                    return result[0]
                    
        except Exception as e:
            logger.error(f"Erreur récupération comparaison: {e}")
            
        return None
    
    def store_comparison(self, file1_path, file2_path, similarity, 
                        comparison_method="optimized", is_early_exit=False, computation_time=0.0):
        """Stocke un résultat de comparaison - OPTIMISÉ avec batch"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Récupère les IDs en une seule requête
                cursor.execute('''
                    SELECT 
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (file1_path, file2_path))
                
                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    return False
                
                file1_id, file2_id = result
                
                # Assure l'ordre pour éviter les doublons
                if file1_id > file2_id:
                    file1_id, file2_id = file2_id, file1_id
                
                cursor.execute('''
                    INSERT OR REPLACE INTO comparisons 
                    (file1_id, file2_id, similarity, comparison_method, is_early_exit, computation_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (file1_id, file2_id, similarity, comparison_method, is_early_exit, computation_time))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erreur stockage comparaison: {e}")
            return False
    
    def is_pair_ignored(self, file1_path, file2_path):
        """Vérifie si une paire est ignorée - CORRIGÉ avec ignore_type"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # CORRECTION: Vérifie seulement les paires ignorées DÉFINITIVEMENT
                # Utilise COALESCE pour gérer les anciennes entrées sans ignore_type
                cursor.execute('''
                    SELECT 1 FROM ignored_pairs ip
                    JOIN video_files v1 ON ip.file1_id = v1.id
                    JOIN video_files v2 ON ip.file2_id = v2.id
                    WHERE (v1.file_path = ? AND v2.file_path = ?)
                       OR (v1.file_path = ? AND v2.file_path = ?)
                    AND COALESCE(ip.ignore_type, 'permanent') = 'permanent'
                    LIMIT 1
                ''', (file1_path, file2_path, file2_path, file1_path))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Erreur vérification paire ignorée: {e}")
            
        return False
    
    def add_ignored_pair(self, file1_path, file2_path, reason="user_choice", ignore_type="permanent"):
        """Ajoute une paire à ignorer - CORRIGÉ avec ignore_type"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Récupère les IDs en une seule requête
                cursor.execute('''
                    SELECT 
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (file1_path, file2_path))
                
                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    logger.warning(f"Fichiers non trouvés en base: {file1_path}, {file2_path}")
                    return False
                
                file1_id, file2_id = result
                
                # Assure l'ordre
                if file1_id > file2_id:
                    file1_id, file2_id = file2_id, file1_id
                
                # Vérifie si ignore_type existe dans la table
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'ignore_type' in columns:
                    cursor.execute('''
                        INSERT OR REPLACE INTO ignored_pairs (file1_id, file2_id, reason, ignore_type)
                        VALUES (?, ?, ?, ?)
                    ''', (file1_id, file2_id, reason, ignore_type))
                else:
                    # Fallback pour anciennes DB
                    cursor.execute('''
                        INSERT OR REPLACE INTO ignored_pairs (file1_id, file2_id, reason)
                        VALUES (?, ?, ?)
                    ''', (file1_id, file2_id, reason))
                
                conn.commit()
                logger.info(f"Paire ignorée ({ignore_type}): {os.path.basename(file1_path)} <-> {os.path.basename(file2_path)}")
                return True
                
        except Exception as e:
            logger.error(f"Erreur ajout paire ignorée: {e}")
            return False
    
    def get_statistics(self):
        """Récupère les statistiques - OPTIMISÉ avec une seule requête"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Vérifie si ignore_type existe
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]
                has_ignore_type = 'ignore_type' in columns
                
                if has_ignore_type:
                    # Version avec ignore_type
                    cursor.execute('''
                        SELECT 
                            (SELECT COUNT(*) FROM video_files) as files_count,
                            (SELECT COUNT(*) FROM comparisons) as comparisons_count,
                            (SELECT COUNT(*) FROM comparisons WHERE is_early_exit = 1) as early_exits,
                            (SELECT COUNT(*) FROM ignored_pairs WHERE COALESCE(ignore_type, 'permanent') = 'permanent') as ignored_permanent,
                            (SELECT COUNT(*) FROM ignored_pairs WHERE ignore_type = 'temporary') as ignored_temporary,
                            (SELECT COUNT(*) FROM ignored_pairs) as ignored_total
                    ''')
                    
                    result = cursor.fetchone()
                    files_count, comparisons_count, early_exits, ignored_perm, ignored_temp, ignored_total = result
                else:
                    # Version sans ignore_type (compatibilité)
                    cursor.execute('''
                        SELECT 
                            (SELECT COUNT(*) FROM video_files) as files_count,
                            (SELECT COUNT(*) FROM comparisons) as comparisons_count,
                            (SELECT COUNT(*) FROM comparisons WHERE is_early_exit = 1) as early_exits,
                            (SELECT COUNT(*) FROM ignored_pairs) as ignored_count
                    ''')
                    
                    result = cursor.fetchone()
                    files_count, comparisons_count, early_exits, ignored_total = result
                    ignored_perm = ignored_total
                    ignored_temp = 0
                
                # Taille de la base
                db_size = os.path.getsize(self.db_path) / 1024 if os.path.exists(self.db_path) else 0
                
                # Calcul du temps économisé (estimé à 2s par comparaison)
                time_saved = comparisons_count * 2
                
                return {
                    'files_count': files_count or 0,
                    'comparisons_count': comparisons_count or 0,
                    'early_exits': early_exits or 0,
                    'ignored_count': ignored_total or 0,
                    'ignored_permanent': ignored_perm or 0,
                    'ignored_temporary': ignored_temp or 0,
                    'db_size_kb': db_size,
                    'time_saved_seconds': time_saved,
                    'early_exit_percentage': (early_exits / comparisons_count * 100) if comparisons_count > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Erreur récupération statistiques: {e}")
            return {
                'files_count': 0,
                'comparisons_count': 0,
                'early_exits': 0,
                'ignored_count': 0,
                'ignored_permanent': 0,
                'ignored_temporary': 0,
                'db_size_kb': 0,
                'time_saved_seconds': 0,
                'early_exit_percentage': 0
            }
    
    def cleanup_missing_files(self):
        """Nettoie la base des fichiers qui n'existent plus"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Récupère tous les fichiers
                cursor.execute('SELECT id, file_path FROM video_files')
                files = cursor.fetchall()
                
                missing_ids = []
                for file_id, file_path in files:
                    if not os.path.exists(file_path):
                        missing_ids.append(file_id)
                
                if missing_ids:
                    # Supprime en une seule transaction
                    placeholders = ','.join('?' * len(missing_ids))
                    
                    # Supprime les comparaisons
                    cursor.execute(f'''
                        DELETE FROM comparisons 
                        WHERE file1_id IN ({placeholders}) OR file2_id IN ({placeholders})
                    ''', missing_ids + missing_ids)
                    
                    # Supprime les paires ignorées
                    cursor.execute(f'''
                        DELETE FROM ignored_pairs 
                        WHERE file1_id IN ({placeholders}) OR file2_id IN ({placeholders})
                    ''', missing_ids + missing_ids)
                    
                    # Supprime les doublons trouvés
                    cursor.execute(f'''
                        DELETE FROM found_duplicates 
                        WHERE file1_id IN ({placeholders}) OR file2_id IN ({placeholders})
                    ''', missing_ids + missing_ids)
                    
                    # Supprime les fichiers
                    cursor.execute(f'DELETE FROM video_files WHERE id IN ({placeholders})', missing_ids)
                    
                    conn.commit()
                    logger.info(f"Nettoyage base: {len(missing_ids)} fichiers supprimés")
                    
                return len(missing_ids)
                
        except Exception as e:
            logger.error(f"Erreur nettoyage base: {e}")
            return 0
    
    def auto_cleanup_on_access(self):
        """Nettoie automatiquement lors des accès si nécessaire"""
        # Nettoie seulement une fois par session
        if not hasattr(self, '_cleaned_this_session'):
            self._cleaned_this_session = True
            removed = self.cleanup_missing_files()
            if removed > 0:
                logger.info(f"Nettoyage automatique: {removed} fichiers manquants supprimés")
    
    def clear_all_data(self):
        """Vide complètement la base de données"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Transaction unique pour tout supprimer
                cursor.executescript('''
                    DELETE FROM comparisons;
                    DELETE FROM ignored_pairs;
                    DELETE FROM corrupted_files;
                    DELETE FROM found_duplicates;
                    DELETE FROM video_files;
                    VACUUM;
                ''')
                
                conn.commit()
                logger.info("Base de données vidée et compactée")
                return True
                
        except Exception as e:
            logger.error(f"Erreur vidage base: {e}")
            return False
    
    def mark_file_as_corrupted(self, file_path, error_message):
        """Marque un fichier comme corrompu"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO corrupted_files (file_path, error_message)
                    VALUES (?, ?)
                ''', (file_path, error_message))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Erreur marquage fichier corrompu: {e}")

    def get_files_needing_analysis(self, file_paths):
        """Retourne les fichiers qui ont besoin d'être analysés - OPTIMISÉ"""
        if not file_paths:
            return []
            
        files_to_analyze = []
        
        # Batch check pour performance
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Récupère tous les fichiers existants en une requête
            placeholders = ','.join('?' * len(file_paths))
            cursor.execute(f'''
                SELECT file_path, modification_time, file_size 
                FROM video_files 
                WHERE file_path IN ({placeholders})
            ''', file_paths)
            
            existing_files = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
        
        # Vérifie chaque fichier
        for file_path in file_paths:
            if not os.path.exists(file_path):
                continue
                
            if file_path not in existing_files:
                files_to_analyze.append(file_path)
            else:
                # Vérifie si modifié
                current_mtime = os.path.getmtime(file_path)
                current_size = os.path.getsize(file_path)
                stored_mtime, stored_size = existing_files[file_path]
                
                if abs(current_mtime - stored_mtime) > 1.0 or current_size != stored_size:
                    files_to_analyze.append(file_path)
        
        return files_to_analyze
    
    def store_found_duplicate(self, file1_path, file2_path, similarity):
        """Stocke un doublon trouvé pour récupération ultérieure"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Récupère les IDs
                cursor.execute('''
                    SELECT 
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (file1_path, file2_path))
                
                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    return False
                
                file1_id, file2_id = result
                
                # Assure l'ordre
                if file1_id > file2_id:
                    file1_id, file2_id = file2_id, file1_id
                
                cursor.execute('''
                    INSERT OR REPLACE INTO found_duplicates 
                    (file1_id, file2_id, similarity, status, detected_at)
                    VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                ''', (file1_id, file2_id, similarity))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erreur stockage doublon trouvé: {e}")
            return False
    
    def get_pending_duplicates(self):
        """Récupère les doublons en attente de traitement"""
        try:
            duplicates = []
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT v1.file_path, v2.file_path, d.similarity, d.id
                    FROM found_duplicates d
                    JOIN video_files v1 ON d.file1_id = v1.id
                    JOIN video_files v2 ON d.file2_id = v2.id
                    WHERE d.status = 'pending'
                    ORDER BY d.similarity DESC, d.detected_at DESC
                ''')
                
                for row in cursor.fetchall():
                    file1, file2, similarity, dup_id = row
                    # Vérifie si les fichiers existent encore
                    if os.path.exists(file1) and os.path.exists(file2):
                        duplicates.append((file1, file2, similarity, dup_id))
                
                return duplicates
                
        except Exception as e:
            logger.error(f"Erreur récupération doublons en attente: {e}")
            return []
    
    def update_duplicate_status(self, dup_id, status, action=None):
        """Met à jour le statut d'un doublon"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE found_duplicates 
                    SET status = ?, action_taken = ?, processed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, action, dup_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erreur mise à jour statut doublon: {e}")
            return False
    
    def clear_processed_duplicates(self):
        """Supprime les doublons déjà traités"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM found_duplicates 
                    WHERE status != 'pending'
                ''')
                
                deleted = cursor.rowcount
                conn.commit()
                
                logger.info(f"Suppression de {deleted} doublons traités")
                return deleted
                
        except Exception as e:
            logger.error(f"Erreur suppression doublons traités: {e}")
            return 0
    
    def get_duplicate_statistics(self):
        """Récupère les statistiques des doublons"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN status = 'processed' THEN 1 ELSE 0 END) as processed,
                        SUM(CASE WHEN action_taken = 'kept_left' THEN 1 ELSE 0 END) as kept_left,
                        SUM(CASE WHEN action_taken = 'kept_right' THEN 1 ELSE 0 END) as kept_right,
                        SUM(CASE WHEN action_taken = 'ignored_permanently' THEN 1 ELSE 0 END) as ignored,
                        SUM(CASE WHEN action_taken = 'ignored_temporarily' THEN 1 ELSE 0 END) as skipped
                    FROM found_duplicates
                ''')
                
                result = cursor.fetchone()
                if result:
                    return {
                        'total': result[0] or 0,
                        'pending': result[1] or 0,
                        'processed': result[2] or 0,
                        'kept_left': result[3] or 0,
                        'kept_right': result[4] or 0,
                        'ignored': result[5] or 0,
                        'skipped': result[6] or 0
                    }
                    
        except Exception as e:
            logger.error(f"Erreur récupération stats doublons: {e}")
            
        return {
            'total': 0,
            'pending': 0,
            'processed': 0,
            'kept_left': 0,
            'kept_right': 0,
            'ignored': 0,
            'skipped': 0
        }
    
    def clear_temporary_ignores(self):
        """Efface toutes les paires ignorées temporairement"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Vérifie si ignore_type existe
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'ignore_type' in columns:
                    cursor.execute('''
                        DELETE FROM ignored_pairs 
                        WHERE ignore_type = 'temporary'
                    ''')
                else:
                    # Si pas de colonne ignore_type, ne fait rien (toutes sont permanentes)
                    return 0
                
                deleted = cursor.rowcount
                conn.commit()
                
                if deleted > 0:
                    logger.info(f"Suppression de {deleted} paires ignorées temporairement")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Erreur suppression ignores temporaires: {e}")
            return 0
    
    def get_ignored_pairs_details(self):
        """Récupère les détails des paires ignorées"""
        try:
            ignored_pairs = []
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Vérifie si ignore_type existe
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]
                has_ignore_type = 'ignore_type' in columns
                
                if has_ignore_type:
                    cursor.execute('''
                        SELECT v1.file_path, v2.file_path, ip.reason, 
                               COALESCE(ip.ignore_type, 'permanent') as ignore_type, ip.created_at
                        FROM ignored_pairs ip
                        JOIN video_files v1 ON ip.file1_id = v1.id
                        JOIN video_files v2 ON ip.file2_id = v2.id
                        ORDER BY ip.created_at DESC
                    ''')
                else:
                    cursor.execute('''
                        SELECT v1.file_path, v2.file_path, ip.reason, 
                               'permanent' as ignore_type, ip.created_at
                        FROM ignored_pairs ip
                        JOIN video_files v1 ON ip.file1_id = v1.id
                        JOIN video_files v2 ON ip.file2_id = v2.id
                        ORDER BY ip.created_at DESC
                    ''')
                
                for row in cursor.fetchall():
                    file1, file2, reason, ignore_type, created_at = row
                    ignored_pairs.append({
                        'file1': file1,
                        'file2': file2,
                        'reason': reason,
                        'type': ignore_type,
                        'created_at': created_at
                    })
                
                return ignored_pairs
                
        except Exception as e:
            logger.error(f"Erreur récupération détails paires ignorées: {e}")
            return []
    
    def force_recreate_table(self, table_name):
        """Force la recréation d'une table (pour migration manuelle)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if table_name == "ignored_pairs":
                    # Sauvegarde les données existantes
                    cursor.execute('''
                        CREATE TEMPORARY TABLE ignored_pairs_backup AS 
                        SELECT * FROM ignored_pairs
                    ''')
                    
                    # Supprime l'ancienne table
                    cursor.execute("DROP TABLE ignored_pairs")
                    
                    # Recrée la nouvelle table
                    cursor.execute('''
                        CREATE TABLE ignored_pairs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            file1_id INTEGER,
                            file2_id INTEGER,
                            reason TEXT DEFAULT 'user_choice',
                            ignore_type TEXT DEFAULT 'permanent',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (file1_id) REFERENCES video_files (id) ON DELETE CASCADE,
                            FOREIGN KEY (file2_id) REFERENCES video_files (id) ON DELETE CASCADE,
                            UNIQUE(file1_id, file2_id)
                        )
                    ''')
                    
                    # Restaure les données
                    cursor.execute('''
                        INSERT INTO ignored_pairs (id, file1_id, file2_id, reason, ignore_type, created_at)
                        SELECT id, file1_id, file2_id, reason, 'permanent', created_at 
                        FROM ignored_pairs_backup
                    ''')
                    
                    # Supprime la table temporaire
                    cursor.execute("DROP TABLE ignored_pairs_backup")
                    
                    # Recrée les index
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ignored_pairs ON ignored_pairs(file1_id, file2_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ignored_type ON ignored_pairs(ignore_type)")
                    
                    conn.commit()
                    logger.info(f"Table {table_name} recréée avec succès")
                    return True
                    
        except Exception as e:
            logger.error(f"Erreur recréation table {table_name}: {e}")
            return False
    
    def verify_database_integrity(self):
        """Vérifie l'intégrité de la base de données"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Vérifie l'intégrité SQLite
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                
                if integrity_result[0] != "ok":
                    logger.warning(f"Problème d'intégrité détecté: {integrity_result[0]}")
                    return False
                
                # Vérifie que toutes les tables existent
                required_tables = ['video_files', 'comparisons', 'ignored_pairs', 'corrupted_files', 'found_duplicates']
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                missing_tables = [table for table in required_tables if table not in existing_tables]
                if missing_tables:
                    logger.warning(f"Tables manquantes: {missing_tables}")
                    return False
                
                # Vérifie la structure de ignored_pairs
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'ignore_type' not in columns:
                    logger.info("Colonne ignore_type manquante - migration nécessaire")
                    return False
                
                logger.info("Intégrité de la base de données vérifiée avec succès")
                return True
                
        except Exception as e:
            logger.error(f"Erreur vérification intégrité: {e}")
            return False
    
    def get_database_info(self):
        """Récupère des informations détaillées sur la base"""
        try:
            info = {
                'path': self.db_path,
                'exists': os.path.exists(self.db_path),
                'size_bytes': 0,
                'tables': [],
                'version': None,
                'pragma_settings': {}
            }
            
            if info['exists']:
                info['size_bytes'] = os.path.getsize(self.db_path)
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Tables
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    info['tables'] = [row[0] for row in cursor.fetchall()]
                    
                    # Version SQLite
                    cursor.execute("SELECT sqlite_version()")
                    info['version'] = cursor.fetchone()[0]
                    
                    # Paramètres PRAGMA
                    pragmas = ['journal_mode', 'synchronous', 'cache_size', 'temp_store', 'foreign_keys']
                    for pragma in pragmas:
                        try:
                            cursor.execute(f"PRAGMA {pragma}")
                            result = cursor.fetchone()
                            info['pragma_settings'][pragma] = result[0] if result else None
                        except:
                            info['pragma_settings'][pragma] = 'error'
            
            return info
            
        except Exception as e:
            logger.error(f"Erreur récupération infos DB: {e}")
            return {'error': str(e)}