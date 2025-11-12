# 🔧 Guide d'Intégration Rapide - Batch Renamer V2.0

**Temps estimé:** 15-20 minutes
**Difficulté:** Facile ⭐

---

## 📋 ÉTAPES D'INTÉGRATION

### ✅ Étape 1: Vérifier les Fichiers (FAIT)

Tous les fichiers suivants sont déjà créés:

```
batch_renamer/
├── advanced_pattern_parser.py      ✅ CRÉÉ
├── enhanced_renamer.py              ✅ CRÉÉ
├── metadata_worker.py               ✅ CRÉÉ
├── enhanced_ui_additions.py         ✅ CRÉÉ
├── window.py                        ✅ MODIFIÉ (imports)
├── ENHANCEMENTS_README.md           ✅ CRÉÉ
├── INTEGRATION_GUIDE.md             ✅ CE FICHIER
└── TEST_EXAMPLES.py                 ✅ CRÉÉ
```

---

### 🔨 Étape 2: Copier les Méthodes UI

Ouvrez `enhanced_ui_additions.py` et copiez toutes les méthodes dans `window.py` **après** la dernière méthode existante (après `closeEvent`).

**Méthodes à copier (11 au total):**

1. `dragEnterEvent(self, event)`
2. `dropEvent(self, event)`
3. `extract_metadata_batch_threaded(self)`
4. `on_metadata_progress(self, current, total, filename)`
5. `on_metadata_finished(self, metadata)`
6. `on_metadata_error(self, error_msg)`
7. `show_dry_run_dialog(self)`
8. `redo_last(self)`
9. `update_undo_redo_buttons(self)`
10. `show_history_dialog(self)`
11. `show_advanced_pattern_help(self)`
12. `setup_table_sorting(self)`

**Note:** Les imports nécessaires sont déjà ajoutés dans window.py.

---

### 🎨 Étape 3: Modifier init_ui()

Trouvez la section "Action buttons" dans `init_ui()` (ligne ~182) et ajoutez les nouveaux boutons:

```python
# Action buttons
action_layout = QHBoxLayout()

# Bouton Dry Run (NOUVEAU)
dry_run_btn = QPushButton("🔬 Dry Run")
dry_run_btn.clicked.connect(self.show_dry_run_dialog)
dry_run_btn.setStyleSheet("""
    QPushButton {
        background-color: #007bff;
        color: white;
        padding: 10px;
        font-weight: bold;
        border-radius: 5px;
    }
    QPushButton:hover {
        background-color: #0056b3;
    }
""")
action_layout.addWidget(dry_run_btn)

# Bouton Rename All (EXISTANT)
self.rename_btn = QPushButton("✏️ Rename All")
# ... (reste inchangé)

# Bouton Undo (EXISTANT)
self.undo_btn = QPushButton("↶ Undo Last")
# ... (reste inchangé)

# Bouton Redo (NOUVEAU)
self.redo_btn = QPushButton("↷ Redo")
self.redo_btn.setEnabled(False)
self.redo_btn.clicked.connect(self.redo_last)
action_layout.addWidget(self.redo_btn)

# Bouton History (NOUVEAU)
history_btn = QPushButton("📜 History")
history_btn.clicked.connect(self.show_history_dialog)
action_layout.addWidget(history_btn)

action_layout.addStretch()

# Bouton Close (EXISTANT - déplacer ici)
close_btn = QPushButton("✖ Close")
close_btn.clicked.connect(self.close)
action_layout.addWidget(close_btn)

main_layout.addLayout(action_layout)
```

---

### 🔧 Étape 4: Ajouter Checkbox Patterns Avancés

Dans `init_ui()`, après la ligne "Variables help" (ligne ~140), ajoutez:

