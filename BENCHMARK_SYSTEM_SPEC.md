# Système de Benchmark - Spécifications Techniques Complètes

**Date de création**: 2025-12-07
**Status**: EN COURS - Phase 1 complétée (DB), Phase 2-4 à implémenter
**Fichiers modifiés jusqu'ici**: `database_manager.py`, `comparison_worker.py`, `analysis_handler.py`, `main_window.py`

---

## 📊 ÉTAT ACTUEL DU PROJET

### ✅ Phase 1: Base de données (COMPLÉTÉ)

**Fichier**: `src/plugins/duplicate_finder/database_manager.py`

**Tables créées** (lignes 599-667):
```sql
-- Table pour les pipelines utilisateur sauvegardés
saved_pipelines (
    id, name UNIQUE, description, mode, methods_json,
    created_at, last_used_at, use_count
)

-- Table pour les paires de test (ground truth)
test_pairs (
    id, video1_path, video2_path, expected CHECK(IN 'positive'/'negative'/'unknown'),
    start_time, duration, sequence_score, notes, test_set_name,
    created_at, UNIQUE(video1_path, video2_path, test_set_name)
)

-- Table pour les runs de benchmark batch
benchmark_runs (
    id, run_label, test_set_name, total_pairs, pipelines_count,
    created_at, completed_at, status DEFAULT 'running'
)

-- Table pour les résultats par pipeline
benchmark_results (
    id, benchmark_run_id FK, pipeline_name, pipeline_config_json,
    tp, fp, tn, fn, precision, recall, f1_score, total_time,
    per_pair_results_json
)
```

**Index créés** (lignes 710-717):
- `idx_saved_pipelines_name`, `idx_test_pairs_set`, `idx_test_pairs_expected`
- `idx_benchmark_runs_label`, `idx_benchmark_runs_status`
- `idx_benchmark_results_run`, `idx_benchmark_results_pipeline`

**Tables existantes réutilisées**:
- `pipeline_configs` - Pour les configs de pipeline (avec config_hash)
- `verification_runs` - Pour les runs individuels
- `verification_cache` - Pour le cache des vérifications
- `debug_labels` - Pour les labels debug (compatibilité pairs.json legacy)

### ✅ Annulation intégration audio-first (COMPLÉTÉ)

**Modifications annulées** dans:
1. `comparison_worker.py` (lignes 58-90, 383-385): Retiré param `verification_pipeline`
2. `analysis_handler.py` (lignes 127-159): Retiré param `verification_pipeline`
3. `main_window.py` (lignes 1150-1160, 1771-1782): Retiré passages de pipeline

**Raison**: Le VerificationPipeline est conçu pour les sous-séquences (nécessite start_time/duration), pas pour la comparaison de fichiers complets. Il reste utilisé uniquement en mode "🎬 SCÈNES".

---

## 🎯 ARCHITECTURE DU SYSTÈME À IMPLÉMENTER

```
┌─────────────────────────────────────────────────────────────┐
│                   ONGLET DEBUG (UI)                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 🔧 GESTION DES PIPELINES                          │    │
│  │  - PipelineEditorWidget                            │    │
│  │  - Utilise: PipelineManager                        │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 📋 GESTION DES TEST SETS                          │    │
│  │  - TestSetEditorWidget                             │    │
│  │  - Utilise: TestSetManager                         │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 🧪 BENCHMARK BATCH                                │    │
│  │  - BenchmarkBatchWidget                            │    │
│  │  - Utilise: BenchmarkRunner                        │    │
│  │  - Barres de progression: ModernProgressWidget     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 📊 RÉSULTATS COMPARATIFS                          │    │
│  │  - BenchmarkResultsWidget                          │    │
│  │  - Utilise: BenchmarkManager.get_results()         │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
         │                    │                    │
    ┌────┴────┐          ┌────┴────┐        ┌─────┴─────┐
    │Pipeline │          │TestSet  │        │Benchmark  │
    │Manager  │          │Manager  │        │Manager    │
    └────┬────┘          └────┬────┘        └─────┬─────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  VideoDatabase    │
                    │  (DB Manager)     │
                    └───────────────────┘
```

---

## 📦 PHASE 2: MANAGERS (Backend Logic)

### 2.1 PipelineManager

