# Intégration des Nouvelles Fonctionnalités dans duplicate_finder

Ce document explique comment utiliser les nouvelles fonctionnalités DuplicateFlow dans le plugin duplicate_finder de VideoFlow.

## Vue d'Ensemble

Les trois nouvelles fonctionnalités peuvent être intégrées dans le workflow existant :

1. **Validation de longueur** : Filtrer les paires de vidéos avant comparaison
2. **Analyse partielle** : Optimiser les performances pour la détection de duplicatas
3. **Validateurs personnalisés** : Ajouter des critères de validation spécifiques

## Cas d'Usage dans duplicate_finder

### 1. Mode Duplicata Optimisé

Pour détecter rapidement des duplicatas complets sans analyser toute la vidéo :

```python
from duplicateflow.pipeline import Pipeline
from duplicateflow.sdk import LengthValidator

# Configuration pour détection rapide de duplicatas
pipeline = Pipeline(
    steps=[
        {'algorithm': 'frame_hash', 'weight': 0.4, 'threshold': 80.0},
        {'algorithm': 'color_histogram', 'weight': 0.3, 'threshold': 75.0},
        {'algorithm': 'motion_analysis', 'weight': 0.3, 'threshold': 75.0}
    ],

    # NOUVEAU : Filtrer par longueur similaire
    # Accepter seulement si durées à ±5% OU ±30 secondes
    pre_validators=[
        LengthValidator(
            tolerance_percent=5.0,
            tolerance_seconds=30.0,
            require_both=False  # OR logic
        )
    ],

    # NOUVEAU : Analyser seulement les 60 premières secondes
    # Économie de 90% du temps pour des vidéos de 10 min
    analyze_duration=60.0,
    analyze_from_start=True,

    # Optimisations standards
    global_threshold=75.0,
    early_termination=True,
    show_progress=True
)
```

**Gains de performance** :
- Filtrage pré-validation : ~10-50ms par paire
- Évite analyses inutiles : 1-10s par paire rejetée
- Analyse partielle (60s au lieu de 600s) : 90% de réduction

### 2. Mode Scène avec Validation Stricte

Pour détecter des scènes avec validation précise de la longueur :

```python
# Configuration pour détection de scènes
pipeline = Pipeline(
    steps=[
        {'algorithm': 'ssim', 'weight': 0.3, 'threshold': 70.0},
        {'algorithm': 'optical_flow', 'weight': 0.3, 'threshold': 70.0},
        {'algorithm': 'audio_fingerprint', 'weight': 0.4, 'threshold': 70.0}
    ],

    # NOUVEAU : Validation stricte de longueur pour scènes
    # Les DEUX tolérances doivent passer (AND logic)
    pre_validators=[
        LengthValidator(
            tolerance_percent=2.0,    # ±2% maximum
            tolerance_seconds=5.0,    # ET ±5 secondes maximum
            require_both=True         # AND logic
        )
    ],

    # Pas d'analyse partielle pour les scènes
    analyze_duration=None,  # Analyser la scène complète

    global_threshold=70.0
)
```

**Avantages** :
- Élimine les faux positifs (scènes de durées différentes)
- Validation stricte pour mode scène
- Garantit correspondance précise

### 3. Détection de Génériques/Intros

Pour comparer les génériques ou intros des vidéos :

```python
# Configuration pour génériques de fin
pipeline_end_credits = Pipeline(
    steps=[
        {'algorithm': 'frame_hash', 'weight': 0.5, 'threshold': 85.0},
        {'algorithm': 'color_histogram', 'weight': 0.5, 'threshold': 80.0}
    ],

    # NOUVEAU : Analyser seulement les 30 dernières secondes
    analyze_duration=30.0,
    analyze_from_start=False,  # De la fin

    # Pas de filtrage par longueur totale (non pertinent)
    pre_validators=[],

    global_threshold=80.0
)

# Configuration pour intros
pipeline_intros = Pipeline(
    steps=[...],
    analyze_duration=45.0,      # Premiers 45 secondes
    analyze_from_start=True,    # Du début
    global_threshold=80.0
)
```

**Cas d'usage** :
- Détecter des séries TV avec même générique
- Grouper des vidéos par intro/outro commun
- Optimisation : analyse seulement la portion pertinente

## Intégration dans l'UI