```python
# Variables help
variables_label = QLabel("Variables: {name} {ext} {date} {time} {resolution}...")
variables_label.setStyleSheet("color: gray; font-size: 10px;")
variables_label.setWordWrap(True)
options_layout.addWidget(variables_label)

# NOUVEAU: Checkbox et bouton help
advanced_layout = QHBoxLayout()

self.use_advanced_check = QCheckBox("Use Advanced Patterns")
self.use_advanced_check.setChecked(True)
self.use_advanced_check.setToolTip("Enable conditionals, transformations, and regex")
advanced_layout.addWidget(self.use_advanced_check)

help_btn = QPushButton("❓ Pattern Help")
help_btn.clicked.connect(self.show_advanced_pattern_help)
help_btn.setMaximumWidth(150)
advanced_layout.addWidget(help_btn)

advanced_layout.addStretch()
options_layout.addLayout(advanced_layout)
```

---

### ⚙️ Étape 5: Modifier update_preview()

Dans `update_preview()`, trouvez le bloc "Apply pattern if provided" (ligne ~349) et modifiez:

```python
# Apply pattern if provided
if pattern:
    metadata = self.metadata_cache.get(file_path, {})

    # NOUVEAU: Utiliser advanced parser si activé
    if self.use_advanced_check.isChecked():
        base_name = self.advanced_parser.parse(pattern, file_path, metadata, index)
    else:
        base_name = self.pattern_parser.parse(pattern, file_path, metadata, index)

    extension = Path(file_path).suffix
    new_name = f"{base_name}{extension}"
```

---

### 🧵 Étape 6: Modifier add_file_list()

Dans `add_file_list()`, remplacez l'appel à `extract_metadata_batch()` (ligne ~271):

```python
def add_file_list(self, files):
    """Add files to the table."""
    added_count = 0

    for file in files:
        if file not in self.files:
            self.files.append(file)
            added_count += 1

    if added_count > 0:
        # MODIFIÉ: Utiliser version threadée
        self.extract_metadata_batch_threaded()
        self.update_preview()
        self.rename_btn.setEnabled(True)
        logger.info(f"Added {added_count} files")
```

---

### 🔄 Étape 7: Modifier rename_all() et undo_last()

Dans `rename_all()`, ajouter l'update des boutons undo/redo (ligne ~440):

```python
# Enable undo
self.undo_btn.setEnabled(self.active_renamer.can_undo())

# NOUVEAU: Update redo button aussi
self.update_undo_redo_buttons()

# Update preview
self.update_preview()
```

Dans `undo_last()`, ajouter (ligne ~453):

```python
if success:
    QMessageBox.information(self, "Undo Complete", "Last rename operation undone")
    # MODIFIÉ: Utiliser la nouvelle méthode
    self.update_undo_redo_buttons()
```

---

### ✅ Étape 8: Initialiser Table Sorting

Dans `init_ui()`, après la création de `files_table` (ligne ~116):

```python
self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

# NOUVEAU: Activer tri
self.files_table.setSortingEnabled(True)

main_layout.addWidget(self.files_table)
```

---

## 🧪 ÉTAPE 9: TESTER

### Test 1: Lancer l'Application

```bash
cd /Users/nico/Documents/videoFlow
python3 main.py
```

**Vérifier:**
- ✅ L'application démarre sans erreur
- ✅ Le menu "Batch Renamer" est disponible
- ✅ La fenêtre s'ouvre correctement

### Test 2: Drag & Drop

**Actions:**
1. Glisser un fichier vidéo depuis le Finder
2. Le déposer dans la fenêtre

**Attendu:**
- ✅ Le fichier est ajouté à la table
- ✅ Progress bar s'affiche
- ✅ Métadonnées extraites en arrière-plan

### Test 3: Patterns Avancés

**Actions:**
1. Ajouter des fichiers
2. Cocher "Use Advanced Patterns"
3. Entrer pattern: `{name:upper}_{if:resolution==1920x1080}HD{endif}`
4. Voir preview

**Attendu:**
- ✅ Nom en majuscules
- ✅ "_HD" ajouté si résolution est 1920x1080

