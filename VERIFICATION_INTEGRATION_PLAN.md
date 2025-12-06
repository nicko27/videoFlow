# Plan d'Intégration de la Vérification de Sous-séquences

## 🎯 Objectif

Intégrer correctement la vérification Strategy 3 avec:
1. ✅ Les barres de progression existantes
2. ✅ Le système de cache de la base de données
3. ✅ Éviter les re-vérifications inutiles
4. ✅ Feedback utilisateur en temps réel

## 📊 Système Existant Analysé

### Barres de Progression
- `self.file_progress` - Hachage des fichiers
- `self.duplicate_progress` - Comparaison/détection
- `self.audio_progress` - Empreintes audio

### Système de Cache (Base de Données)
- Table: `video_files`
  - `file_path`, `modification_time`, `file_size`, `duration`, `hash`
- Détection de changements: `mtime` + `file_size`
- Cache intelligent évite re-calculs

### Workers Existants
- `ParallelHashWorker` - Hash vidéos en parallèle
- `ComparisonWorker` - Compare vidéos en parallèle
- `SubsequenceWorker` - Détecte sous-séquences (existe déjà!)

## ❌ Problèmes Actuels

1. **Pas de barre de progression pour la vérification**
   - La vérification bloque l'UI sans feedback

2. **Pas de cache des résultats de vérification**
   - Re-vérifie même si déjà fait

3. **Pas de signal de progression**
   - Impossible de suivre l'avancement

4. **Pas de stockage en DB**
   - Résultats perdus après fermeture

## ✅ Solution Proposée

### 1. Créer une Table de Cache pour la Vérification

```sql
CREATE TABLE verification_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    short_video_path TEXT NOT NULL,
    long_video_path TEXT NOT NULL,
    short_mtime REAL NOT NULL,
    long_mtime REAL NOT NULL,
    short_size INTEGER NOT NULL,
    long_size INTEGER NOT NULL,
    start_time REAL NOT NULL,
    duration REAL NOT NULL,
    sequence_score REAL NOT NULL,
    -- Résultats de vérification
    accepted BOOLEAN NOT NULL,
    scene_cuts_score REAL NOT NULL,
    dct_score REAL NOT NULL,
    rejection_reason TEXT,
    verification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(short_video_path, long_video_path, start_time)
);
```

### 2. Créer un VerificationWorker (PyQt6)

```python
class VerificationWorker(QThread):
    """Worker pour vérification en arrière-plan avec progression."""

    # Signaux
    progress = pyqtSignal(int, int, str)  # current, total, message
    verification_complete = pyqtSignal(dict)  # résultat
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, verifier, matches, db):
        super().__init__()
        self.verifier = verifier
        self.matches = matches
        self.db = db
        self._stop = False

    def run(self):
        for i, match in enumerate(self.matches):
            if self._stop:
                break

            # Vérifier cache d'abord
            cached = self.db.get_cached_verification(
                match['short_video'],
                match['long_video'],
                match['start_time']
            )

            if cached:
                self.progress.emit(i+1, len(self.matches),
                                  f"✓ Cached: {os.path.basename(match['short_video'])}")
                self.verification_complete.emit(cached)
                continue

            # Vérifier
            self.progress.emit(i+1, len(self.matches),
                             f"🔬 Verifying: {os.path.basename(match['short_video'])}")

            result = self.verifier.verify_with_strategy3(
                match['short_video'],
                match['long_video'],
                match['start_time'],
                match['duration'],
                match['sequence_score']
            )

            # Stocker en cache
            self.db.store_verification_result(match, result)

            self.verification_complete.emit(result)

        self.finished.emit()
```

### 3. Ajouter Barre de Progression "Verification"

Dans `ui/panels.py`:

```python
verification_progress = ModernProgressWidget("🎯 Subsequence Verification")
layout.addWidget(verification_progress)
```

Dans `main_window.py`:

```python
self.verification_progress = right_widgets.get('verification_progress')
```

### 4. Intégrer dans SubsequenceDetector

```python
class SubsequenceDetector:
    def find_subsequence(self, short_video, long_video, ...):
        # ... détection initiale ...

        if not is_subsequence:
            return {
                'is_subsequence': False,
                'verified': False,
                'verification_result': None
            }

        # PHASE 3: Vérification avec cache
        if self.enable_verification and self.verifier:
            # Vérifier cache d'abord
            cached = self.db.get_cached_verification(
                short_video, long_video, start_time
            )

            if cached:
                logger.info(f"✓ Using cached verification result")
                return {
                    'is_subsequence': cached['accepted'],
                    'verification_result': cached,
                    'verified': True,
                    'from_cache': True
                }

            # Vérifier (et mettre en cache)
            verification_result = self.verifier.verify_with_strategy3(...)

            # Stocker en cache
            self.db.store_verification_result(
                short_video, long_video, start_time,
                verification_result
            )

            return {
                'is_subsequence': verification_result['accepted'],
                'verification_result': verification_result,
                'verified': True,
                'from_cache': False
            }
```

