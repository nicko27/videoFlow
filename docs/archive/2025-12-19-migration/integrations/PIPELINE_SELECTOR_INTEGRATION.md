# Pipeline Selector - Integration Complete

**Date**: 2025-12-18
**Status**: ✅ COMPLETE

---

## 📝 Vue d'ensemble

Le sélecteur de pipeline DuplicateFlow a été intégré dans l'interface principale de duplicate_finder. Les utilisateurs peuvent maintenant :

✅ **Sélectionner** un pipeline parmi tous les pipelines disponibles (par défaut + personnalisés)
✅ **Créer** de nouveaux pipelines avec le bouton "➕ Nouveau"
✅ **Éditer** des pipelines personnalisés avec le bouton "✏️ Éditer"
✅ **Voir** la description et les features de chaque pipeline

---

## 📍 Emplacement

**Onglet** : ⚙️ Paramètres
**Position** : Juste après la section "🚀 Quick Presets"
**Avant** : Section LSH (DuplicateFlow Fingerprint Mode)

---

## 🎨 Interface Utilisateur

### Section "🎯 Pipeline DuplicateFlow"

```
┌─────────────────────────────────────────────────────────────┐
│ 🎯 Pipeline DuplicateFlow                                   │
├─────────────────────────────────────────────────────────────┤
│  Pipeline: [⭐ Fast Duplicate Detection    ▼] [✏️ Éditer] [➕ Nouveau] │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Description: Détection rapide de duplicatas           │ │
│  │ Mode: filtering | Méthodes: 2                         │ │
│  │ Features: ✓ Validation longueur, ⚡ Analyse partielle (60s) │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Éléments

1. **Combo Box "Pipeline"**
   - Affiche tous les pipelines (défauts marqués avec ⭐)
   - Tooltip: "Sélectionnez un pipeline de détection DuplicateFlow"
   - Hauteur: 35px

2. **Bouton "✏️ Éditer"**
   - Couleur: Bleu (#007BFF)
   - Tooltip: "Modifier le pipeline sélectionné"
   - Action: Ouvre UnifiedPipelineEditorDialog
   - Désactivé pour les pipelines par défaut

3. **Bouton "➕ Nouveau"**
   - Couleur: Vert (#28A745)
   - Tooltip: "Créer un nouveau pipeline"
   - Action: Ouvre UnifiedPipelineEditorDialog (mode création)

4. **Label de Description**
   - Background: #f5f5f5
   - Affiche: Description, mode, nombre de méthodes
   - Affiche les features DuplicateFlow si présentes

---

## 💻 Implémentation

### 1. panels.py (Ligne 376-468)

#### Ajout de la section

```python
# ═══════════════════════════════════════════════════════════
# DUPLICATEFLOW PIPELINE SELECTOR
# ═══════════════════════════════════════════════════════════
pipeline_group = QGroupBox("🎯 Pipeline DuplicateFlow")
pipeline_layout = QVBoxLayout(pipeline_group)
pipeline_layout.setSpacing(10)

# Pipeline selection row
selection_layout = QHBoxLayout()

pipeline_combo = QComboBox()
pipeline_combo.setMinimumHeight(35)
pipeline_combo.setObjectName("pipeline_combo")
pipeline_combo.setToolTip("Sélectionnez un pipeline de détection DuplicateFlow")

# Load pipelines from PipelineManager
if pipeline_manager:
    pipelines = pipeline_manager.list_pipelines(include_defaults=True)
    for pipeline in pipelines:
        display_name = pipeline['name']
        if pipeline.get('is_default'):
            display_name = f"⭐ {display_name}"
        pipeline_combo.addItem(display_name, userData=pipeline)
```

#### Fonction de mise à jour de la description

```python
def update_description(index):
    if index >= 0:
        pipeline_data = pipeline_combo.itemData(index)
        if pipeline_data:
            desc = pipeline_data.get('description', 'Aucune description')
            mode = pipeline_data.get('mode', 'unknown')
            methods_count = len(pipeline_data.get('methods', []))

            # Check for DuplicateFlow config
            df_config = pipeline_data.get('duplicateflow_config', {})
            features = []
            if df_config.get('pre_validators'):
                features.append("✓ Validation longueur")
            if df_config.get('analyze_duration'):
                duration = df_config['analyze_duration']
                features.append(f"⚡ Analyse partielle ({duration:.0f}s)")

            info_text = f"<b>Description:</b> {desc}<br>"
            info_text += f"<b>Mode:</b> {mode} | <b>Méthodes:</b> {methods_count}"
            if features:
                info_text += f"<br><b>Features:</b> {', '.join(features)}"

            pipeline_desc_label.setText(info_text)
