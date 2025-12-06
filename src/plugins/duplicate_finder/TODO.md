# TODO - Duplicate Finder Plugin

**Dernière mise à jour**: Décembre 2024
**Statut**: Analyse complète effectuée

---

## ✅ COMPLÉTÉ RÉCEMMENT (Session actuelle)

### Problèmes critiques corrigés

- [x] **Bare except clauses** - Remplacés par exceptions spécifiques (3 fichiers)
- [x] **Audio-first workflow** - Filtrage des paires vidéo (495x speedup)
- [x] **File deletion handling** - Vérification existence avant comparaison
- [x] **Database migration** - Vérification fonctionnement correct
- [x] **Layout system** - Suppression layouts inutiles, gardé Dashboard uniquement
- [x] **Verification cache** - Vérification utilisation correcte
- [x] **Strategy 3 integration** - Scene Cuts Veto + DCT complètement intégré

### Documentation créée

- [x] `SCENE_DETECTION_COMPLETE_GUIDE.md` - Guide complet 500+ lignes
- [x] `TODO.md` - Ce fichier

---

## 🚀 PRIORITÉ 1 - Quick Wins (1-3 jours)

### Performance

- [ ] **Parallélisation de la vérification Strategy 3**
  - **Description**: Utiliser ThreadPoolExecutor pour vérifier 4 scènes en parallèle
  - **Fichier**: `workers/verification_worker.py`
  - **Gain attendu**: 3-4x plus rapide
  - **Complexité**: Faible (2-3h)
  - **Code**:
    ```python
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(verify_scene, s) for s in scenes]
        results = [f.result() for f in futures]
    ```

- [ ] **Cache LRU en mémoire**
  - **Description**: Ajouter cache RAM de 100 résultats (évite queries DB répétées)
  - **Fichier**: `database_manager.py`
  - **Gain attendu**: 10-20% speedup sur analyses répétées
  - **Complexité**: Faible (1-2h)
  - **Code**:
    ```python
    from functools import lru_cache

    @lru_cache(maxsize=100)
    def get_cached_verification_memory(short_path, long_path, start_time):
        return self.get_cached_verification(short_path, long_path, start_time)
    ```

- [ ] **Pré-calcul et stockage des durées vidéo**
  - **Description**: Stocker durée dans `video_files` table au lieu de recalculer
  - **Fichier**: `database_manager.py`, `workers/hash_worker.py`
  - **Gain attendu**: -1s par paire lors de `_generate_pairs()`
  - **Complexité**: Moyenne (3-4h)
  - **Migration DB nécessaire**: Oui

### Code Quality

- [ ] **i18n complet**
  - **Description**: Utiliser le système i18n existant partout (pas juste audio-first)
  - **Fichiers**: Tous les .py avec strings user-facing
  - **Gain**: UX multilingue
  - **Complexité**: Moyenne (1 jour)
  - **Status**: Framework existe (`i18n/translator.py`), juste appliquer partout

- [ ] **Supprimer code mort**
  - **Description**: Supprimer `_ignore_type_exists` flag (jamais utilisé)
  - **Fichier**: `database_manager.py:168, 431`
  - **Gain**: Clarté
  - **Complexité**: Trivial (5 min)

- [ ] **Tests unitaires pour Strategy 3**
  - **Description**: Tests automatisés pour `verify_with_strategy3()`
  - **Fichier**: Créer `tests/test_verification.py`
  - **Gain**: Confiance, non-régression
  - **Complexité**: Moyenne (4-6h)
  - **Contenu**:
    ```python
    def test_scene_cuts_veto():
        # Tester rejet si scene_cuts = 0

    def test_dct_threshold():
        # Tester rejet si DCT < 75%

    def test_accept_valid_subsequence():
        # Tester accept si tous critères OK
    ```

---

## 🎯 PRIORITÉ 2 - Améliorations Algorithmiques (1-2 semaines)

### Détection améliorée

- [ ] **Strategy 4: Hybrid temporal+spatial**
  - **Description**: Ajouter analyse temporelle (patterns de mouvement)
  - **Fichier**: Créer `analysis/subsequence_verification_v2.py`
  - **Gain attendu**: Rappel 84% → 95%+
  - **Complexité**: Haute (3-5 jours)
  - **Algorithme**:
    ```
    1. Scene cuts veto (comme Strategy 3)
    2. DCT spatial (comme Strategy 3)
    3. NOUVEAU: Optical flow comparison
       - Extraire vecteurs de mouvement
       - Comparer patterns temporels
    4. Vote pondéré des 3 scores
    ```