### 5. Signaux de Progression

Connecter le VerificationWorker aux barres de progression:

```python
def start_verification(self, matches):
    self.verification_worker = VerificationWorker(
        self.verifier,
        matches,
        self.video_hasher.db
    )

    # Connecter signaux
    self.verification_worker.progress.connect(
        lambda c, t, m: self.verification_progress.update_progress(c, t, m)
    )

    self.verification_worker.verification_complete.connect(
        self.on_verification_complete
    )

    self.verification_worker.finished.connect(
        lambda: self.verification_progress.set_status("Complete", "#28A745")
    )

    self.verification_worker.start()
```

## 📈 Avantages

### Performance
- **Cache de DB**: Évite re-vérifications (gain ~5s par match)
- **Détection de changements**: mtime + file_size
- **Progression en temps réel**: Feedback utilisateur

### UX
- **Barre de progression dédiée**: Clarté visuelle
- **Messages informatifs**: "Cached", "Verifying", etc.
- **Annulation possible**: Bouton STOP fonctionne

### Fiabilité
- **Persistance**: Résultats sauvegardés en DB
- **Invalidation intelligente**: Re-vérifie si fichier modifié
- **Thread-safe**: PyQt6 QThread + signaux

## 🔄 Flux Complet

```
1. Utilisateur lance détection sous-séquences
   ↓
2. SubsequenceDetector trouve correspondances initiales
   ↓
3. Pour chaque correspondance:
   a. Vérifier cache DB (mtime + file_size)
   b. Si en cache ET fichiers non modifiés → Utiliser résultat
   c. Sinon → Vérifier avec Strategy 3
   d. Stocker résultat en DB
   ↓
4. Mettre à jour barre de progression en temps réel
   ↓
5. Signaler résultats via signaux Qt
   ↓
6. Afficher doublons vérifiés dans UI
```

## 🛠️ Modifications Nécessaires

### database_manager.py
```python
def store_verification_result(self, short_video, long_video, start_time, result):
    # Stocker résultat de vérification avec mtime/size

def get_cached_verification(self, short_video, long_video, start_time):
    # Récupérer résultat si fichiers non modifiés

def invalidate_verification_cache(self, video_path):
    # Invalider cache si fichier modifié
```

### subsequence_detector.py
```python
# Ajouter vérification de cache avant vérification
# Stocker résultats après vérification
```

### workers/verification_worker.py (nouveau)
```python
# Worker PyQt6 pour vérification en arrière-plan
```

### ui/panels.py
```python
# Ajouter verification_progress widget
```

### main_window.py
```python
# Connecter verification_worker aux signaux
# Mettre à jour verification_progress
```

## 📊 Estimation Impact

### Avant (sans cache)
- 1ère exécution: 10 matches × 5s = 50s
- 2ème exécution: 10 matches × 5s = 50s
- **Total: 100s**

### Après (avec cache)
- 1ère exécution: 10 matches × 5s = 50s
- 2ème exécution: 10 matches × 0.01s = 0.1s
- **Total: 50.1s** ⚡ **50% gain**

### Avec Progression
- Feedback en temps réel ✅
- Possibilité d'annulation ✅
- Clarté pour l'utilisateur ✅

## 🎯 Priorités d'Implémentation

1. **Critique** - Ajouter table `verification_cache` en DB
2. **Haute** - Créer `VerificationWorker` avec signaux
3. **Haute** - Intégrer cache dans `SubsequenceDetector`
4. **Moyenne** - Ajouter barre de progression UI
5. **Moyenne** - Connecter signaux dans `main_window.py`
6. **Basse** - Tests et optimisations

## 🔍 Tests Requis

1. Vérification initiale (sans cache)
2. Vérification avec cache (rapide)
3. Invalidation si fichier modifié
4. Annulation pendant vérification
5. Gestion des erreurs
6. Signaux de progression corrects

## 📝 Notes Importantes

- Utiliser **mtime + file_size** comme clé de cache (déjà utilisé ailleurs)
- Ne PAS recalculer si fichiers identiques
- Invalider cache si fichier déplacé/renommé
- Afficher "(cached)" dans messages de progression
- Permettre forcer re-vérification (option UI)

## 🚀 Résultat Final

Un système de vérification:
- ✅ Intégré avec UI existante
- ✅ Cache intelligent (évite re-calculs)
- ✅ Progression en temps réel
- ✅ Persistant (DB)
- ✅ Performant (multi-threaded)
- ✅ Fiable (détection de changements)

**Gain estimé**: 50% de temps sur exécutions répétées + UX grandement améliorée