### Modification de PipelineConfigWidget

Ajouter des options UI pour configurer les nouvelles fonctionnalités :

```python
# src/plugins/duplicate_finder/ui/pipeline_config_widget.py

class PipelineConfigWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # ... code existant ...

        # NOUVEAU : Section Validation
        validation_group = QGroupBox("Validation de Longueur")
        validation_layout = QFormLayout()

        self.enable_length_validation = QCheckBox("Activer")
        self.tolerance_percent = QDoubleSpinBox()
        self.tolerance_percent.setRange(0.0, 100.0)
        self.tolerance_percent.setValue(5.0)
        self.tolerance_percent.setSuffix(" %")

        self.tolerance_seconds = QDoubleSpinBox()
        self.tolerance_seconds.setRange(0.0, 3600.0)
        self.tolerance_seconds.setValue(30.0)
        self.tolerance_seconds.setSuffix(" s")

        self.validation_logic = QComboBox()
        self.validation_logic.addItems(["OU (l'une ou l'autre)", "ET (les deux)"])

        validation_layout.addRow("Activer:", self.enable_length_validation)
        validation_layout.addRow("Tolérance %:", self.tolerance_percent)
        validation_layout.addRow("Tolérance s:", self.tolerance_seconds)
        validation_layout.addRow("Logique:", self.validation_logic)
        validation_group.setLayout(validation_layout)

        # NOUVEAU : Section Analyse Partielle
        partial_group = QGroupBox("Analyse Partielle")
        partial_layout = QFormLayout()

        self.enable_partial_analysis = QCheckBox("Activer")
        self.analyze_duration = QDoubleSpinBox()
        self.analyze_duration.setRange(1.0, 3600.0)
        self.analyze_duration.setValue(60.0)
        self.analyze_duration.setSuffix(" s")

        self.analyze_position = QComboBox()
        self.analyze_position.addItems(["Début de la vidéo", "Fin de la vidéo"])

        partial_layout.addRow("Activer:", self.enable_partial_analysis)
        partial_layout.addRow("Durée:", self.analyze_duration)
        partial_layout.addRow("Position:", self.analyze_position)
        partial_group.setLayout(partial_layout)

        # Ajouter au layout principal
        # ... layout.addWidget(validation_group)
        # ... layout.addWidget(partial_group)

    def get_pipeline_config(self):
        """Générer la configuration Pipeline avec les nouvelles options."""
        config = {
            'steps': self._get_algorithm_steps(),
            'global_threshold': self.threshold_spinbox.value(),
            'early_termination': self.early_termination_checkbox.isChecked(),
            'show_progress': True
        }

        # NOUVEAU : Ajouter validation de longueur
        if self.enable_length_validation.isChecked():
            from duplicateflow.sdk import LengthValidator

            require_both = (self.validation_logic.currentIndex() == 1)

            config['pre_validators'] = [
                LengthValidator(
                    tolerance_percent=self.tolerance_percent.value(),
                    tolerance_seconds=self.tolerance_seconds.value(),
                    require_both=require_both
                )
            ]

        # NOUVEAU : Ajouter analyse partielle
        if self.enable_partial_analysis.isChecked():
            config['analyze_duration'] = self.analyze_duration.value()
            config['analyze_from_start'] = (self.analyze_position.currentIndex() == 0)

        return config
```

### Modification de DuplicateFlowWorker

Utiliser la configuration étendue dans le worker :

```python
# src/plugins/duplicate_finder/workers/duplicateflow_worker.py

class DuplicateFlowWorker(QThread):
    def run(self):
        # Créer le pipeline avec la configuration complète
        pipeline_config = self.config.get('pipeline_config', {})

        # Le pipeline supporte maintenant automatiquement :
        # - pre_validators
        # - post_validators
        # - analyze_duration
        # - analyze_from_start
        pipeline = Pipeline(**pipeline_config)

        # Comparaison standard
        result = pipeline.compare(
            short_video=self.short_video,
            long_video=self.long_video,
            start_time=self.start_time,
            duration=self.duration
        )

        # NOUVEAU : Vérifier si rejeté par pré-validation
        if result['metadata'].get('pre_validation_failed'):
            validation_info = result['metadata']['pre_validation_results'][0]
            reason = validation_info['metadata'].get('reason', 'Unknown')

            self.progress.emit({
                'status': 'rejected',
                'reason': f"Filtré par validation: {reason}",
                'metadata': validation_info['metadata']
            })
            return

        # Traitement normal du résultat
        self.result_ready.emit(result)
```