**Fichier à créer**: `src/plugins/duplicate_finder/managers/pipeline_manager.py`

**Responsabilités**:
- CRUD pour saved_pipelines
- Charger les 10 protocoles prédéfinis (depuis ui/panels.py TEST_PROTOCOLS)
- Valider les configurations de pipeline
- Créer des instances VerificationPipeline depuis la config

**Classe complète**:

```python
"""
Pipeline Manager - Gestion des pipelines de vérification
"""
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.PipelineManager')


class PipelineManager:
    """Gestionnaire pour les pipelines de vérification sauvegardés."""

    # Protocoles prédéfinis (importés depuis ui/panels.py)
    DEFAULT_PROTOCOLS = {
        'anti_fp': {...},  # Copier depuis ui/panels.py TEST_PROTOCOLS
        'balanced': {...},
        'high_precision': {...},
        'fast': {...},
        'dct_only': {...},
        'motion_only': {...},
        'weighted_consensus': {...},
        're_encoded_specialist': {...},
        'ultra_permissive': {...},
        'hybrid_conservative': {...}
    }

    def __init__(self, db_manager):
        """
        Args:
            db_manager: Instance de VideoDatabase
        """
        self.db = db_manager
        logger.info("PipelineManager initialisé")

    # ═══════════════════════════════════════════════════════════
    # MÉTHODES CRUD
    # ═══════════════════════════════════════════════════════════

    def save_pipeline(self, name: str, description: str, mode: str, methods: List[Dict]) -> int:
        """
        Sauvegarde un pipeline utilisateur.

        Args:
            name: Nom unique du pipeline
            description: Description
            mode: 'filtering', 'weighting', ou 'hybrid'
            methods: Liste de dicts avec {name, enabled, parameters, weight}

        Returns:
            ID du pipeline créé

        Raises:
            ValueError: Si le nom existe déjà ou mode invalide
        """
        # Validation
        if mode not in ['filtering', 'weighting', 'hybrid']:
            raise ValueError(f"Mode invalide: {mode}")

        # Sérialisation
        methods_json = json.dumps(methods, ensure_ascii=False)

        # Insertion
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO saved_pipelines (name, description, mode, methods_json)
                    VALUES (?, ?, ?, ?)
                """, (name, description, mode, methods_json))
                conn.commit()
                pipeline_id = cursor.lastrowid
                logger.info(f"Pipeline sauvegardé: {name} (ID: {pipeline_id})")
                return pipeline_id
            except Exception as e:
                if 'UNIQUE constraint failed' in str(e):
                    raise ValueError(f"Un pipeline nommé '{name}' existe déjà")
                raise

    def update_pipeline(self, pipeline_id: int, name: str = None, description: str = None,
                       mode: str = None, methods: List[Dict] = None) -> bool:
        """
        Met à jour un pipeline existant.

        Args:
            pipeline_id: ID du pipeline
            name: Nouveau nom (optionnel)
            description: Nouvelle description (optionnel)
            mode: Nouveau mode (optionnel)
            methods: Nouvelles méthodes (optionnel)

        Returns:
            True si mise à jour réussie
        """
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if mode is not None:
            if mode not in ['filtering', 'weighting', 'hybrid']:
                raise ValueError(f"Mode invalide: {mode}")
            updates.append("mode = ?")
            params.append(mode)
        if methods is not None:
            updates.append("methods_json = ?")
            params.append(json.dumps(methods, ensure_ascii=False))

        if not updates:
            return False

        params.append(pipeline_id)

        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE saved_pipelines
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_pipeline(self, pipeline_id: int) -> bool:
        """Supprime un pipeline."""
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM saved_pipelines WHERE id = ?", (pipeline_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_pipeline(self, pipeline_id: int) -> Optional[Dict]:
        """
        Récupère un pipeline par ID.

        Returns:
            Dict avec {id, name, description, mode, methods, created_at, last_used_at, use_count}
            ou None si non trouvé
        """
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, mode, methods_json,
                       created_at, last_used_at, use_count
                FROM saved_pipelines WHERE id = ?
            """, (pipeline_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'mode': row[3],
                'methods': json.loads(row[4]),
                'created_at': row[5],
                'last_used_at': row[6],
                'use_count': row[7]
            }

    def get_pipeline_by_name(self, name: str) -> Optional[Dict]:
        """Récupère un pipeline par nom."""
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, mode, methods_json,
                       created_at, last_used_at, use_count
                FROM saved_pipelines WHERE name = ?
            """, (name,))
            row = cursor.fetchone()

            if not row:
                return None

            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'mode': row[3],
                'methods': json.loads(row[4]),
                'created_at': row[5],
                'last_used_at': row[6],
                'use_count': row[7]
            }

    def list_pipelines(self, include_defaults: bool = True) -> List[Dict]:
        """
        Liste tous les pipelines disponibles.

        Args:
            include_defaults: Si True, inclut les 10 protocoles prédéfinis

        Returns:
            Liste de dicts avec {id, name, description, mode, is_default, ...}
        """
        pipelines = []

        # Ajouter les protocoles prédéfinis
        if include_defaults:
            for protocol_id, config in self.DEFAULT_PROTOCOLS.items():
                pipelines.append({
                    'id': None,
                    'name': config['name'],
                    'description': config['description'],
                    'mode': config['mode'],
                    'methods': config['methods'],
                    'is_default': True,
                    'protocol_id': protocol_id,
                    'created_at': None,
                    'last_used_at': None,
                    'use_count': 0
                })

        # Ajouter les pipelines utilisateur
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, mode, methods_json,
                       created_at, last_used_at, use_count
                FROM saved_pipelines
                ORDER BY use_count DESC, created_at DESC
            """)

            for row in cursor.fetchall():
                pipelines.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'mode': row[3],
                    'methods': json.loads(row[4]),
                    'is_default': False,
                    'protocol_id': None,
                    'created_at': row[5],
                    'last_used_at': row[6],
                    'use_count': row[7]
                })

        return pipelines

    def increment_use_count(self, pipeline_id: int):
        """Incrémente le compteur d'utilisation et met à jour last_used_at."""
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE saved_pipelines
                SET use_count = use_count + 1,
                    last_used_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), pipeline_id))
            conn.commit()

    # ═══════════════════════════════════════════════════════════
    # UTILITAIRES
    # ═══════════════════════════════════════════════════════════

    def get_protocol_config(self, protocol_id: str) -> Optional[Dict]:
        """
        Récupère la configuration d'un protocole prédéfini.

        Args:
            protocol_id: 'anti_fp', 'balanced', etc.

        Returns:
            Dict avec {name, description, mode, methods} ou None
        """
        return self.DEFAULT_PROTOCOLS.get(protocol_id)

    def create_verification_pipeline(self, pipeline_config: Dict):
        """
        Crée une instance VerificationPipeline depuis une config.

        Args:
            pipeline_config: Dict avec {mode, methods}

        Returns:
            Instance de VerificationPipeline configurée
        """
        from ..verification_pipeline import VerificationPipeline

        mode = pipeline_config['mode']
        methods = pipeline_config['methods']

        pipeline = VerificationPipeline(
            db_manager=self.db,
            max_workers=8,
            enable_caching=True,
            mode=mode
        )

        # Ajouter les méthodes
        for method in methods:
            if method.get('enabled', True):
                pipeline.add_method(
                    method['name'],
                    enabled=True,
                    parameters=method.get('parameters', {}),
                    weight=method.get('weight', 1.0)
                )

        return pipeline

    def export_to_json(self, pipeline_id: int, file_path: str):
        """Exporte un pipeline vers un fichier JSON."""
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} non trouvé")

        # Retirer les champs non nécessaires
        export_data = {
            'name': pipeline['name'],
            'description': pipeline['description'],
            'mode': pipeline['mode'],
            'methods': pipeline['methods']
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Pipeline exporté: {file_path}")

    def import_from_json(self, file_path: str, name: str = None) -> int:
        """
        Importe un pipeline depuis un fichier JSON.

        Args:
            file_path: Chemin du fichier JSON
            name: Nom pour le pipeline importé (optionnel, utilise le nom du fichier)

        Returns:
            ID du pipeline créé
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        import_name = name or data.get('name', 'Imported Pipeline')

        return self.save_pipeline(
            name=import_name,
            description=data.get('description', ''),
            mode=data['mode'],
            methods=data['methods']
        )
```

