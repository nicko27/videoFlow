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

    # Protocoles prédéfinis - Initialisés automatiquement au premier démarrage
    DEFAULT_PROTOCOLS = {
        'color_histogram': {
            'name': '🎨 Color Histogram',
            'description': 'Compare color distribution using histogram analysis',
            'mode': 'multiple',
            'methods': {
                'methods': [
                    {
                        'name': 'color_histogram',
                        'enabled': True,
                        'parameters': {'threshold': 85.0},
                        'weight': 1.0
                    }
                ]
            }
        },
        'edge_pattern': {
            'name': '📐 Edge Pattern',
            'description': 'Detect duplicates based on edge detection patterns',
            'mode': 'multiple',
            'methods': {
                'methods': [
                    {
                        'name': 'edge_pattern',
                        'enabled': True,
                        'parameters': {'threshold': 80.0},
                        'weight': 1.0
                    }
                ]
            }
        },
        'motion_analysis': {
            'name': '🎬 Motion Analysis',
            'description': 'Analyze motion vectors and temporal patterns',
            'mode': 'multiple',
            'methods': {
                'methods': [
                    {
                        'name': 'motion_analysis',
                        'enabled': True,
                        'parameters': {'correlation_threshold': 85.0, 'sample_interval': 3},
                        'weight': 1.0
                    }
                ]
            }
        },
        'dct_coefficients': {
            'name': '🔢 DCT Coefficients',
            'description': 'Use Discrete Cosine Transform for frequency domain comparison',
            'mode': 'multiple',
            'methods': {
                'methods': [
                    {
                        'name': 'dct_coefficients',
                        'enabled': True,
                        'parameters': {'threshold': 75.0, 'num_coeffs': 15},
                        'weight': 1.0
                    }
                ]
            }
        },
        'perceptual_hash': {
            'name': '🔑 Perceptual Hash',
            'description': 'Fast perceptual hashing for quick comparison',
            'mode': 'multiple',
            'methods': {
                'methods': [
                    {
                        'name': 'perceptual_hash',
                        'enabled': True,
                        'parameters': {'threshold': 90.0},
                        'weight': 1.0
                    }
                ]
            }
        },
        'combined_balanced': {
            'name': '⚖️ Balanced Combined',
            'description': 'Balanced mix of multiple algorithms for good accuracy',
            'mode': 'multiple',
            'methods': {
                'methods': [
                    {
                        'name': 'color_histogram',
                        'enabled': True,
                        'parameters': {'threshold': 85.0},
                        'weight': 1.0
                    },
                    {
                        'name': 'motion_analysis',
                        'enabled': True,
                        'parameters': {'correlation_threshold': 85.0, 'sample_interval': 3},
                        'weight': 1.5
                    },
                    {
                        'name': 'dct_coefficients',
                        'enabled': True,
                        'parameters': {'threshold': 75.0, 'num_coeffs': 15},
                        'weight': 1.5
                    }
                ]
            }
        },
        'high_precision': {
            'name': '🎯 High Precision',
            'description': 'Maximum accuracy with strict thresholds',
            'mode': 'multiple',
            'methods': {
                'methods': [
                    {
                        'name': 'color_histogram',
                        'enabled': True,
                        'parameters': {'threshold': 92.0},
                        'weight': 1.5
                    },
                    {
                        'name': 'motion_analysis',
                        'enabled': True,
                        'parameters': {'correlation_threshold': 90.0, 'sample_interval': 3},
                        'weight': 2.0
                    },
                    {
                        'name': 'dct_coefficients',
                        'enabled': True,
                        'parameters': {'threshold': 85.0, 'num_coeffs': 15},
                        'weight': 2.0
                    },
                    {
                        'name': 'edge_pattern',
                        'enabled': True,
                        'parameters': {'threshold': 85.0},
                        'weight': 1.0
                    }
                ]
            }
        },
        'fast_screening': {
            'name': '⚡ Fast Screening',
            'description': 'Quick screening with perceptual hash',
            'mode': 'multiple',
            'methods': {
                'methods': [
                    {
                        'name': 'perceptual_hash',
                        'enabled': True,
                        'parameters': {'threshold': 88.0},
                        'weight': 1.0
                    },
                    {
                        'name': 'color_histogram',
                        'enabled': True,
                        'parameters': {'threshold': 80.0},
                        'weight': 0.5
                    }
                ]
            }
        }
    }

    def __init__(self, db_manager):
        """
        Args:
            db_manager: Instance de DatabaseManager
        """
        self.db = db_manager
        logger.info("PipelineManager initialisé")

        # Initialiser les protocoles par défaut dans la DB au premier démarrage
        self.initialize_default_protocols()

    def initialize_default_protocols(self):
        """
        Initialise les protocoles par défaut dans la base de données.

        Cette méthode est appelée au démarrage pour s'assurer que tous les
        protocoles prédéfinis (DEFAULT_PROTOCOLS) sont présents dans la DB.

        - Insère uniquement les protocoles manquants (basé sur le nom)
        - Marque tous les protocoles par défaut avec is_default=1
        - Idempotent: peut être appelé plusieurs fois sans dupliquer
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()

            # Récupérer les noms des protocoles déjà présents avec is_default=1
            cursor.execute("""
                SELECT name FROM saved_pipelines WHERE is_default = 1
            """)
            existing_defaults = {row[0] for row in cursor.fetchall()}

            inserted_count = 0
            for protocol_id, config in self.DEFAULT_PROTOCOLS.items():
                protocol_name = config['name']

                # Ne pas insérer si déjà présent
                if protocol_name in existing_defaults:
                    continue

                # Insérer le protocole par défaut
                methods_json = json.dumps(config['methods'], ensure_ascii=False)
                confirmation_json = json.dumps(config.get('confirmation'), ensure_ascii=False) if config.get('confirmation') else None

                try:
                    cursor.execute("""
                        INSERT INTO saved_pipelines
                        (name, description, mode, methods_json, confirmation_json, is_default)
                        VALUES (?, ?, ?, ?, ?, 1)
                    """, (
                        protocol_name,
                        config['description'],
                        config['mode'],
                        methods_json,
                        confirmation_json
                    ))
                    inserted_count += 1
                    logger.debug(f"  ✅ Protocole par défaut inséré: {protocol_name}")
                except Exception as e:
                    # En cas d'erreur (ex: contrainte UNIQUE), on continue
                    logger.warning(f"  ⚠️ Échec insertion {protocol_name}: {e}")
                    continue

            conn.commit()

            if inserted_count > 0:
                logger.info(f"🔧 Protocoles par défaut initialisés: {inserted_count} ajoutés")
            else:
                logger.debug("✓ Tous les protocoles par défaut sont déjà en DB")

    # ═══════════════════════════════════════════════════════════
    # MÉTHODES CRUD
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _parse_methods_payload(payload: str) -> Dict:
        """
        Parse methods_json which can be either a list (legacy) or a dict containing
        methods and optional global_threshold.
        """
        methods = []
        global_threshold = None
        try:
            data = json.loads(payload)
            if isinstance(data, dict) and 'methods' in data:
                methods = data.get('methods', [])
                global_threshold = data.get('global_threshold')
            else:
                methods = data
        except Exception:
            methods = []
        return {"methods": methods, "global_threshold": global_threshold}

    def save_pipeline(self, name: str, description: str, mode: str, methods: List[Dict], confirmation: Optional[Dict] = None, global_threshold: Optional[float] = None) -> int:
        """
        Sauvegarde un pipeline utilisateur.

        Args:
            name: Nom unique du pipeline
            description: Description
            mode: 'filtering', 'weighting', ou 'hybrid'
            methods: Liste de dicts avec {name, enabled, parameters, weight}
            confirmation: Dict avec configuration de confirmation visuelle (optionnel)

        Returns:
            ID du pipeline créé

        Raises:
            ValueError: Si le nom existe déjà ou mode invalide
        """
        # Validation
        if mode not in ['filtering', 'weighting', 'hybrid']:
            raise ValueError(f"Mode invalide: {mode}")

        # Sérialisation (supporte désormais un seuil global)
        if global_threshold is not None:
            methods_payload = {"methods": methods, "global_threshold": global_threshold}
        else:
            methods_payload = methods
        methods_json = json.dumps(methods_payload, ensure_ascii=False)

        confirmation_json = json.dumps(confirmation, ensure_ascii=False) if confirmation else None

        # Insertion (pipelines utilisateur: is_default=0)
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO saved_pipelines (name, description, mode, methods_json, confirmation_json, is_default)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (name, description, mode, methods_json, confirmation_json))
                conn.commit()
                pipeline_id = cursor.lastrowid
                logger.info(f"Pipeline utilisateur sauvegardé: {name} (ID: {pipeline_id})")
                return pipeline_id
            except Exception as e:
                if 'UNIQUE constraint failed' in str(e):
                    raise ValueError(f"Un pipeline nommé '{name}' existe déjà")
                raise

    def update_pipeline(self, pipeline_id: int, name: str = None, description: str = None,
                       mode: str = None, methods: List[Dict] = None, confirmation: Optional[Dict] = None,
                       global_threshold: Optional[float] = None) -> bool:
        """
        Met à jour un pipeline existant.

        Note: Les pipelines par défaut (is_default=1) ne peuvent pas être modifiés.

        Args:
            pipeline_id: ID du pipeline
            name: Nouveau nom (optionnel)
            description: Nouvelle description (optionnel)
            mode: Nouveau mode (optionnel)
            methods: Nouvelles méthodes (optionnel)

        Returns:
            True si mise à jour réussie

        Raises:
            ValueError: Si tentative de modification d'un pipeline par défaut
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()

            # Vérifier si c'est un pipeline par défaut
            cursor.execute("SELECT is_default, name FROM saved_pipelines WHERE id = ?", (pipeline_id,))
            row = cursor.fetchone()

            if not row:
                return False

            is_default, current_name = row
            if is_default:
                raise ValueError(f"Impossible de modifier le pipeline par défaut '{current_name}'")

            # Construire la requête de mise à jour
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
                if global_threshold is not None:
                    payload = {"methods": methods, "global_threshold": global_threshold}
                else:
                    payload = methods
                params.append(json.dumps(payload, ensure_ascii=False))
            elif global_threshold is not None:
                # CORRECTION BUG #2: Fix race condition by reading within the same transaction
                # Previously: get_pipeline_by_id() was called outside transaction,
                # allowing another thread to modify the pipeline between read and write.
                # Solution: Read methods_json directly within this transaction.
                cursor.execute(
                    "SELECT methods_json FROM saved_pipelines WHERE id = ?",
                    (pipeline_id,)
                )
                methods_row = cursor.fetchone()
                if methods_row:
                    current_methods = self._parse_methods_payload(methods_row[0])
                    payload = {"methods": current_methods.get("methods", []), "global_threshold": global_threshold}
                    updates.append("methods_json = ?")
                    params.append(json.dumps(payload, ensure_ascii=False))
            if confirmation is not None:
                updates.append("confirmation_json = ?")
                params.append(json.dumps(confirmation, ensure_ascii=False))

            if not updates:
                return False

            params.append(pipeline_id)

            # Paramétrer la requête pour éviter les f-strings SQL
            query = "UPDATE saved_pipelines SET " + ', '.join(updates) + " WHERE id = ?"  # nosec B608
            cursor.execute(query, params)  # colonnes pré-validées et paramétrées
            conn.commit()
            logger.info(f"Pipeline utilisateur mis à jour: {current_name} (ID: {pipeline_id})")
            return cursor.rowcount > 0

    def delete_pipeline(self, pipeline_id: int) -> bool:
        """
        Supprime un pipeline.

        Note: Les pipelines par défaut (is_default=1) ne peuvent pas être supprimés.

        Returns:
            True si suppression réussie

        Raises:
            ValueError: Si tentative de suppression d'un pipeline par défaut
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()

            # Vérifier si c'est un pipeline par défaut
            cursor.execute("SELECT is_default, name FROM saved_pipelines WHERE id = ?", (pipeline_id,))
            row = cursor.fetchone()

            if not row:
                return False

            is_default, name = row
            if is_default:
                raise ValueError(f"Impossible de supprimer le pipeline par défaut '{name}'")

            # Supprimer le pipeline utilisateur
            cursor.execute("DELETE FROM saved_pipelines WHERE id = ?", (pipeline_id,))
            conn.commit()
            logger.info(f"Pipeline utilisateur supprimé: {name} (ID: {pipeline_id})")
            return cursor.rowcount > 0

    def get_pipeline(self, pipeline_id: int) -> Optional[Dict]:
        """
        Récupère un pipeline par ID.

        Returns:
            Dict avec {id, name, description, mode, methods, confirmation, created_at, last_used_at, use_count, is_default}
            ou None si non trouvé
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, mode, methods_json, confirmation_json,
                       created_at, last_used_at, use_count, is_default
                FROM saved_pipelines WHERE id = ?
            """, (pipeline_id,))
            row = cursor.fetchone()

            if not row:
                return None

            parsed = self._parse_methods_payload(row[4])
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'mode': row[3],
                'methods': parsed["methods"],
                'global_threshold': parsed["global_threshold"],
                'confirmation': json.loads(row[5]) if row[5] else None,
                'created_at': row[6],
                'last_used_at': row[7],
                'use_count': row[8],
                'is_default': bool(row[9])
            }

    def get_pipeline_by_name(self, name: str) -> Optional[Dict]:
        """Récupère un pipeline par nom."""
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, mode, methods_json, confirmation_json,
                       created_at, last_used_at, use_count, is_default
                FROM saved_pipelines WHERE name = ?
            """, (name,))
            row = cursor.fetchone()

            if not row:
                return None

            parsed = self._parse_methods_payload(row[4])
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'mode': row[3],
                'methods': parsed["methods"],
                'global_threshold': parsed["global_threshold"],
                'confirmation': json.loads(row[5]) if row[5] else None,
                'created_at': row[6],
                'last_used_at': row[7],
                'use_count': row[8],
                'is_default': bool(row[9])
            }

    def list_pipelines(self, include_defaults: bool = True) -> List[Dict]:
        """
        Liste tous les pipelines disponibles depuis la base de données.

        IMPORTANT: Cette méthode lit désormais UNIQUEMENT depuis la DB.
        Les protocoles par défaut sont stockés en DB avec is_default=1.

        Args:
            include_defaults: Si True, inclut les protocoles par défaut (is_default=1)

        Returns:
            Liste de dicts avec {id, name, description, mode, methods, is_default, ...}
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()

            # Construire la requête SQL en fonction de include_defaults
            if include_defaults:
                # Tous les pipelines (défauts + utilisateur)
                query = """
                    SELECT id, name, description, mode, methods_json, confirmation_json,
                           created_at, last_used_at, use_count, is_default
                    FROM saved_pipelines
                    ORDER BY is_default DESC, use_count DESC, created_at DESC
                """
            else:
                # Uniquement les pipelines utilisateur (is_default=0)
                query = """
                    SELECT id, name, description, mode, methods_json, confirmation_json,
                           created_at, last_used_at, use_count, is_default
                    FROM saved_pipelines
                    WHERE is_default = 0
                    ORDER BY use_count DESC, created_at DESC
                """

            cursor.execute(query)
            pipelines = []

            for row in cursor.fetchall():
                parsed = self._parse_methods_payload(row[4])
                pipelines.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'mode': row[3],
                    'methods': parsed["methods"],
                    'global_threshold': parsed["global_threshold"],
                    'confirmation': json.loads(row[5]) if row[5] else None,
                    'created_at': row[6],
                    'last_used_at': row[7],
                    'use_count': row[8],
                    'is_default': bool(row[9])  # Convertir 0/1 en False/True
                })

            return pipelines

    def get_saved_pipelines(self, include_defaults: bool = True) -> List[str]:
        """
        Retourne la liste des noms de pipelines (compatibilité avec UI).

        Args:
            include_defaults: Si True, inclut les protocoles par défaut

        Returns:
            Liste de noms de pipelines
        """
        pipelines = self.list_pipelines(include_defaults=include_defaults)
        return [p['name'] for p in pipelines]

    def increment_use_count(self, pipeline_id: int):
        """Incrémente le compteur d'utilisation et met à jour last_used_at."""
        with self.db.pool.get_connection() as conn:
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

        DEPRECATED: Cette méthode est conservée pour rétrocompatibilité.
        Utiliser get_pipeline_by_name() à la place.

        Args:
            protocol_id: 'anti_fp', 'balanced', etc. (anciens identifiants)

        Returns:
            Dict avec {name, description, mode, methods} ou None
        """
        # Mapping des anciens protocol_id vers les noms en DB
        protocol_name_mapping = {
            'anti_fp': 'Anti-Faux Positifs',
            'balanced': 'Équilibré',
            'high_precision': 'Haute Précision',
            'fast': 'Rapide',
            'dct_only': 'DCT Seulement',
            'motion_only': 'Motion Seulement',
            'weighted_consensus': 'Consensus Pondéré',
            're_encoded_specialist': 'Spécialiste Réencodage',
            'ultra_permissive': 'Ultra Permissif',
            'debug_accept_all': '🚨 DEBUG - Accepte Tout',
            'hybrid_conservative': 'Hybride Conservateur'
        }

        protocol_name = protocol_name_mapping.get(protocol_id)
        if not protocol_name:
            logger.warning(f"Protocol ID inconnu: {protocol_id}")
            return None

        # Chercher dans la base de données
        return self.get_pipeline_by_name(protocol_name)

    def create_verification_pipeline(self, pipeline_config: Dict):
        """
        Crée une instance VerificationPipeline depuis une config.

        Args:
            pipeline_config: Dict avec {mode, methods, max_workers (optional)}

        Returns:
            Instance de VerificationPipeline configurée
        """
        from ..verification import VerificationPipeline

        mode = pipeline_config['mode']
        methods = pipeline_config['methods']
        # Extract max_workers from config if provided, otherwise default to 8
        max_workers = pipeline_config.get('max_workers', 8)

        pipeline = VerificationPipeline(
            db_manager=self.db,
            max_workers=max_workers,
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
