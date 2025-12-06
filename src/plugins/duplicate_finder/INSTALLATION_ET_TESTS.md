# INSTALLATION ET TESTS - Corrections 2025-12-06

## 📦 INSTALLATION DES NOUVELLES DÉPENDANCES

### 1. Installer datasketch (CRITIQUE)

```bash
# Depuis le répertoire racine du projet
cd /Users/nico/Documents/videoFlow

# Installer les nouvelles dépendances
pip install datasketch>=1.6.0 librosa>=0.10.0 soundfile>=0.12.1

# Vérifier l'installation
python -c "import datasketch; print(f'datasketch version: {datasketch.__version__}')"
python -c "import librosa; print(f'librosa version: {librosa.__version__}')"
```

**Résultat attendu**:
```
datasketch version: 1.6.x
librosa version: 0.10.x
```

### 2. Installer toutes les dépendances (recommandé)

```bash
# Réinstaller toutes les dépendances depuis requirements.txt
pip install -r requirements.txt

# Vérifier qu'il n'y a pas d'erreurs
pip list | grep -E "(datasketch|librosa|soundfile)"
```

---

## 🧪 TESTS DE VALIDATION

### TEST #1: LSH Level 1 Fonctionnel ✅

**Objectif**: Vérifier que le Level 1 de l'analyse avancée retourne des candidats (pas 0)

**Procédure**:
1. Lancer l'application
2. Ajouter 20-50 fichiers vidéo
3. Choisir "Analyse Avancée (3 niveaux)"
4. Observer les logs pendant l'exécution

**Résultat attendu**:
```
Level 1 (LSH Audio) Results:
- Candidates found: 15 (ou tout nombre > 0)
- Time: 2.3s
```

**❌ ÉCHEC si**:
```
Level 1 (LSH Audio) Results:
- Candidates found: 0
- Message: "LSH analyzer not available - skipping Level 1"
```
→ Vérifier installation datasketch

---

### TEST #2: Timeout Scene Detection ✅

**Objectif**: Vérifier que la détection ne bloque pas indéfiniment

**Procédure**:
1. Créer ou trouver une vidéo avec audio corrompu/problématique
2. Lancer détection de scènes avec cette vidéo
3. Observer les logs et le comportement

**Résultat attendu**:
- Timeout après 300 secondes (5 minutes)
- Message dans logs: `"Scene detection timed out for {filename}"`
- Application reste responsive
- Passe à la vidéo suivante automatiquement

**❌ ÉCHEC si**:
- L'application se fige indéfiniment
- Impossible de fermer l'application
- Aucun message d'erreur dans les logs

---

### TEST #3: OpenCV Resource Cleanup ✅

**Objectif**: Vérifier qu'aucune fuite de file handles

**Procédure**:
1. Ouvrir le dialog de comparaison avec 2 vidéos
2. Attendre le chargement complet (2 previews visibles)
3. Fermer le dialog
4. Essayer de supprimer ou renommer l'une des vidéos

**Résultat attendu**:
- Fichiers vidéo immédiatement libérés
- Suppression/renommage possible sans erreur
- Aucun message "file in use" ou "permission denied"

**❌ ÉCHEC si**:
- Erreur "fichier utilisé par un autre processus"
- Impossible de supprimer même après fermeture dialog
- Nécessite fermeture complète de l'application

**macOS - Test avancé**:
```bash
# Avant d'ouvrir le dialog
lsof | grep -i "nom_du_fichier.mp4" | wc -l
# Devrait retourner 0

# Pendant que le dialog est ouvert
lsof | grep -i "nom_du_fichier.mp4" | wc -l
# Devrait retourner 1 (ou 2 pour les 2 vidéos)

# Après fermeture du dialog
lsof | grep -i "nom_du_fichier.mp4" | wc -l
# Devrait retourner 0 ✅
```

---

### TEST #4: Graceful Shutdown Verification ✅

**Objectif**: Vérifier que l'application se ferme rapidement même pendant verification

**Procédure**:
1. Lancer détection de scènes sur 20-30 paires de vidéos
2. Activer "Vérification Strategy 3"
3. Attendre que 2-3 vérifications soient complètes
4. Fermer l'application (CMD+Q sur macOS, Alt+F4 sur Windows)
5. Chronométrer le temps de fermeture

**Résultat attendu**:
- Fermeture en < 5 secondes
- Message dans logs: `"Verification stop requested"`
- Message dans logs: `"Verification cancelled at X/Y"`
- Aucun blocage ou freeze

**❌ ÉCHEC si**:
- Fermeture prend >10 secondes
- Application semble figée
- Pas de message "cancelled" dans logs
- Nécessite force quit

---

### TEST #5: Vérification Logs

**Objectif**: S'assurer que les logs montrent les améliorations

**Procédure**:
```bash
# Lancer l'app et observer la console
# ou lire les logs si configuré

# Chercher ces messages clés:
grep "Released video capture" logs.txt
grep "Verification stop requested" logs.txt
grep "Scene detection timed out" logs.txt
grep "Level 1 (LSH Audio) Results" logs.txt
```

**Messages attendus**:
```
[DEBUG] Released video capture for /path/to/video.mp4
[INFO] Verification stop requested
[INFO] Verification cancelled at 3/20
[ERROR] Scene detection timed out for long_video.mp4
[INFO] Level 1 (LSH Audio) Results: Candidates found: 15
```

---

## 🐛 DÉPANNAGE

### Problème: datasketch non trouvé

**Symptômes**:
```python
ModuleNotFoundError: No module named 'datasketch'
```