### 2.2 TestSetManager

**Fichier à créer**: `src/plugins/duplicate_finder/managers/test_set_manager.py`

**Responsabilités**:
- CRUD pour test_pairs
- Import/export pairs.json (compatibilité legacy)
- Génération automatique de paires depuis liste de fichiers
- Gestion des test sets (groupes de paires)

**Classe complète**:

```python
"""
Test Set Manager - Gestion des paires de test
"""
import json
import os
from typing import Dict, List, Optional, Tuple
import cv2
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.TestSetManager')


class TestSetManager:
    """Gestionnaire pour les paires de test (ground truth)."""

    def __init__(self, db_manager):
        """
        Args:
            db_manager: Instance de VideoDatabase
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
        if expected not in ['positive', 'negative', 'unknown']:
            raise ValueError(f"expected doit être 'positive', 'negative' ou 'unknown', reçu: {expected}")

        # Auto-détection de la durée
        if duration is None and expected == 'positive':
            duration = self._get_video_duration(video1_path)

        with self.db.connection_pool.get_connection() as conn:
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
            if expected not in ['positive', 'negative', 'unknown']:
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

        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE test_pairs
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_test_pair(self, pair_id: int) -> bool:
        """Supprime une paire de test."""
        with self.db.connection_pool.get_connection() as conn:
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
        with self.db.connection_pool.get_connection() as conn:
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
        with self.db.connection_pool.get_connection() as conn:
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
        with self.db.connection_pool.get_connection() as conn:
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
            Dict avec {total, positives, negatives, unknowns, max_possible_pairs}
        """
        pairs = self.get_test_set(test_set_name)

        stats = {
            'total': len(pairs),
            'positives': sum(1 for p in pairs if p['expected'] == 'positive'),
            'negatives': sum(1 for p in pairs if p['expected'] == 'negative'),
            'unknowns': sum(1 for p in pairs if p['expected'] == 'unknown')
        }

        return stats
```

