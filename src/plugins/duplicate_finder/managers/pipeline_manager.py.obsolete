"""
Pipeline Manager - Gestion des pipelines de vérification
"""
import json
from typing import Dict, List, Optional
from datetime import datetime
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.PipelineManager')


class PipelineManager:
    """Gestionnaire pour les pipelines de vérification sauvegardés."""

    # Protocoles prédéfinis (importés depuis ui/panels.py)
    DEFAULT_PROTOCOLS = {
        'anti_fp': {
            'name': 'Anti-Faux Positifs',
            'description': 'Seuils très stricts (92-97%) pour éliminer tous les faux positifs. Peut manquer certains vrais doublons.',
            'mode': 'filtering',
            'methods': [
                {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 92.0}, 'weight': 1.5},
                {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 90.0, 'sample_interval': 3}, 'weight': 1.5},
                {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 85.0, 'num_coeffs': 15}, 'weight': 2.0},
                {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 60.0, 'dct_threshold': 85.0, 'sequence_threshold': 97.0, 'num_samples': 15, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 3.0}
            ]
        },
        'balanced': {
            'name': 'Équilibré',
            'description': 'Bon compromis entre précision et rappel (seuils 85-90%). Recommandé pour la plupart des cas.',
            'mode': 'filtering',
            'methods': [
                {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 85.0}, 'weight': 1.0},
                {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 85.0, 'sample_interval': 3}, 'weight': 1.0},
                {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 75.0, 'num_coeffs': 15}, 'weight': 1.5},
                {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 50.0, 'dct_threshold': 75.0, 'sequence_threshold': 95.0, 'num_samples': 10, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 2.0}
            ]
        },
        'high_precision': {
            'name': 'Haute Précision',
            'description': 'Tous les tests activés avec seuils très élevés (90-98%). Maximum de fiabilité, lent.',
            'mode': 'hybrid',
            'methods': [
                {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 90.0}, 'weight': 1.0},
                {'name': 'edge_pattern', 'enabled': True, 'parameters': {'threshold': 85.0}, 'weight': 1.0},
                {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 90.0, 'sample_interval': 2}, 'weight': 1.5},
                {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 85.0, 'num_coeffs': 20}, 'weight': 2.0},
                {'name': 'ssim', 'enabled': True, 'parameters': {'threshold': 0.90}, 'weight': 1.5},
                {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 60.0, 'dct_threshold': 88.0, 'sequence_threshold': 98.0, 'num_samples': 20, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 3.0}
            ]
        },
        'fast': {
            'name': 'Rapide',
            'description': 'Seuils plus bas (75-85%) et moins de méthodes pour une exécution rapide.',
            'mode': 'filtering',
            'methods': [
                {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 80.0}, 'weight': 1.0},
                {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 70.0, 'num_coeffs': 10}, 'weight': 1.0},
                {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 45.0, 'dct_threshold': 70.0, 'sequence_threshold': 90.0, 'num_samples': 8, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 1.5}
            ]
        },
        'dct_only': {
            'name': 'DCT Seulement',
            'description': 'Uniquement DCT coefficients. Parfait pour détecter les vidéos réencodées avec différents codecs/bitrates.',
            'mode': 'filtering',
            'methods': [
                {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 70.0, 'num_coeffs': 20}, 'weight': 1.0}
            ]
        },
        'motion_only': {
            'name': 'Motion Seulement',
            'description': 'Uniquement motion analysis. Idéal pour détecter les vidéos recadrées, rotées ou avec bordures ajoutées.',
            'mode': 'filtering',
            'methods': [
                {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 80.0, 'sample_interval': 2}, 'weight': 1.0}
            ]
        },
        'weighted_consensus': {
            'name': 'Consensus Pondéré',
            'description': 'Mode weighting: combine tous les tests avec poids. Score global = moyenne pondérée de toutes les méthodes.',
            'mode': 'weighting',
            'methods': [
                {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 80.0}, 'weight': 1.0},
                {'name': 'edge_pattern', 'enabled': True, 'parameters': {'threshold': 75.0}, 'weight': 0.8},
                {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 80.0, 'sample_interval': 3}, 'weight': 1.5},
                {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 70.0, 'num_coeffs': 15}, 'weight': 2.0},
                {'name': 'ssim', 'enabled': True, 'parameters': {'threshold': 0.80}, 'weight': 1.2}
            ]
        },
        're_encoded_specialist': {
            'name': 'Spécialiste Réencodage',
            'description': 'Optimisé pour vidéos réencodées: DCT + Motion avec seuils adaptés. Ignore les différences de couleur/compression.',
            'mode': 'filtering',
            'methods': [
                {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 68.0, 'num_coeffs': 20}, 'weight': 2.0},
                {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 75.0, 'sample_interval': 2}, 'weight': 1.5},
                {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 40.0, 'dct_threshold': 68.0, 'sequence_threshold': 88.0, 'num_samples': 12, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 2.5}
            ]
        },
        'ultra_permissive': {
            'name': 'Ultra Permissif',
            'description': 'Seuils très bas (60-70%) pour maximiser le rappel. Risque de faux positifs mais trouve TOUS les doublons potentiels.',
            'mode': 'weighting',
            'methods': [
                {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 65.0}, 'weight': 1.0},
                {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 70.0, 'sample_interval': 4}, 'weight': 1.0},
                {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 60.0, 'num_coeffs': 12}, 'weight': 1.0}
            ]
        },
        'hybrid_conservative': {
            'name': 'Hybride Conservateur',
            'description': 'Mode hybrid: moyenne pondérée + seuils individuels. Seuils modérés (80-85%) pour bon équilibre.',
            'mode': 'hybrid',
            'methods': [
                {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 82.0}, 'weight': 1.0},
                {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 82.0, 'sample_interval': 3}, 'weight': 1.2},
                {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 72.0, 'num_coeffs': 15}, 'weight': 1.8},
                {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 48.0, 'dct_threshold': 75.0, 'sequence_threshold': 92.0, 'num_samples': 12, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 2.0}
            ]
        }
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