### Interface Résultats

Afficher les informations de validation dans l'UI :

```python
# src/plugins/duplicate_finder/ui/panels.py

class ResultsPanel(QWidget):
    def display_result(self, result):
        # ... code existant ...

        # NOUVEAU : Afficher info validation
        metadata = result.get('metadata', {})

        if metadata.get('pre_validation_failed'):
            # Afficher pourquoi rejeté
            validation_results = metadata['pre_validation_results']
            for val_result in validation_results:
                if not val_result['passed']:
                    val_meta = val_result['metadata']

                    info_text = f"❌ Filtré par {val_result['validator']}\n"
                    info_text += f"   Raison: {val_meta.get('reason', 'N/A')}\n"

                    if 'length_diff_seconds' in val_meta:
                        info_text += f"   Différence: {val_meta['length_diff_seconds']:.1f}s "
                        info_text += f"({val_meta['length_diff_percent']:.1f}%)\n"

                    self.info_label.setText(info_text)

        elif result['accepted']:
            # Afficher info analyse partielle
            if 'analyze_duration' in metadata:
                info_text = f"✓ Duplicata détecté (analyse partielle: "
                info_text += f"{metadata['analyze_duration']}s)\n"
                self.info_label.setText(info_text)
```

## Présets Recommandés

Créer des présets pour les cas d'usage courants :

```python
# src/plugins/duplicate_finder/presets/duplicateflow_presets.py

DUPLICATEFLOW_PRESETS = {
    'fast_duplicate': {
        'name': 'Détection Rapide de Duplicatas',
        'description': 'Optimisé pour trouver rapidement des duplicatas exacts',
        'config': {
            'steps': [
                {'algorithm': 'frame_hash', 'weight': 0.5, 'threshold': 85.0},
                {'algorithm': 'color_histogram', 'weight': 0.5, 'threshold': 80.0}
            ],
            'pre_validators': [
                LengthValidator(tolerance_percent=5.0, tolerance_seconds=30.0)
            ],
            'analyze_duration': 60.0,
            'analyze_from_start': True,
            'global_threshold': 80.0,
            'early_termination': True
        }
    },

    'accurate_scene': {
        'name': 'Détection Précise de Scènes',
        'description': 'Validation stricte pour détecter des scènes exactes',
        'config': {
            'steps': [
                {'algorithm': 'ssim', 'weight': 0.3, 'threshold': 70.0},
                {'algorithm': 'motion_analysis', 'weight': 0.3, 'threshold': 70.0},
                {'algorithm': 'audio_fingerprint', 'weight': 0.4, 'threshold': 70.0}
            ],
            'pre_validators': [
                LengthValidator(
                    tolerance_percent=2.0,
                    tolerance_seconds=5.0,
                    require_both=True
                )
            ],
            'analyze_duration': None,  # Analyse complète
            'global_threshold': 70.0
        }
    },

    'intro_detector': {
        'name': 'Détecteur d\'Intros',
        'description': 'Compare les 45 premières secondes des vidéos',
        'config': {
            'steps': [
                {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 85.0},
                {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 80.0}
            ],
            'analyze_duration': 45.0,
            'analyze_from_start': True,
            'global_threshold': 85.0
        }
    },

    'credits_detector': {
        'name': 'Détecteur de Génériques',
        'description': 'Compare les 30 dernières secondes des vidéos',
        'config': {
            'steps': [
                {'algorithm': 'frame_hash', 'weight': 0.5, 'threshold': 85.0},
                {'algorithm': 'color_histogram', 'weight': 0.5, 'threshold': 80.0}
            ],
            'analyze_duration': 30.0,
            'analyze_from_start': False,  # Fin
            'global_threshold': 85.0
        }
    }
}


def get_duplicateflow_preset(preset_name):
    """Obtenir un preset DuplicateFlow par nom."""
    if preset_name not in DUPLICATEFLOW_PRESETS:
        raise ValueError(f"Preset '{preset_name}' inconnu")

    return DUPLICATEFLOW_PRESETS[preset_name]['config']
```

## Statistiques et Métriques