### 2.3 BenchmarkManager

**Fichier à créer**: `src/plugins/duplicate_finder/managers/benchmark_manager.py`

**Responsabilités**:
- Exécuter des benchmarks batch (plusieurs pipelines sur un test set)
- Calculer les métriques (TP, FP, TN, FN, Precision, Recall, F1)
- Stocker et récupérer les résultats
- Générer des comparaisons

**Classe complète** (voir fichier suivant - trop long pour un seul bloc)

```python
"""
Benchmark Manager - Exécution et gestion des benchmarks
"""
import json
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import os

from src.core.logger import Logger
from ..verification_pipeline import VerificationPipeline

logger = Logger.get_logger('DuplicateFinder.BenchmarkManager')


class BenchmarkRunner(QThread):
    """
    Worker thread pour exécuter un benchmark batch.

    Signals:
        pipeline_progress: (current_pipeline, total_pipelines, pipeline_name)
        pair_progress: (current_pair, total_pairs, video1, video2)
        pipeline_completed: (pipeline_name, results_dict)
        finished: (benchmark_run_id)
        error: (error_msg)
    """

    pipeline_progress = pyqtSignal(int, int, str)  # current, total, name
    pair_progress = pyqtSignal(int, int, str, str)  # current, total, video1, video2
    pipeline_completed = pyqtSignal(str, dict)  # name, results
    finished = pyqtSignal(int)  # run_id
    error = pyqtSignal(str)

    def __init__(
        self,
        db_manager,
        test_pairs: List[Dict],
        pipeline_configs: List[Dict],
        run_label: str
    ):
        """
        Args:
            db_manager: Instance VideoDatabase
            test_pairs: Liste de paires de test
            pipeline_configs: Liste de configs pipeline
            run_label: Label du run
        """
        super().__init__()
        self.db = db_manager
        self.test_pairs = test_pairs
        self.pipeline_configs = pipeline_configs
        self.run_label = run_label
        self._stop = False

    def stop(self):
        """Arrête le benchmark."""
        self._stop = True

    def run(self):
        """Exécute le benchmark batch."""
        try:
            # Créer le run dans la DB
            run_id = self._create_benchmark_run()

            # Pour chaque pipeline
            total_pipelines = len(self.pipeline_configs)

            for pipeline_idx, pipeline_config in enumerate(self.pipeline_configs, 1):
                if self._stop:
                    break

                pipeline_name = pipeline_config['name']
                logger.info(f"Benchmark pipeline {pipeline_idx}/{total_pipelines}: {pipeline_name}")

                # Émettre progression pipeline
                self.pipeline_progress.emit(pipeline_idx, total_pipelines, pipeline_name)

                # Exécuter benchmark pour ce pipeline
                results = self._run_pipeline_benchmark(pipeline_config)

                # Stocker résultats
                self._store_pipeline_results(run_id, pipeline_config, results)

                # Émettre complétion
                self.pipeline_completed.emit(pipeline_name, results)

            # Marquer run comme complété
            self._complete_benchmark_run(run_id)

            # Émettre fin
            self.finished.emit(run_id)

        except Exception as e:
            logger.error(f"Erreur benchmark: {e}", exc_info=True)
            self.error.emit(str(e))

    def _create_benchmark_run(self) -> int:
        """Crée l'entrée benchmark_run dans la DB."""
        # Déterminer le test set name (depuis la première paire)
        test_set_name = 'default'
        if self.test_pairs:
            # Chercher dans la DB le test_set_name de la première paire
            with self.db.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT test_set_name FROM test_pairs
                    WHERE video1_path = ? AND video2_path = ?
                    LIMIT 1
                """, (self.test_pairs[0]['video1_path'], self.test_pairs[0]['video2_path']))
                row = cursor.fetchone()
                if row:
                    test_set_name = row[0]

        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO benchmark_runs
                (run_label, test_set_name, total_pairs, pipelines_count, status)
                VALUES (?, ?, ?, ?, 'running')
            """, (self.run_label, test_set_name, len(self.test_pairs), len(self.pipeline_configs)))
            conn.commit()
            return cursor.lastrowid

    def _complete_benchmark_run(self, run_id: int):
        """Marque le run comme complété."""
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE benchmark_runs
                SET status = 'completed', completed_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), run_id))
            conn.commit()

    def _run_pipeline_benchmark(self, pipeline_config: Dict) -> Dict:
        """
        Exécute un benchmark pour un pipeline.

        Returns:
            Dict avec {tp, fp, tn, fn, precision, recall, f1, total_time, per_pair_results}
        """
        # Créer le pipeline
        pipeline = self._create_pipeline(pipeline_config)

        # Métriques
        tp = fp = tn = fn = 0
        per_pair_results = []
        start_time = time.time()

        total_pairs = len(self.test_pairs)

        # Pour chaque paire
        for pair_idx, pair in enumerate(self.test_pairs, 1):
            if self._stop:
                break

            video1 = pair['video1_path']
            video2 = pair['video2_path']
            expected = pair['expected']

            # Émettre progression
            self.pair_progress.emit(pair_idx, total_pairs, video1, video2)

            # Vérifier avec le pipeline
            try:
                result = pipeline.verify(
                    short_video=video1,
                    long_video=video2,
                    start_time=pair.get('start_time', 0.0),
                    duration=pair.get('duration', 0.0),
                    sequence_score=pair.get('sequence_score', 100.0)
                )

                accepted = result['accepted']

                # Calculer métrique
                if expected == 'positive':
                    if accepted:
                        tp += 1
                    else:
                        fn += 1
                elif expected == 'negative':
                    if accepted:
                        fp += 1
                    else:
                        tn += 1
                # 'unknown' n'est pas compté

                # Stocker résultat détaillé
                per_pair_results.append({
                    'video1': video1,
                    'video2': video2,
                    'expected': expected,
                    'accepted': accepted,
                    'weighted_score': result.get('weighted_score'),
                    'total_time': result['total_time']
                })

            except Exception as e:
                logger.error(f"Erreur vérification {video1} vs {video2}: {e}")
                per_pair_results.append({
                    'video1': video1,
                    'video2': video2,
                    'expected': expected,
                    'accepted': False,
                    'error': str(e)
                })

        total_time = time.time() - start_time

        # Calculer métriques
        precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        return {
            'tp': tp,
            'fp': fp,
            'tn': tn,
            'fn': fn,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'total_time': total_time,
            'per_pair_results': per_pair_results
        }

    def _create_pipeline(self, pipeline_config: Dict) -> VerificationPipeline:
        """Crée une instance VerificationPipeline depuis la config."""
        mode = pipeline_config['mode']
        methods = pipeline_config['methods']

        pipeline = VerificationPipeline(
            db_manager=self.db,
            max_workers=8,
            enable_caching=True,
            mode=mode
        )

        for method in methods:
            if method.get('enabled', True):
                pipeline.add_method(
                    method['name'],
                    enabled=True,
                    parameters=method.get('parameters', {}),
                    weight=method.get('weight', 1.0)
                )

        return pipeline

    def _store_pipeline_results(self, run_id: int, pipeline_config: Dict, results: Dict):
        """Stocke les résultats d'un pipeline dans la DB."""
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO benchmark_results
                (benchmark_run_id, pipeline_name, pipeline_config_json,
                 tp, fp, tn, fn, precision, recall, f1_score, total_time,
                 per_pair_results_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                pipeline_config['name'],
                json.dumps(pipeline_config, ensure_ascii=False),
                results['tp'], results['fp'], results['tn'], results['fn'],
                results['precision'], results['recall'], results['f1_score'],
                results['total_time'],
                json.dumps(results['per_pair_results'], ensure_ascii=False)
            ))
            conn.commit()


class BenchmarkManager:
    """Gestionnaire pour les benchmarks et leurs résultats."""

    def __init__(self, db_manager):
        """
        Args:
            db_manager: Instance VideoDatabase
        """
        self.db = db_manager
        logger.info("BenchmarkManager initialisé")

    # ═══════════════════════════════════════════════════════════
    # MÉTHODES DE RÉCUPÉRATION
    # ═══════════════════════════════════════════════════════════

    def get_benchmark_run(self, run_id: int) -> Optional[Dict]:
        """Récupère les informations d'un run."""
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, run_label, test_set_name, total_pairs, pipelines_count,
                       created_at, completed_at, status
                FROM benchmark_runs WHERE id = ?
            """, (run_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return {
                'id': row[0],
                'run_label': row[1],
                'test_set_name': row[2],
                'total_pairs': row[3],
                'pipelines_count': row[4],
                'created_at': row[5],
                'completed_at': row[6],
                'status': row[7]
            }

    def get_benchmark_results(self, run_id: int) -> List[Dict]:
        """
        Récupère tous les résultats d'un run.

        Returns:
            Liste de dicts avec résultats par pipeline
        """
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pipeline_name, pipeline_config_json,
                       tp, fp, tn, fn, precision, recall, f1_score, total_time,
                       per_pair_results_json
                FROM benchmark_results
                WHERE benchmark_run_id = ?
                ORDER BY f1_score DESC
            """, (run_id,))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'pipeline_name': row[0],
                    'pipeline_config': json.loads(row[1]),
                    'tp': row[2],
                    'fp': row[3],
                    'tn': row[4],
                    'fn': row[5],
                    'precision': row[6],
                    'recall': row[7],
                    'f1_score': row[8],
                    'total_time': row[9],
                    'per_pair_results': json.loads(row[10])
                })

            return results

    def list_benchmark_runs(self, limit: int = 20) -> List[Dict]:
        """Liste les runs récents."""
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, run_label, test_set_name, total_pairs, pipelines_count,
                       created_at, completed_at, status
                FROM benchmark_runs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            runs = []
            for row in cursor.fetchall():
                runs.append({
                    'id': row[0],
                    'run_label': row[1],
                    'test_set_name': row[2],
                    'total_pairs': row[3],
                    'pipelines_count': row[4],
                    'created_at': row[5],
                    'completed_at': row[6],
                    'status': row[7]
                })

            return runs

    def delete_benchmark_run(self, run_id: int) -> bool:
        """Supprime un run (et tous ses résultats via CASCADE)."""
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM benchmark_runs WHERE id = ?", (run_id,))
            conn.commit()
            return cursor.rowcount > 0
```