```

#### Références stockées

```python
# Store references for later access in main window
tab.pipeline_combo = pipeline_combo
tab.edit_pipeline_btn = edit_pipeline_btn
tab.new_pipeline_btn = new_pipeline_btn
tab.pipeline_desc_label = pipeline_desc_label
```

---

### 2. main_window.py (Lignes 536-551)

#### Extraction des références

```python
# DuplicateFlow pipeline widgets (NEW)
self.pipeline_combo = getattr(params_tab, 'pipeline_combo', None)
self.edit_pipeline_btn = getattr(params_tab, 'edit_pipeline_btn', None)
self.new_pipeline_btn = getattr(params_tab, 'new_pipeline_btn', None)
self.pipeline_desc_label = getattr(params_tab, 'pipeline_desc_label', None)

# Connect pipeline buttons
if self.edit_pipeline_btn:
    self.edit_pipeline_btn.clicked.connect(self._on_edit_pipeline)
if self.new_pipeline_btn:
    self.new_pipeline_btn.clicked.connect(self._on_new_pipeline)
```

---

### 3. Méthodes de callback (Lignes 920-1012)

#### _on_edit_pipeline()

**Fonction** : Ouvre l'éditeur pour le pipeline sélectionné

**Comportement** :
1. Vérifie qu'un pipeline est sélectionné
2. Empêche l'édition des pipelines par défaut (message d'avertissement)
3. Ouvre `UnifiedPipelineEditorDialog` en mode édition
4. Recharge la liste après sauvegarde

**Protection des pipelines par défaut** :
```python
if pipeline_data.get('is_default', False):
    QMessageBox.warning(
        self,
        "Pipeline par défaut",
        f"Le pipeline '{pipeline_data['name']}' est un pipeline par défaut et ne peut pas être modifié.\n\n"
        "Vous pouvez créer une copie en cliquant sur 'Nouveau'."
    )
    return