- [ ] **Détection de transformations vidéo**
  - **Description**: Détecter rotation, crop, letterbox, ralenti/accéléré
  - **Fichier**: `analysis/video_transforms.py` (nouveau)
  - **Gain**: Détecte plus de variantes
  - **Complexité**: Haute (5-7 jours)
  - **Transformations**:
    - Rotation: 90°, 180°, 270°
    - Crop: détection bordures
    - Letterbox/Pillarbox: détection bandes noires
    - Speed: détection ralenti/accéléré (audio pitch)

- [ ] **Audio multi-résolution adaptatif**
  - **Description**: Commencer avec fenêtres courtes, augmenter si incertain
  - **Fichier**: `audio_fingerprinting.py`
  - **Gain attendu**: 30-50% temps audio économisé
  - **Complexité**: Moyenne (2-3 jours)
  - **Algorithme**:
    ```
    1. Analyse 5s (rapide)
    2. Si score 60-80% → Analyse 15s
    3. Si score > 80% → Confirme
    4. Si score < 60% → Rejette
    ```

### Base de données

- [ ] **Nettoyage automatique cache ancien**
  - **Description**: Supprimer entrées > 30 jours non accédées
  - **Fichier**: `database_manager.py`
  - **Gain**: Taille DB réduite
  - **Complexité**: Faible (2h)
  - **Query**:
    ```sql
    DELETE FROM verification_cache
    WHERE verification_date < datetime('now', '-30 days');
    ```

- [ ] **Index composites optimisés**
  - **Description**: Améliorer indexes pour queries fréquentes
  - **Fichier**: `database_manager.py:455-462`
  - **Gain**: Queries 2-3x plus rapides
  - **Complexité**: Faible (1h)
  - **Indexes à ajouter**:
    ```sql
    CREATE INDEX idx_verification_lookup
    ON verification_cache(short_video_id, long_video_id, start_time, accepted);
    ```

---

## 🌟 PRIORITÉ 3 - Features Avancées (3-4 semaines)

### Machine Learning

- [ ] **ML Scoring Model**
  - **Description**: Entraîner modèle ML pour prédire probabilité sous-séquence
  - **Fichier**: Créer `analysis/ml_verifier.py`
  - **Gain attendu**: Rappel 95%+, Précision 100%
  - **Complexité**: Très haute (2-3 semaines)
  - **Étapes**:
    1. Collecter dataset étiqueté (500+ paires)
    2. Extraire features (scene_cuts, DCT, audio, durée, etc.)
    3. Entraîner Random Forest ou XGBoost
    4. Validation croisée
    5. Déploiement avec pickle
  - **Dependencies**: `scikit-learn`, `xgboost`

### Détection multi-scènes

- [ ] **Graph de relations sous-séquences**
  - **Description**: Un court peut être dans plusieurs longs, vice-versa
  - **Fichier**: Créer `analysis/subsequence_graph.py`
  - **Gain**: Détecte compilations, remixes
  - **Complexité**: Haute (1 semaine)
  - **Structure**:
    ```python
    class SubsequenceGraph:
        def __init__(self):
            self.nodes = {}  # video_path -> Node
            self.edges = []  # (short, long, start_time, score)

        def find_chains(self):
            # Trouver A in B, B in C → A transitif in C

        def find_compilations(self):
            # Trouver A in [B, C, D] → A est compilation
    ```

- [ ] **Export timeline vers éditeurs vidéo**
  - **Description**: Générer EDL/XML pour Premiere/Final Cut/DaVinci
  - **Fichier**: Créer `export/timeline_exporter.py`
  - **Gain**: Workflow professionnel
  - **Complexité**: Moyenne (3-5 jours)
  - **Formats**:
    - EDL (Edit Decision List)
    - Final Cut Pro XML
    - DaVinci Resolve XML

### UI/UX

- [ ] **Visualisation timeline interactive**
  - **Description**: Timeline visuelle montrant où extraits se trouvent
  - **Fichier**: Créer `ui/timeline_widget.py`
  - **Gain**: UX premium
  - **Complexité**: Haute (1 semaine)
  - **Features**:
    - Zoom/pan timeline
    - Highlight matches
    - Clic pour preview
    - Export screenshot