---

## 📱 PHASE 3: INTERFACES UI (PyQt6 Widgets)

*(Contenu trop long - voir BENCHMARK_SYSTEM_SPEC_PART2.md pour les détails UI)*

---

## 🔄 ORDRE D'IMPLÉMENTATION RECOMMANDÉ

1. ✅ **Phase 1: DB** (FAIT)
   - Tables créées
   - Index ajoutés

2. **Phase 2: Managers** (EN COURS)
   - [X] Spec PipelineManager écrite
   - [X] Spec TestSetManager écrite
   - [X] Spec BenchmarkManager écrite
   - [ ] Implémenter pipeline_manager.py
   - [ ] Implémenter test_set_manager.py
   - [ ] Implémenter benchmark_manager.py
   - [ ] Tester les managers individuellement

3. **Phase 3: UI Widgets**
   - [ ] PipelineEditorWidget
   - [ ] TestSetEditorWidget
   - [ ] BenchmarkBatchWidget
   - [ ] BenchmarkResultsWidget

4. **Phase 4: Intégration**
   - [ ] Intégrer dans panels.py (onglet Debug)
   - [ ] Connecter aux barres de progression existantes
   - [ ] Tests end-to-end

---

## 📝 NOTES IMPORTANTES

### Barres de progression existantes

