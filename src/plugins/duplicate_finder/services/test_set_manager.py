"""
Test Set Manager - Gestion des paires de test
"""
import json
import os
from typing import Dict, List, Optional
import cv2
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.TestSetManager')


class TestSetManager:
    """Gestionnaire pour les paires de test (ground truth)."""

    def __init__(self, db_manager):
        """
        Args:
            db_manager: Instance de DatabaseManager
        """
        self.db = db_manager
        logger.info("TestSetManager initialisé")

    # ═══════════════════════════════════════════════════════════
    # MÉTHODES CRUD
    # ═══════════════════════════════════════════════════════════

    def add_test_pair(
        self,
        video1_path: str,
        video2_path: str,
        expected: str,
        test_set_name: str = 'default',
        start_time: float = 0.0,
        duration: float = None,
        sequence_score: float = 100.0,
        notes: str = None
    ) -> int:
        """
        Ajoute une paire de test.

        Args:
            video1_path: Chemin vidéo 1
            video2_path: Chemin vidéo 2
            expected: 'positive', 'negative', ou 'unknown'
            test_set_name: Nom du test set
            start_time: Temps de début (pour sous-séquences)
            duration: Durée (auto-détectée si None)
            sequence_score: Score attendu
            notes: Notes optionnelles

        Returns:
            ID de la paire créée
        """
        # Support both old and new label formats
        valid_labels = [
            'positive', 'negative', 'unknown',
            'duplicate', 'not_duplicate',
            'scene_found', 'scene_not_found'
        ]
        if expected not in valid_labels:
            raise ValueError(
                f"expected doit être l'un de {valid_labels}, reçu: {expected}"
            )

        # Auto-détection de la durée
        if duration is None and expected == 'positive':
            duration = self._get_video_duration(video1_path)

        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO test_pairs
                (video1_path, video2_path, expected, start_time, duration,
                 sequence_score, notes, test_set_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (video1_path, video2_path, expected, start_time, duration,
                  sequence_score, notes, test_set_name))
            conn.commit()
            pair_id = cursor.lastrowid
            logger.info(f"Paire de test ajoutée: {os.path.basename(video1_path)} ↔ {os.path.basename(video2_path)} ({expected})")
            return pair_id

    def update_test_pair(
        self,
        pair_id: int,
        expected: str = None,
        start_time: float = None,
        duration: float = None,
        sequence_score: float = None,
        notes: str = None
    ) -> bool:
        """Met à jour une paire de test."""
        updates = []
        params = []

        if expected is not None:
            if expected not in ['positive', 'negative', 'unknown', 'scene_not_found']:
                raise ValueError(f"expected invalide: {expected}")
            updates.append("expected = ?")
            params.append(expected)
        if start_time is not None:
            updates.append("start_time = ?")
            params.append(start_time)
        if duration is not None:
            updates.append("duration = ?")
            params.append(duration)
        if sequence_score is not None:
            updates.append("sequence_score = ?")
            params.append(sequence_score)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if not updates:
            return False

        params.append(pair_id)

        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            query = "UPDATE test_pairs SET " + ', '.join(updates) + " WHERE id = ?"  # nosec B608
            cursor.execute(query, params)  # colonnes pré-validées et paramétrées
            conn.commit()
            return cursor.rowcount > 0

    def delete_test_pair(self, pair_id: int) -> bool:
        """Supprime une paire de test."""
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM test_pairs WHERE id = ?", (pair_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_test_set(self, test_set_name: str = 'default') -> List[Dict]:
        """
        Récupère toutes les paires d'un test set.

        Returns:
            Liste de dicts avec {id, video1_path, video2_path, expected, ...}
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, video1_path, video2_path, expected, start_time, duration,
                       sequence_score, notes, created_at
                FROM test_pairs
                WHERE test_set_name = ?
                ORDER BY created_at DESC
            """, (test_set_name,))

            pairs = []
            for row in cursor.fetchall():
                pairs.append({
                    'id': row[0],
                    'video1_path': row[1],
                    'video2_path': row[2],
                    'expected': row[3],
                    'start_time': row[4],
                    'duration': row[5],
                    'sequence_score': row[6],
                    'notes': row[7],
                    'created_at': row[8]
                })

            return pairs

    def list_test_sets(self) -> List[Dict]:
        """
        Liste tous les test sets disponibles.

        Returns:
            Liste de dicts avec {name, count, positives, negatives, unknowns}
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT test_set_name,
                       COUNT(*) as total,
                       SUM(CASE WHEN expected = 'positive' THEN 1 ELSE 0 END) as positives,
                       SUM(CASE WHEN expected = 'negative' THEN 1 ELSE 0 END) as negatives,
                       SUM(CASE WHEN expected = 'unknown' THEN 1 ELSE 0 END) as unknowns
                FROM test_pairs
                GROUP BY test_set_name
                ORDER BY test_set_name
            """)

            test_sets = []
            for row in cursor.fetchall():
                test_sets.append({
                    'name': row[0],
                    'count': row[1],
                    'positives': row[2],
                    'negatives': row[3],
                    'unknowns': row[4]
                })

            return test_sets

    def delete_test_set(self, test_set_name: str) -> int:
        """
        Supprime toutes les paires d'un test set.

        Returns:
            Nombre de paires supprimées
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM test_pairs WHERE test_set_name = ?", (test_set_name,))
            conn.commit()
            count = cursor.rowcount
            logger.info(f"Test set '{test_set_name}' supprimé ({count} paires)")
            return count

    # ═══════════════════════════════════════════════════════════
    # GÉNÉRATION ET IMPORT/EXPORT
    # ═══════════════════════════════════════════════════════════

    def generate_from_file_list(
        self,
        file_paths: List[str],
        test_set_name: str = 'generated',
        expected: str = 'unknown'
    ) -> int:
        """
        Génère toutes les paires possibles depuis une liste de fichiers.

        Args:
            file_paths: Liste de chemins vidéo
            test_set_name: Nom du test set
            expected: Valeur expected par défaut

        Returns:
            Nombre de paires créées
        """
        count = 0

        for i, file1 in enumerate(file_paths):
            for file2 in file_paths[i+1:]:
                try:
                    self.add_test_pair(
                        video1_path=file1,
                        video2_path=file2,
                        expected=expected,
                        test_set_name=test_set_name
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Erreur lors de l'ajout de la paire: {e}")

        logger.info(f"Généré {count} paires depuis {len(file_paths)} fichiers")
        return count

    def expand_test_set_with_all_pairs(self, test_set_name: str, default_expected: str = 'unknown') -> Dict[str, int]:
        """
        Enrichit un test set existant en ajoutant TOUTES les paires possibles
        entre les vidéos du test set qui ne sont pas déjà présentes.

        Cela permet de tester si le pipeline détecte des paires non prévues.

        Args:
            test_set_name: Nom du test set à enrichir
            default_expected: Label par défaut pour les nouvelles paires ('unknown' recommandé)

        Returns:
            Dict avec {
                'existing_pairs': nombre de paires déjà présentes,
                'new_pairs': nombre de nouvelles paires ajoutées,
                'total_pairs': nombre total de paires après expansion
            }
        """
        # Récupérer toutes les paires existantes
        existing_pairs = self.get_test_set(test_set_name)

        if not existing_pairs:
            logger.warning(f"Test set '{test_set_name}' est vide, impossible de l'enrichir")
            return {'existing_pairs': 0, 'new_pairs': 0, 'total_pairs': 0}

        # Extraire toutes les vidéos uniques
        videos = set()
        existing_pair_set = set()  # Pour éviter les doublons
        for pair in existing_pairs:
            videos.add(pair['video1_path'])
            videos.add(pair['video2_path'])
            # Créer une clé unique (ordre indépendant)
            pair_key = tuple(sorted([pair['video1_path'], pair['video2_path']]))
            existing_pair_set.add(pair_key)

        videos = sorted(list(videos))
        logger.info(f"Test set '{test_set_name}': {len(videos)} vidéos uniques, {len(existing_pairs)} paires existantes")

        # Générer toutes les paires possibles
        new_pairs_count = 0
        for i, video1 in enumerate(videos):
            for video2 in videos[i+1:]:
                pair_key = tuple(sorted([video1, video2]))

                # Si la paire n'existe pas déjà, l'ajouter
                if pair_key not in existing_pair_set:
                    try:
                        self.add_test_pair(
                            video1_path=video1,
                            video2_path=video2,
                            expected=default_expected,
                            test_set_name=test_set_name,
                            notes="Auto-généré par expansion"
                        )
                        new_pairs_count += 1
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'ajout de la paire {video1} ↔ {video2}: {e}")

        total_pairs = len(existing_pairs) + new_pairs_count

        result = {
            'existing_pairs': len(existing_pairs),
            'new_pairs': new_pairs_count,
            'total_pairs': total_pairs
        }

        logger.info(
            f"Test set '{test_set_name}' enrichi: "
            f"{len(existing_pairs)} paires existantes + {new_pairs_count} nouvelles = {total_pairs} total"
        )

        return result

    def import_from_pairs_json(self, json_path: str, test_set_name: str = None) -> int:
        """
        Importe des paires depuis un fichier pairs.json (format legacy).

        Format attendu:
        [
            {
                "short": "/path/to/video1.mp4",
                "long": "/path/to/video2.mp4",
                "expected": "positive",
                "start": 45.0,
                "duration": 120.0,
                "sequence_score": 95.0,
                "preference": "notes optionnelles"
            },
            ...
        ]

        Args:
            json_path: Chemin du fichier pairs.json
            test_set_name: Nom du test set (utilise nom fichier si None)

        Returns:
            Nombre de paires importées
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            pairs_data = json.load(f)

        # Nom du test set
        if test_set_name is None:
            test_set_name = os.path.splitext(os.path.basename(json_path))[0]

        count = 0
        for item in pairs_data:
            try:
                self.add_test_pair(
                    video1_path=item.get('short', item.get('video1_path')),
                    video2_path=item.get('long', item.get('video2_path')),
                    expected=item.get('expected', 'positive'),
                    test_set_name=test_set_name,
                    start_time=float(item.get('start', item.get('start_time', 0.0))),
                    duration=item.get('duration'),
                    sequence_score=float(item.get('sequence_score', 100.0)),
                    notes=item.get('preference', item.get('notes'))
                )
                count += 1
            except Exception as e:
                logger.warning(f"Erreur import paire: {e}")

        logger.info(f"Importé {count} paires depuis {json_path}")
        return count

    def export_to_pairs_json(self, test_set_name: str, json_path: str):
        """
        Exporte un test set vers un fichier pairs.json.

        Args:
            test_set_name: Nom du test set
            json_path: Chemin de destination
        """
        pairs = self.get_test_set(test_set_name)

        export_data = []
        for pair in pairs:
            export_data.append({
                'short': pair['video1_path'],
                'long': pair['video2_path'],
                'expected': pair['expected'],
                'start': pair['start_time'],
                'duration': pair['duration'],
                'sequence_score': pair['sequence_score'],
                'preference': pair['notes']
            })

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exporté {len(export_data)} paires vers {json_path}")

    # ═══════════════════════════════════════════════════════════
    # UTILITAIRES
    # ═══════════════════════════════════════════════════════════

    def _normalize_label(self, expected: str) -> str:
        """
        Normalize expected labels to standard positive/negative/unknown format.

        Maps:
        - 'scene_found', 'duplicate' → 'positive'
        - 'scene_not_found', 'not_duplicate' → 'negative'
        - 'unknown' → 'unknown'
        """
        label_map = {
            'scene_found': 'positive',
            'duplicate': 'positive',
            'scene_not_found': 'negative',
            'not_duplicate': 'negative',
            'positive': 'positive',
            'negative': 'negative',
            'unknown': 'unknown'
        }
        return label_map.get(expected, 'unknown')

    def _get_video_duration(self, video_path: str) -> float:
        """Calcule la durée d'une vidéo."""
        if not os.path.exists(video_path):
            return 0.0

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 0.0

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        cap.release()

        if fps <= 0 or total_frames <= 0:
            return 0.0

        return float(total_frames / fps)

    def get_stats(self, test_set_name: str = 'default') -> Dict:
        """
        Statistiques sur un test set.

        Returns:
            Dict avec {total, positives, negatives, unknowns}
        """
        pairs = self.get_test_set(test_set_name)

        # Normalize labels for counting
        positives = 0
        negatives = 0
        unknowns = 0

        for p in pairs:
            normalized = self._normalize_label(p['expected'])
            if normalized == 'positive':
                positives += 1
            elif normalized == 'negative':
                negatives += 1
            elif normalized == 'unknown':
                unknowns += 1

        stats = {
            'total': len(pairs),
            'positives': positives,
            'negatives': negatives,
            'unknowns': unknowns
        }

        return stats