Ajouter des statistiques sur l'utilisation de la validation :

```python
# src/plugins/duplicate_finder/services/benchmark_manager.py

class BenchmarkManager:
    def run_benchmark(self, test_set, pipeline_config):
        stats = {
            'total_pairs': 0,
            'pre_validation_rejected': 0,
            'post_validation_rejected': 0,
            'accepted': 0,
            'rejected': 0,
            'time_saved_ms': 0
        }

        for pair in test_set:
            stats['total_pairs'] += 1

            start_time = time.time()
            result = pipeline.compare(pair['video1'], pair['video2'])
            elapsed_ms = (time.time() - start_time) * 1000

            # NOUVEAU : Tracker rejets par validation
            metadata = result.get('metadata', {})

            if metadata.get('pre_validation_failed'):
                stats['pre_validation_rejected'] += 1
                # Estimer le temps économisé
                # (validation ~50ms vs comparaison complète ~5000ms)
                stats['time_saved_ms'] += (5000 - elapsed_ms)

            elif metadata.get('post_validation_failed'):
                stats['post_validation_rejected'] += 1
                stats['rejected'] += 1

            elif result['accepted']:
                stats['accepted'] += 1
            else:
                stats['rejected'] += 1

        # Calculer métriques
        stats['pre_validation_rate'] = (
            stats['pre_validation_rejected'] / stats['total_pairs'] * 100
        )
        stats['time_saved_seconds'] = stats['time_saved_ms'] / 1000

        return stats
```

## Migration du Code Existant

### Étape 1 : Identifier les Cas d'Usage

Analyser le code existant pour identifier où les nouvelles fonctionnalités sont utiles :

1. **Recherche de DuplicateFlowWorker** :
   ```bash
   grep -r "DuplicateFlowWorker" src/plugins/duplicate_finder/
   ```

2. **Recherche de Pipeline** :
   ```bash
   grep -r "Pipeline(" src/plugins/duplicate_finder/
   ```

### Étape 2 : Migration Progressive

Ne pas tout changer d'un coup. Commencer par :

1. Ajouter UI pour validation de longueur (optionnelle, désactivée par défaut)
2. Ajouter preset "fast_duplicate" avec analyse partielle
3. Tester sur un sous-ensemble de données
4. Étendre progressivement

### Étape 3 : Tests de Régression

Vérifier que le code existant continue de fonctionner :

```python
# Test : Pipeline sans nouvelles fonctionnalités
def test_backward_compatibility():
    # Ancienne syntaxe - doit toujours fonctionner
    pipeline = Pipeline(
        steps=[
            {'algorithm': 'frame_hash', 'weight': 1.0, 'threshold': 75.0}
        ],
        global_threshold=70.0
    )

    # Vérifier comportement standard
    result = pipeline.compare("video1.mp4", "video2.mp4")
    assert 'global_score' in result
    assert 'accepted' in result

    # Vérifier absence de métadonnées de validation
    metadata = result.get('metadata', {})
    assert 'pre_validation_failed' not in metadata
```

## Benchmarks Attendus

### Scénario 1 : Dataset de 1000 paires
- **Sans optimisations** : ~5000 ms/paire = 83 min total
- **Avec validation longueur** (20% rejetés) : ~4000 ms/paire = 66 min (-20%)
- **Avec analyse partielle 60s** (vidéos 10 min) : ~500 ms/paire = 8.3 min (-90%)
- **Combiné** : ~400 ms/paire = 6.6 min (-92%)

### Scénario 2 : Dataset de 100 vidéos (comparaison all-vs-all)
- **Total paires** : 4950
- **Sans optimisations** : ~413 min (6.9h)
- **Avec optimisations** : ~33 min (0.55h)
- **Gain** : ~380 min (6.3h) économisées

## Conclusion

Les trois nouvelles fonctionnalités s'intègrent naturellement dans duplicate_finder :

1. ✅ **Validation de longueur** : Filtre intelligent pré-comparaison
2. ✅ **Analyse partielle** : Optimisation majeure pour duplicatas
3. ✅ **Extensibilité** : Framework pour validateurs personnalisés

**Prochaines étapes** :
1. Implémenter les modifications UI suggérées
2. Créer les presets recommandés
3. Tester avec datasets réels
4. Mesurer gains de performance
5. Documenter dans l'aide utilisateur