**Localisation**: `src/plugins/duplicate_finder/progress_widgets.py`

**Widgets disponibles**:
- `ModernProgressWidget` - Barre principale avec % et temps
- `FileListWidget` - Liste de fichiers
- `StatusIndicator` - Indicateur de status coloré

**Usage dans benchmark**:
```python
# Dans BenchmarkBatchWidget, créer 2 barres:
self.pipeline_progress = ModernProgressWidget()  # Pipeline X/Y
self.pair_progress = ModernProgressWidget()      # Paire X/Y

# Connecter aux signaux du BenchmarkRunner
self.runner.pipeline_progress.connect(self._update_pipeline_progress)
self.runner.pair_progress.connect(self._update_pair_progress)

# Les barres apparaissent/disparaissent selon état
if benchmark_running:
    self.pipeline_progress.setVisible(True)
    self.pair_progress.setVisible(True)
else:
    self.pipeline_progress.setVisible(False)
    self.pair_progress.setVisible(False)
```

### Protocoles prédéfinis

**Localisation**: `src/plugins/duplicate_finder/ui/panels.py` ligne 967-1078

**10 protocoles**:
1. anti_fp
2. balanced
3. high_precision
4. fast
5. dct_only
6. motion_only
7. weighted_consensus
8. re_encoded_specialist
9. ultra_permissive
10. hybrid_conservative