```

#### _on_new_pipeline()

**Fonction** : Ouvre l'éditeur pour créer un nouveau pipeline

**Comportement** :
1. Ouvre `UnifiedPipelineEditorDialog` en mode création
2. Recharge la liste après sauvegarde
3. Sélectionne automatiquement le nouveau pipeline créé

#### _reload_pipeline_combo()

**Fonction** : Recharge la liste des pipelines

**Comportement** :
1. Mémorise le pipeline actuellement sélectionné
2. Vide et recharge la combo box
3. Restaure la sélection précédente si possible

---

## 🔄 Workflow Utilisateur

### Créer un nouveau pipeline

1. L'utilisateur clique sur "➕ Nouveau"
2. `UnifiedPipelineEditorDialog` s'ouvre (mode création)
3. L'utilisateur configure :
   - Nom et description
   - Mode (filtering/weighting/hybrid)
   - Méthodes de détection
   - **Validation de longueur** (nouveau)
   - **Analyse partielle** (nouveau)
4. L'utilisateur clique "💾 Sauvegarder"
5. Le pipeline est enregistré en base de données
6. La combo box se recharge et sélectionne le nouveau pipeline

### Éditer un pipeline existant

1. L'utilisateur sélectionne un pipeline dans la combo box
2. L'utilisateur clique sur "✏️ Éditer"
3. **Si pipeline par défaut** : Message d'avertissement + blocage
4. **Si pipeline personnalisé** : `UnifiedPipelineEditorDialog` s'ouvre
5. L'utilisateur modifie la configuration
6. L'utilisateur clique "💾 Sauvegarder"
7. Le pipeline est mis à jour en base de données
8. La combo box se recharge avec la sélection conservée

### Sélectionner un pipeline

1. L'utilisateur clique sur la combo box
2. Liste déroulante affiche tous les pipelines
3. Pipelines par défaut marqués avec ⭐
4. L'utilisateur sélectionne un pipeline
5. La description se met à jour automatiquement
6. Features DuplicateFlow affichées si présentes

---

## 📊 Affichage des Features

Le label de description affiche dynamiquement les features DuplicateFlow:

### Exemple 1 : Pipeline avec validation et analyse partielle

```
Description: Détection rapide de duplicatas
Mode: filtering | Méthodes: 2
Features: ✓ Validation longueur, ⚡ Analyse partielle (60s)
```

### Exemple 2 : Pipeline sans features

```
Description: Détection équilibrée
Mode: weighting | Méthodes: 4
```

### Exemple 3 : Pipeline avec validation seule

```
Description: Détection de scènes exactes
Mode: hybrid | Méthodes: 3
Features: ✓ Validation longueur
```

---

## 🎯 Cas d'usage

### 1. Utilisateur débutant

**Besoin** : Utiliser un preset optimisé

**Workflow** :
1. Ouvre l'onglet Paramètres
2. Voit la section "Pipeline DuplicateFlow"
3. Sélectionne "⭐ Fast Duplicate Detection" dans la combo
4. Lit la description et les features
5. Lance l'analyse

**Avantage** : Pipeline pré-configuré avec validation et analyse partielle

---

### 2. Utilisateur avancé

**Besoin** : Créer un pipeline personnalisé

**Workflow** :
1. Clique sur "➕ Nouveau"
2. Configure dans l'éditeur :
   - Nom: "Mon pipeline HD"
   - Mode: filtering
   - Méthodes: frame_hash + color_histogram
   - **Active validation longueur : ±3% OU ±20s**
   - **Active analyse partielle : 45s depuis le début**
3. Sauvegarde
4. Le pipeline apparaît dans la liste (sans ⭐)
5. Peut le modifier à tout moment

---

### 3. Utilisateur expert

**Besoin** : Adapter un preset existant

**Workflow** :
1. Sélectionne un preset par défaut (ex: "⭐ Balanced")
2. Essaye de cliquer "✏️ Éditer"
3. **Message** : "Ce pipeline est un pipeline par défaut..."
4. Clique "➕ Nouveau" à la place
5. Configure un pipeline similaire mais personnalisé
6. Sauvegarde sous un nouveau nom
7. Peut maintenant l'éditer librement

---

## ✅ Avantages

### Pour l'utilisateur

1. **Visibilité** : Tous les pipelines au même endroit
2. **Description** : Comprendre chaque pipeline sans l'ouvrir
3. **Features** : Voir d'un coup d'œil les optimisations (validation, analyse partielle)
4. **Protection** : Impossible de modifier accidentellement un preset par défaut
5. **Flexibilité** : Créer autant de pipelines que nécessaire

### Pour le développeur

1. **Séparation** : Logique UI dans panels.py, callbacks dans main_window.py
2. **Réutilisable** : Méthodes `_reload_pipeline_combo()` appelable partout
3. **Extensible** : Facile d'ajouter d'autres boutons (Copier, Supprimer, etc.)
4. **Cohérent** : Utilise le même pattern que les autres sections

---

## 🔧 Prochaines Améliorations Possibles

### Court terme

- [ ] Bouton "📋 Copier" pour dupliquer un pipeline
- [ ] Bouton "🗑️ Supprimer" pour les pipelines personnalisés
- [ ] Icône visuelle pour chaque pipeline (selon le mode)
- [ ] Tri des pipelines (alphabétique, usage, etc.)

### Moyen terme

- [ ] Recherche/filtrage des pipelines
- [ ] Catégories de pipelines (Duplicates, Scènes, Audio, etc.)
- [ ] Import/Export de pipelines (fichiers JSON)
- [ ] Partage de pipelines entre utilisateurs

### Long terme

- [ ] Recommandation automatique de pipeline selon le contenu
- [ ] Statistiques d'utilisation par pipeline
- [ ] Benchmarking intégré
- [ ] Templates de pipelines

---

## 📝 Notes Techniques

### Gestion de la sélection

La méthode `_reload_pipeline_combo()` préserve la sélection actuelle lors du rechargement:

```python
# Remember current selection
current_name = None
current_index = self.pipeline_combo.currentIndex()
if current_index >= 0:
    current_data = self.pipeline_combo.itemData(current_index)
    if current_data:
        current_name = current_data.get('name')

# ... reload ...

# Restore selection
if current_name and pipeline['name'] == current_name:
    new_index = i
```

### Protection des presets

Les pipelines par défaut (`is_default=1`) sont protégés au niveau de l'UI:

```python
if pipeline_data.get('is_default', False):
    QMessageBox.warning(...)
    return
```

Et au niveau du `PipelineManager`:

```python
if is_default:
    raise ValueError(f"Impossible de modifier le pipeline par défaut '{current_name}'")
```

---

## 🎉 Résumé

Le sélecteur de pipeline est maintenant **complètement intégré** dans l'interface de duplicate_finder:

✅ **Section UI** dans l'onglet Paramètres
✅ **Combo box** avec tous les pipelines
✅ **Boutons** Éditer et Nouveau
✅ **Description dynamique** avec features
✅ **Callbacks** dans main_window.py
✅ **Protection** des pipelines par défaut
✅ **Rechargement** automatique après modifications

L'utilisateur peut maintenant **sélectionner, créer et éditer** des pipelines DuplicateFlow directement depuis l'interface principale, avec accès complet aux nouvelles fonctionnalités (validation de longueur et analyse partielle).

---

*Implémenté le 2025-12-18 par Claude Sonnet 4.5*