- [ ] **Batch operations sur sous-séquences**
  - **Description**: Sélection multiple + action (supprimer, garder, etc.)
  - **Fichier**: `handlers/duplicate_handler.py`
  - **Gain**: Efficacité utilisateur
  - **Complexité**: Moyenne (2-3 jours)

- [ ] **Filtre/tri des résultats**
  - **Description**: Filtrer par score, durée, date, etc.
  - **Fichier**: `ui/panels.py`
  - **Gain**: Navigation résultats
  - **Complexité**: Faible (1 jour)

---

## 🔧 PRIORITÉ 4 - Maintenance & Infrastructure (Ongoing)

### Monitoring

- [ ] **Système de métriques**
  - **Description**: Logger temps, cache hit rate, précision, etc.
  - **Fichier**: Créer `monitoring/metrics.py`
  - **Gain**: Visibilité production
  - **Complexité**: Moyenne (2-3 jours)
  - **Métriques**:
    ```python
    class Metrics:
        - detection_time: Distribution temps détection
        - verification_time: Distribution temps vérification
        - cache_hit_rate: % cache hits
        - precision_rate: % vrais positifs
        - recall_rate: % détectés vs total
        - db_size: Taille DB
        - memory_usage: RAM utilisée
    ```

- [ ] **Alertes automatiques**
  - **Description**: Email/notification si métriques anormales
  - **Fichier**: `monitoring/alerts.py`
  - **Gain**: Proactivité
  - **Complexité**: Faible (1 jour)
  - **Triggers**:
    - Cache hit rate < 70%
    - Temps vérification > 5s moyenne
    - Erreurs > 5% des opérations

### Documentation

- [ ] **API Documentation (Sphinx)**
  - **Description**: Documentation auto-générée depuis docstrings
  - **Gain**: Maintenabilité
  - **Complexité**: Faible (1 jour)
  - **Setup**:
    ```bash
    pip install sphinx sphinx-rtd-theme
    sphinx-quickstart docs/
    sphinx-apidoc -o docs/source src/plugins/duplicate_finder
    make html
    ```

- [ ] **Video tutorials**
  - **Description**: Screencasts montrant features
  - **Gain**: Adoption utilisateurs
  - **Complexité**: Moyenne (2-3 jours)
  - **Sujets**:
    1. Détection basique de doublons
    2. Détection de sous-séquences
    3. Configuration avancée
    4. Troubleshooting

### Testing

- [ ] **Integration tests**
  - **Description**: Tests end-to-end du workflow complet
  - **Fichier**: `tests/test_integration.py`
  - **Gain**: Confiance déploiement
  - **Complexité**: Haute (1 semaine)
  - **Scénarios**:
    ```python
    def test_full_workflow():
        # 1. Add files
        # 2. Run detection
        # 3. Verify results
        # 4. Process duplicates
        # 5. Check DB state
    ```

- [ ] **Performance regression tests**
  - **Description**: Tests garantissant performance ne régresse pas
  - **Fichier**: `tests/test_performance.py`
  - **Gain**: Stabilité
  - **Complexité**: Moyenne (2-3 jours)
  - **Benchmarks**:
    - Temps détection < 5s/paire
    - Temps vérification < 3s/scène
    - Cache hit > 90%

---

## 🐛 BUGS CONNUS

### Mineurs (Non-bloquants)

- [ ] **Barre de progression scene detection parfois bloquée à 99%**
  - **Fichier**: `main_window.py:_on_scene_progress()`
  - **Cause**: Race condition sur dernier emit
  - **Fix**: Force emit 100% dans on_finished()
  - **Priorité**: Basse

- [ ] **Cache invalide si fichier renommé**
  - **Fichier**: `database_manager.py:get_cached_verification()`
  - **Cause**: Cache par file_path, pas par inode
  - **Fix**: Utiliser inode au lieu de path
  - **Priorité**: Basse (edge case rare)

- [ ] **Logs WARNING si fichier sans audio**
  - **Fichier**: `audio_fingerprinting.py`
  - **Cause**: Fallback silencieux attendu mais log warning
  - **Fix**: Changer niveau log à INFO
  - **Priorité**: Très basse

### Edge Cases