### Test 4: Dry Run

**Actions:**
1. Configurer pattern
2. Cliquer "Dry Run"

**Attendu:**
- ✅ Dialogue avec résultats simulation
- ✅ Nombres de succès/échecs affichés
- ✅ Aucun fichier réellement renommé

### Test 5: Undo/Redo

**Actions:**
1. Renommer quelques fichiers
2. Cliquer "Undo"
3. Cliquer "Redo"

**Attendu:**
- ✅ Undo restaure noms originaux
- ✅ Redo réapplique renommage
- ✅ Boutons s'activent/désactivent correctement

### Test 6: Historique

**Actions:**
1. Après avoir renommé
2. Cliquer "📜 History"

**Attendu:**
- ✅ Dialogue avec liste transactions
- ✅ Timestamps, noms old/new affichés
- ✅ Statut succès/échec indiqué

### Test 7: Pattern Help

**Actions:**
1. Cliquer "❓ Pattern Help"

**Attendu:**
- ✅ Dialogue d'aide s'ouvre
- ✅ Onglets "Basic" et "Advanced" disponibles
- ✅ Exemples affichés correctement

---

## 🐛 DÉPANNAGE

### Problème: ImportError

**Erreur:**
```
ImportError: cannot import name 'AdvancedPatternParser'
```

**Solution:**
Vérifier que les imports dans `window.py` sont corrects (lignes 16-22).

---

### Problème: AttributeError sur self.advanced_parser

**Erreur:**
```
AttributeError: 'BatchRenamerWindow' object has no attribute 'advanced_parser'
```

**Solution:**
Vérifier que l'initialisation dans `__init__()` inclut:
```python
self.advanced_parser = AdvancedPatternParser()
```

---

### Problème: Méthode non trouvée

**Erreur:**
```
AttributeError: 'BatchRenamerWindow' object has no attribute 'show_dry_run_dialog'
```

**Solution:**
Vérifier que les méthodes de `enhanced_ui_additions.py` ont été copiées dans `window.py`.

---

### Problème: Progress bar ne s'affiche pas

**Cause:** La progress bar est créée dynamiquement.

**Solution:**
Vérifier que `extract_metadata_batch_threaded()` est bien appelée et que les signaux du worker sont connectés.

---

## ✅ CHECKLIST POST-INTÉGRATION

- [ ] Application démarre sans erreur
- [ ] Drag & Drop fonctionne
- [ ] Metadata extraction threadée fonctionne
- [ ] Progress bar s'affiche
- [ ] Patterns avancés fonctionnent (conditionnels, transformations)
- [ ] Dry Run fonctionne
- [ ] Undo fonctionne
- [ ] Redo fonctionne
- [ ] Historique s'affiche
- [ ] Pattern Help s'affiche
- [ ] Tri de table fonctionne
- [ ] Patterns persistent entre sessions (déjà implémenté)
- [ ] Détection de patterns fonctionne (déjà implémenté)

---

## 📞 SUPPORT

### En Cas de Problème

1. **Vérifier les logs:**
   ```bash
   cat ~/.videoflow/batch_renamer/logs/session_*.json
   ```

2. **Vérifier la compilation:**
   ```bash
   cd /Users/nico/Documents/videoFlow/src/plugins/batch_renamer
   python3 -m py_compile *.py
   ```

3. **Exécuter les tests:**
   ```bash
   python3 TEST_EXAMPLES.py
   ```

---

## 🎉 FÉLICITATIONS !

Une fois toutes les étapes complétées, vous aurez un **Batch Renamer v2.0** avec:

✅ Patterns avancés (conditions, transformations, regex)
✅ UX moderne (drag-drop, threading)
✅ Sécurité (dry-run, undo/redo, logging)
✅ Persistance (patterns sauvegardés)
✅ Détection intelligente (auto-detect patterns)

**Profitez de votre nouveau plugin amélioré !** 🚀