**À copier dans** `PipelineManager.DEFAULT_PROTOCOLS`

### Structure fichier pairs.json (legacy)

```json
[
  {
    "short": "/path/to/short.mp4",
    "long": "/path/to/long.mp4",
    "expected": "positive",
    "start": 45.0,
    "duration": 120.0,
    "sequence_score": 95.0,
    "preference": "notes"
  }
]
```

### Méthodes disponibles dans VerificationPipeline

1. `color_histogram` - Histogramme couleurs HSV
2. `edge_pattern` - Détection contours Canny
3. `motion_analysis` - Corrélation mouvement
4. `dct_coefficients` - Fréquences DCT
5. `ssim` - Similarité structurelle
6. `feature_matching` - Points clés ORB/SIFT
7. `strategy3` - Scene cuts + DCT (100% précision)

---

## ✅ CHECKLIST DE COMPLÉTION

### Managers (Backend)
- [ ] pipeline_manager.py créé et testé
- [ ] test_set_manager.py créé et testé
- [ ] benchmark_manager.py créé et testé
- [ ] managers/__init__.py mis à jour

### UI Widgets
- [ ] PipelineEditorWidget créé
- [ ] TestSetEditorWidget créé
- [ ] BenchmarkBatchWidget créé
- [ ] BenchmarkResultsWidget créé

### Intégration
- [ ] panels.py modifié (section Debug)
- [ ] Barres de progression connectées
- [ ] Export CSV/JSON implémenté
- [ ] Tests end-to-end réussis

### Documentation
- [ ] Docstrings complètes
- [ ] Exemples d'usage
- [ ] Guide utilisateur

---

## 🚀 PROCHAINE ÉTAPE

**Implémenter les 3 managers dans l'ordre**:
1. PipelineManager
2. TestSetManager
3. BenchmarkManager

**Puis créer les widgets UI**.

---

*Ce fichier sert de référence complète pour continuer le développement du système de benchmark, même après compactage du contexte ou dans une nouvelle session.*
