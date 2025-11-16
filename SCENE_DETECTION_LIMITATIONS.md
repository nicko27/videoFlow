# Scene Detection - Limitations et Solutions

## 🐛 Problème Actuel

La détection de scènes **fonctionne uniquement si la scène est au début de la vidéo longue**.

### Pourquoi ?

L'implémentation actuelle utilise une **comparaison de chaînes simplifiée** qui ne correspond pas à la vraie méthode de Chromaprint :

```python
# ❌ MAUVAISE APPROCHE (actuelle)
# Compare les fingerprints comme des strings
window = fp_long[i:i + window_size]
similarity = count_matching_chars(fp_short, window)
```

**Problèmes** :
1. Les fingerprints Chromaprint ne sont PAS linéaires dans le temps
2. On ne peut pas simplement extraire des sous-chaînes
3. La structure interne est compressée et encodée
4. Chromaprint utilise un algorithme de similarité spécifique

## ✅ Solution : Utiliser pyacoustid

La bibliothèque `pyacoustid` implémente correctement l'algorithme de comparaison de Chromaprint.

### Installation

```bash
# macOS
brew install chromaprint
pip3 install pyacoustid

# Linux
sudo apt install libchromaprint-dev
pip3 install pyacoustid

# Windows
pip3 install pyacoustid
# Installer chromaprint depuis: https://acoustid.org/chromaprint
```

### Vérification

```bash
python3 -c "import acoustid; print('acoustid OK')"
```

## 🔧 Approche Alternative (Sans pyacoustid)

Si vous ne pouvez pas installer pyacoustid, voici une approche alternative :

### Option 1 : Chunking Manuel

Découper la vidéo longue en segments et comparer chaque segment :

```bash
# Extraire un segment de 15 minutes commençant à 10:00
ffmpeg -i video_longue.mp4 -ss 00:10:00 -t 00:15:00 -c copy segment.mp4

# Extraire fingerprint
fpcalc segment.mp4

# Comparer avec fpcalc de la scène
```

**Avantages** :
- Simple à comprendre
- Fonctionne avec les outils existants

**Inconvénients** :
- Très lent (nécessite plusieurs extractions)
- Pas automatique

### Option 2 : Utiliser difflib (Python)

Comparer les fingerprints avec l'algorithme de similarité de séquence :

```python
import difflib

def compare_fingerprints(fp1, fp2):
    matcher = difflib.SequenceMatcher(None, fp1, fp2)
    return matcher.ratio()
```

**Avantages** :
- Ne nécessite pas de bibliothèque externe
- Meilleur que la comparaison caractère par caractère

**Inconvénients** :
- Toujours pas optimal pour Chromaprint
- Peut donner des faux positifs/négatifs

### Option 3 : Comparaison Basée sur la Durée

Heuristique simple :
- Si `dur_short / dur_long` est proche de la ratio attendu
- ET les premiers 30s de la scène matchent les premiers 30s d'un segment de la vidéo longue
- → C'est probablement une scène

## 🎯 Recommandation

**Pour une détection fiable de scènes au milieu des vidéos** :

1. **Installer pyacoustid** (recommandé)
   ```bash
   pip3 install pyacoustid
   ```

2. **Ou utiliser une alternative** :
   - Découper manuellement avec ffmpeg
   - Utiliser des outils spécialisés (video-duplicate-finder, etc.)

## 📊 État Actuel

| Cas | Fonctionne | Raison |
|-----|-----------|--------|
| Scène au début (0:00-15:00) | ✅ OUI | Position 0 = début de fingerprint |
| Scène au milieu (30:00-45:00) | ❌ NON | Fenêtre glissante ne fonctionne pas correctement |
| Scène à la fin | ❌ NON | Même problème |

## 🔮 Prochaine Version

Je vais implémenter une version améliorée qui :

1. ✅ Utilise `pyacoustid` si disponible
2. ✅ Fallback vers `difflib.SequenceMatcher` sinon
3. ✅ Affiche un avertissement si pyacoustid n'est pas installé
4. ✅ Guide l'utilisateur vers l'installation

## 💡 Workaround Temporaire

En attendant une vraie implémentation :

### Pour détecter une scène au milieu

1. **Découper la vidéo longue** en chunks de 15-60 minutes
2. **Extraire fingerprints** pour chaque chunk
3. **Comparer** avec le fingerprint de la scène
4. Si match > 85%, c'est probablement cette scène

**Script Bash** :

```bash
#!/bin/bash
# Découper video_longue.mp4 en chunks de 15 minutes

DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 video_longue.mp4)
CHUNK_SIZE=900  # 15 minutes en secondes

for ((i=0; i<$DURATION; i+=$CHUNK_SIZE)); do
    HH=$(printf "%02d" $((i/3600)))
    MM=$(printf "%02d" $(((i%3600)/60)))
    SS=$(printf "%02d" $((i%60)))

    ffmpeg -i video_longue.mp4 -ss $HH:$MM:$SS -t 00:15:00 -c copy chunk_${i}.mp4
    fpcalc chunk_${i}.mp4 > chunk_${i}_fp.txt
done

# Comparer avec scene.mp4
fpcalc scene.mp4 > scene_fp.txt
```

## 📚 Références

- **Chromaprint** : https://acoustid.org/chromaprint
- **pyacoustid** : https://github.com/beetbox/pyacoustid
- **Algorithme** : https://oxygene.sk/2011/01/how-does-chromaprint-work/

---

## ⚠️ Important

La détection de scènes par audio fingerprinting est **complexe**. Pour des résultats fiables :

1. **Installez pyacoustid** (recommandé fortement)
2. **Ou acceptez les limitations** de l'approche simplifiée
3. **Ou utilisez le découpage manuel** pour les cas critiques