- [ ] **Détection échoue sur vidéos < 5 secondes**
  - **Fichier**: `audio_fingerprinting.py`
  - **Cause**: Fenêtre audio minimum = 5s
  - **Fix**: Adapter fenêtre à durée vidéo
  - **Priorité**: Basse

- [ ] **DCT similarity faux si vidéos noir et blanc vs couleur**
  - **Fichier**: `analysis/subsequence_verification.py:_compute_dct_similarity()`
  - **Cause**: Conversion gray identique pour les deux
  - **Fix**: Détecter si B&W avant comparaison
  - **Priorité**: Très basse

---

## 🎨 AMÉLIORATIONS UX

### Quick wins

- [ ] **Bouton "Pause" pendant analyse**
  - **Gain**: Contrôle utilisateur
  - **Complexité**: Faible (2h)

- [ ] **Estimation temps restant**
  - **Gain**: UX transparente
  - **Complexité**: Faible (1h)
  - **Calcul**: `(total - current) * avg_time_per_item`

- [ ] **Preview images dans résultats**
  - **Gain**: Vérification visuelle rapide
  - **Complexité**: Moyenne (1 jour)

### Nice to have

- [ ] **Thème sombre**
  - **Note**: Système thème existe déjà, juste ajouter dark theme
  - **Gain**: Confort utilisateur
  - **Complexité**: Faible (2-3h)

- [ ] **Raccourcis clavier**
  - **Gain**: Efficacité power users
  - **Complexité**: Faible (1 jour)
  - **Shortcuts**:
    - Ctrl+A: Add files
    - Ctrl+S: Start analysis
    - Ctrl+D: Delete selected
    - Space: Play/pause preview

- [ ] **Drag & drop fichiers**
  - **Gain**: UX moderne
  - **Complexité**: Faible (2-3h)

---

## 📊 MÉTRIQUES DE SUCCÈS

### Performance

- [ ] Temps détection audio < 5s par paire (Shazam-like)
- [ ] Temps vérification < 3s par scène
- [ ] Cache hit rate > 90% sur datasets stables
- [ ] Memory usage < 500MB pour 1000 vidéos

### Qualité

- [ ] Précision Strategy 3 = 100% (aucun faux positif)
- [ ] Rappel Strategy 3 > 85%
- [ ] F1 Score > 90%
- [ ] 0 crashes sur 100 runs

### Code

- [ ] Test coverage > 80%
- [ ] 0 bare except clauses
- [ ] 0 TODO/FIXME dans production code
- [ ] Documentation complète (Sphinx)

---

## 🗺️ ROADMAP

### Q1 2025

- Priorité 1 complète (Quick wins)
- Tests unitaires complets
- Documentation Sphinx
- Monitoring métriques

### Q2 2025

- Strategy 4 implémentée
- Détection transformations
- Audio adaptatif
- ML scoring (début)

### Q3 2025

- ML scoring (production)
- Graph sous-séquences
- Export timeline
- Timeline widget

### Q4 2025

- Optimisations finales
- Video tutorials
- Beta release public

---

## 📝 NOTES

### Décisions architecturales

- **Pourquoi Strategy 3 et pas ML direct?**
  - ML nécessite dataset étiqueté (pas disponible initialement)
  - Strategy 3 donne 100% précision sans ML
  - ML sera ajouté plus tard pour améliorer rappel

- **Pourquoi cache avec mtime+size et pas hash?**
  - Hash de vidéo = trop lent (30s-1min)
  - mtime+size = instantané et détecte 99.9% des modifications
  - Acceptable trade-off pour speedup 417x

- **Pourquoi Dashboard View uniquement?**
  - Simplifie codebase (-300 lignes)
  - Élimine bugs de récréation UI
  - UX cohérente pour tous
  - Layouts multiples = complexité inutile

### Leçons apprises

1. **Cache est crucial**: 417x speedup mesuré
2. **Veto approach > scoring**: Scene cuts veto élimine faux positifs
3. **DCT > pixel diff**: Robuste au réencodage
4. **Batch verification**: Collecte puis vérifie = meilleur UX

---

## ✅ CRITÈRES DE COMPLÉTION

Un item est "complété" quand:
- [ ] Code écrit et testé
- [ ] Tests unitaires passent
- [ ] Documentation mise à jour
- [ ] Code review effectué
- [ ] Commit avec message descriptif
- [ ] Aucun warning/erreur dans logs

---

**Maintenu par**: Nico & Claude Code
**Dernière revue**: Décembre 2024