**Solution**:
```bash
# Vérifier pip
which pip
# Doit correspondre au Python utilisé par l'application

# Installer explicitement
pip install datasketch>=1.6.0

# Si problème persiste, utiliser python -m pip
python -m pip install datasketch>=1.6.0
```

---

### Problème: LSH retourne toujours 0 candidats

**Symptômes**:
```
Level 1 (LSH Audio) Results: Candidates found: 0
```

**Diagnostic**:
```python
# Tester dans Python
python
>>> import datasketch
>>> print(datasketch.__version__)
# Si erreur ici, datasketch pas installé

# Tester LSH
>>> from datasketch import MinHash
>>> m = MinHash()
>>> m.update("test".encode('utf8'))
>>> print(m.digest())
# Si erreur ici, problème avec datasketch
```

**Solution**:
1. Réinstaller datasketch: `pip install --force-reinstall datasketch`
2. Vérifier requirements.txt inclut bien `datasketch>=1.6.0`
3. Relancer l'application

---

### Problème: Timeout ne fonctionne pas (Windows)

**Symptômes**:
- Message dans logs: `"Timeout protection not available on this platform"`
- Détection bloque toujours

**Explication**:
- Le timeout utilise `signal.SIGALRM` (Unix/macOS uniquement)
- Windows n'a pas SIGALRM
- Graceful degradation: pas de timeout mais pas de crash

**Solution Windows** (à implémenter dans future version):
```python
# Utiliser threading.Timer au lieu de signal
import threading

def run_with_timeout(func, args, timeout):
    result = [None]
    def target():
        result[0] = func(*args)

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        # Thread encore vivant après timeout
        raise TimeoutError()

    return result[0]
```

---

### Problème: Fichiers toujours verrouillés après fermeture

**Symptômes**:
- Impossible de supprimer vidéo après comparaison
- Message "fichier utilisé"

**Diagnostic**:
```bash
# macOS/Linux
lsof /path/to/video.mp4

# Windows (PowerShell)
handle.exe video.mp4
```

**Solution**:
1. Vérifier que `closeEvent()` est bien appelé
2. Vérifier logs pour `"Released video capture"`
3. Si pas de log: ajouter debug dans `cleanup()`:
```python
def cleanup(self):
    print(f"[DEBUG] Cleaning up {self.video_path}")
    if self.cap is not None:
        self.cap.release()
        print(f"[DEBUG] Released {self.video_path}")
```

---

## ✅ CHECKLIST POST-INSTALLATION

- [ ] datasketch installé et importable
- [ ] librosa installé et importable
- [ ] soundfile installé et importable
- [ ] TEST #1 passé: LSH retourne candidats > 0
- [ ] TEST #2 passé: Timeout après 5 minutes
- [ ] TEST #3 passé: Fichiers libérés immédiatement
- [ ] TEST #4 passé: Fermeture <5 secondes
- [ ] TEST #5 passé: Logs montrent améliorations
- [ ] Aucune régression sur fonctionnalités existantes

---

## 📊 MÉTRIQUES DE SUCCÈS

### Performance
- ✅ LSH Level 1 génère candidats (gain 10x+)
- ✅ Aucune fuite mémoire sur 100+ comparaisons
- ✅ Fermeture app <5s en toutes circonstances

### Stabilité
- ✅ Aucun hang/freeze sur vidéos corrompues
- ✅ Aucun "file in use" après fermeture dialogs
- ✅ Aucun crash sur stop pendant verification

### User Experience
- ✅ Feedback visuel (logs) pour toutes opérations
- ✅ Annulation rapide et responsive
- ✅ Pas de perte de travail sur fermeture

---

## 🚀 PROCHAINES ÉTAPES

### Si tous les tests passent ✅
1. Committer les changements
2. Créer un tag de version (ex: v1.5.0-bugfixes)
3. Déployer en production
4. Monitorer logs utilisateurs

### Si des tests échouent ❌
1. Noter quels tests échouent
2. Vérifier les logs détaillés
3. Consulter FIXES_APPLIED.md pour comprendre la correction
4. Reporter le problème avec logs complets
5. Revenir à version précédente si critique

---

## 📝 RAPPORT DE TESTS

**Template à remplir après tests**:

```markdown
# RAPPORT DE TESTS - [DATE]

## Configuration
- OS: macOS / Windows / Linux
- Python version: 3.x.x
- datasketch version: x.x.x

## Résultats

### TEST #1: LSH Level 1
- ✅ / ❌ PASSÉ / ÉCHOUÉ
- Candidats trouvés: X
- Notes:

### TEST #2: Timeout
- ✅ / ❌ PASSÉ / ÉCHOUÉ
- Temps avant timeout: Xs
- Notes:

### TEST #3: OpenCV Cleanup
- ✅ / ❌ PASSÉ / ÉCHOUÉ
- lsof count après fermeture: X
- Notes:

### TEST #4: Graceful Shutdown
- ✅ / ❌ PASSÉ / ÉCHOUÉ
- Temps fermeture: Xs
- Notes:

### TEST #5: Logs
- ✅ / ❌ PASSÉ / ÉCHOUÉ
- Messages trouvés: ...
- Notes:

## Conclusion
- [ ] Tous les tests passent → VALIDATION ✅
- [ ] Des tests échouent → INVESTIGATION REQUISE ❌

## Problèmes rencontrés
1. ...
2. ...

## Actions requises
1. ...
2. ...
```

---

**BON COURAGE POUR LES TESTS!** 🚀
