# 🚀 Guide d'Implémentation des Algorithmes de Comparaison

**Date:** 2025-11-16
**Contexte:** 2000+ fichiers = ~2 millions de comparaisons avec l'algorithme naïf actuel

---

## ✅ Ce Qui Est Déjà Fait

### **Sélecteur dans l'UI**
Un nouveau groupe **"🚀 Comparison Algorithm"** a été ajouté dans l'onglet Settings avec 4 choix:

1. **Naïve** (All pairs - Slow, 100% accurate) - Actuel
2. **Ball Tree** (Fast, 100% accurate) - Recommandé par défaut ⭐
3. **Annoy** (Very fast, ~98% accurate) - Pour 1000-10000 fichiers
4. **FAISS** (Ultra fast, ~95-99% accurate) - Pour 2000+ fichiers

### **Persistance**
- Sauvegarde automatique dans QSettings
- Chargement au démarrage
- Valeur par défaut: **Ball Tree** (bon compromis)

### **Intégration**
- Widget ajouté dans `ui/panels.py`
- Références dans `main_window.py`
- Save/load dans `settings_manager.py`
- Disponible dans `config['comparison_algorithm']`

---

## 📦 Dépendances à Installer

```bash
# Ball Tree (déjà disponible si sklearn installé)
pip install scikit-learn

# Annoy
pip install annoy

# FAISS (CPU version)
pip install faiss-cpu

# FAISS (GPU version - si GPU CUDA disponible)
pip install faiss-gpu
```

---

## 🏗️ Architecture à Créer

### **Fichier: `comparison_algorithms.py`** (nouveau)

```
src/plugins/duplicate_finder/comparison_algorithms.py
```

**Structure recommandée:**

```python
from abc import ABC, abstractmethod
from typing import List, Tuple, Callable, Optional
import numpy as np

class ComparisonAlgorithm(ABC):
    """Base class for comparison algorithms."""

    @abstractmethod
    def find_similar_pairs(
        self,
        hashes: List[Tuple[str, np.ndarray]],  # (path, hash)
        threshold: float,
        progress_callback: Optional[Callable] = None
    ) -> List[Tuple[str, str, float]]:  # (path1, path2, similarity)
        """Find all similar pairs above threshold."""
        pass

class NaiveComparison(ComparisonAlgorithm):
    """Current all-pairs comparison."""
    pass

class BallTreeComparison(ComparisonAlgorithm):
    """Ball Tree using sklearn."""
    pass

class AnnoyComparison(ComparisonAlgorithm):
    """Annoy approximate nearest neighbors."""
    pass

class FAISSComparison(ComparisonAlgorithm):
    """FAISS ultra-fast similarity search."""
    pass
```

---

## 🔄 Modification du Code Existant

### **1. Dans `workers/comparison_worker.py`**

**Actuellement:**
```python
# Ligne ~200-250
# Comparaison naïve de toutes les paires
for i in range(len(pairs)):
    for j in range(i+1, len(pairs)):
        similarity = compare_hashes(hash1, hash2)
        if similarity >= threshold:
            results.append((file1, file2, similarity))
```

**À modifier:**
```python
# Import du module
from ..comparison_algorithms import get_comparison_algorithm

# Dans run() ou compare_pairs()
def run(self):
    # ... code existant ...

    # Récupérer l'algorithme choisi
    algorithm_name = config.get('comparison_algorithm', 'balltree')
    algorithm = get_comparison_algorithm(algorithm_name)

    # Utiliser l'algorithme
    results = algorithm.find_similar_pairs(
        hashes=all_hashes,
        threshold=threshold,
        progress_callback=self.progress_callback
    )

    # ... traiter les résultats ...
```

---

## 📝 Implémentation Détaillée

### **1. Naïve (Actuel) - Garder comme Fallback**

```python
class NaiveComparison(ComparisonAlgorithm):
    """All-pairs comparison - O(n²)."""

    def find_similar_pairs(self, hashes, threshold, progress_callback=None):
        results = []
        total = len(hashes) * (len(hashes) - 1) // 2
        count = 0

        for i in range(len(hashes)):
            for j in range(i+1, len(hashes)):
                path1, hash1 = hashes[i]
                path2, hash2 = hashes[j]

                # Calcul similarité (Hamming distance normalisée)
                similarity = 1.0 - (np.count_nonzero(hash1 != hash2) / len(hash1))

                if similarity >= threshold:
                    results.append((path1, path2, similarity))

                count += 1
                if progress_callback and count % 100 == 0:
                    progress_callback(count, total, f"{count}/{total}")

        return results
```

**Complexité:** O(n²)
**Avantages:** 100% précis, simple
**Inconvénients:** Très lent pour 1000+ fichiers

---

### **2. Ball Tree - Recommandé pour 100-2000 Fichiers**

```python
from sklearn.neighbors import BallTree

class BallTreeComparison(ComparisonAlgorithm):
    """Ball Tree spatial indexing - O(n log n)."""

    def find_similar_pairs(self, hashes, threshold, progress_callback=None):
        # Extraire paths et hashes
        paths = [h[0] for h in hashes]
        hash_array = np.array([h[1] for h in hashes], dtype=np.float32)

        # Construire le Ball Tree
        # Utiliser distance de Hamming
        tree = BallTree(hash_array, metric='hamming')

        # Convertir threshold en distance (1 - similarity)
        max_distance = 1.0 - threshold

        results = []

        # Pour chaque hash, trouver ses voisins
        for i, (path, hash_vec) in enumerate(hashes):
            # Query pour voisins dans le rayon
            indices = tree.query_radius(
                hash_vec.reshape(1, -1),
                r=max_distance,
                return_distance=False
            )[0]

            # Filtrer et calculer similarités exactes
            for j in indices:
                if j > i:  # Éviter doublons
                    similarity = 1.0 - (np.count_nonzero(hash_vec != hash_array[j]) / len(hash_vec))
                    if similarity >= threshold:
                        results.append((paths[i], paths[j], similarity))

            if progress_callback and i % 10 == 0:
                progress_callback(i, len(hashes), f"{i}/{len(hashes)}")

        return results
```

**Complexité:** O(n log n)
**Gain:** ~50x plus rapide
**Précision:** 100% (exact)
**Dépendance:** `scikit-learn`

**Pourquoi Ball Tree ?**
- Structure d'arbre qui partitionne l'espace
- Élimine automatiquement les branches éloignées
- Parfait pour Hamming distance
- Pas de perte de précision

---

### **3. Annoy - Pour 1000-10000 Fichiers**

```python
from annoy import AnnoyIndex

class AnnoyComparison(ComparisonAlgorithm):
    """Annoy approximate nearest neighbors - O(log n) per query."""

    def find_similar_pairs(self, hashes, threshold, progress_callback=None):
        paths = [h[0] for h in hashes]
        hash_array = np.array([h[1] for h in hashes], dtype=np.float32)

        n_items = len(hashes)
        f = hash_array.shape[1]  # Dimension

        # Créer l'index Annoy
        # Utiliser distance Hamming (angular pour bits)
        t = AnnoyIndex(f, 'hamming')

        # Ajouter tous les items
        for i, hash_vec in enumerate(hash_array):
            t.add_item(i, hash_vec)

        # Construire l'index (plus d'arbres = plus précis mais plus lent)
        n_trees = 50  # Bon compromis
        t.build(n_trees)

        results = []

        # Pour chaque hash, trouver ses k voisins les plus proches
        # k adaptatif selon taille dataset
        k = min(100, n_items)

        for i in range(n_items):
            # Trouver k voisins
            neighbors, distances = t.get_nns_by_item(
                i, k,
                include_distances=True
            )

            # Convertir distances en similarités et filtrer
            for j, dist in zip(neighbors, distances):
                if j > i:  # Éviter doublons
                    # Annoy retourne distance, on veut similarité
                    similarity = 1.0 - dist
                    if similarity >= threshold:
                        results.append((paths[i], paths[j], similarity))

            if progress_callback and i % 10 == 0:
                progress_callback(i, n_items, f"{i}/{n_items}")

        return results
```

**Complexité:** O(log n) par requête
**Gain:** ~200x plus rapide
**Précision:** ~98% (approximative)
**Dépendance:** `annoy`

**Pourquoi Annoy ?**
- Très rapide
- Faible empreinte mémoire
- Utilisé en production chez Spotify
- Peut sauvegarder l'index sur disque

**Paramètres à ajuster:**
- `n_trees`: Plus = précis mais lent (10-100)
- `k`: Nombre de voisins à chercher (50-200)

---

### **4. FAISS - Pour 2000+ Fichiers (Ultra-Rapide)**

```python
import faiss

class FAISSComparison(ComparisonAlgorithm):
    """FAISS ultra-fast similarity search."""

    def find_similar_pairs(self, hashes, threshold, progress_callback=None):
        paths = [h[0] for h in hashes]
        hash_array = np.array([h[1] for h in hashes], dtype=np.float32)

        n_items, dimension = hash_array.shape

        # Choisir l'index FAISS approprié
        if n_items < 10000:
            # IVF (Inverted File) pour datasets moyens
            nlist = min(100, n_items // 10)  # Nombre de clusters
            quantizer = faiss.IndexFlatL2(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, nlist)

            # Entraîner l'index
            index.train(hash_array)
        else:
            # HNSW pour très grands datasets
            M = 32  # Nombre de connexions
            index = faiss.IndexHNSWFlat(dimension, M)

        # Ajouter tous les vecteurs
        index.add(hash_array)

        results = []

        # Batch search pour performance
        batch_size = 100
        k = min(100, n_items)  # Nombre de voisins à chercher

        for start_idx in range(0, n_items, batch_size):
            end_idx = min(start_idx + batch_size, n_items)
            batch = hash_array[start_idx:end_idx]

            # Recherche des k voisins
            distances, indices = index.search(batch, k)

            # Traiter les résultats
            for i, (dist_row, idx_row) in enumerate(zip(distances, indices)):
                global_i = start_idx + i

                for dist, j in zip(dist_row, idx_row):
                    if j > global_i:  # Éviter doublons
                        # Convertir L2 distance en similarité
                        # Pour hashes binaires, distance L2 ≈ Hamming
                        similarity = 1.0 - (dist / dimension)

                        if similarity >= threshold:
                            results.append((paths[global_i], paths[j], similarity))

            if progress_callback:
                progress_callback(end_idx, n_items, f"{end_idx}/{n_items}")

        return results
```

**Complexité:** O(log n) à O(1) selon l'index
**Gain:** 100x à 1000x plus rapide
**Précision:** 95-99% (approximative)
**Dépendance:** `faiss-cpu` ou `faiss-gpu`

**Pourquoi FAISS ?**
- Développé par Facebook Research
- Le plus rapide disponible
- Support GPU natif
- Plusieurs types d'index optimisés
- Peut gérer des milliards de vecteurs

**Types d'index FAISS:**
- `IndexFlatL2`: Exact, lent (comme naïf)
- `IndexIVFFlat`: Bon pour 10K-1M vecteurs
- `IndexHNSWFlat`: Le plus rapide, excellent pour 1M+
- `IndexIVFPQ`: Le plus compact (compression)

**Avec GPU:**
```python
# Transférer sur GPU
res = faiss.StandardGpuResources()
gpu_index = faiss.index_cpu_to_gpu(res, 0, index)
# ... puis utiliser gpu_index.search()
```

---

## 🔌 Fonction Factory

```python
def get_comparison_algorithm(algorithm_name: str) -> ComparisonAlgorithm:
    """Factory pour obtenir l'algorithme approprié."""

    algorithms = {
        'naive': NaiveComparison,
        'balltree': BallTreeComparison,
        'annoy': AnnoyComparison,
        'faiss': FAISSComparison
    }

    if algorithm_name not in algorithms:
        logger.warning(f"Unknown algorithm '{algorithm_name}', using balltree")
        algorithm_name = 'balltree'

    try:
        return algorithms[algorithm_name]()
    except ImportError as e:
        logger.error(f"Cannot import {algorithm_name}: {e}")
        logger.warning("Falling back to naive comparison")
        return NaiveComparison()
```

**Gestion des erreurs:**
- Si bibliothèque manquante → fallback vers naïve
- Warning dans les logs
- Application continue de fonctionner

---

## 📊 Tableau Comparatif Final

| Algorithme | Complexité | Vitesse | Précision | RAM | GPU | Recommandé pour |
|------------|-----------|---------|-----------|-----|-----|-----------------|
| **Naïve** | O(n²) | 1x | 100% | Faible | Non | < 100 fichiers |
| **Ball Tree** | O(n log n) | 50x | 100% | Moyenne | Non | 100-2000 fichiers |
| **Annoy** | O(log n) | 200x | 98% | Faible | Non | 1000-10000 fichiers |
| **FAISS** | O(log n) | 1000x | 95-99% | Variable | Oui | 2000+ fichiers |

---

## 🎯 Recommandations par Taille de Dataset

### **< 100 fichiers**
→ **Naïve** ou **Ball Tree**
Raison: Différence négligeable, garder simplicité

### **100-1000 fichiers**
→ **Ball Tree** ⭐
Raison: 100% précis, 50x plus rapide, facile à utiliser

### **1000-5000 fichiers**
→ **Annoy** ou **FAISS**
Raison: Ball Tree devient lent, gains massifs

### **5000-20000 fichiers**
→ **FAISS CPU** ⭐
Raison: Optimisé pour cette échelle

### **20000+ fichiers**
→ **FAISS GPU**
Raison: Seule solution viable, utilise parallélisme GPU

---

## 🔧 Optimisations Supplémentaires

### **1. Caching des Index**
```python
# Sauvegarder l'index construit
if algorithm_name == 'faiss':
    faiss.write_index(index, "duplicate_finder.index")
    # Puis reload au lieu de rebuild
    index = faiss.read_index("duplicate_finder.index")
```

### **2. Batch Processing**
```python
# Ne pas charger tous les hashes en mémoire
# Traiter par lots de 1000-5000
```

### **3. Early Stopping**
```python
# Si k voisins trouvés et tous > seuil, arrêter
if len(results) >= expected_duplicates * 2:
    break
```

### **4. Parallel Processing**
```python
# FAISS et Annoy sont thread-safe en lecture
# Paralleliser les queries
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    # ... queries parallèles ...
```

---

## 🧪 Tests de Performance (Exemple avec 2000 Fichiers)

```
Naïve:       2,000,000 comparaisons → ~30 minutes ❌
Ball Tree:      ~40,000 comparaisons → ~30 secondes ⚠️
Annoy:          ~10,000 comparaisons → ~5 secondes ✅
FAISS (CPU):     ~5,000 comparaisons → ~2 secondes ⭐
FAISS (GPU):     ~5,000 comparaisons → ~0.5 secondes 🚀
```

---

## ✅ Checklist d'Implémentation

- [ ] Créer `comparison_algorithms.py`
- [ ] Implémenter `ComparisonAlgorithm` (classe de base)
- [ ] Implémenter `NaiveComparison`
- [ ] Implémenter `BallTreeComparison`
- [ ] Implémenter `AnnoyComparison`
- [ ] Implémenter `FAISSComparison`
- [ ] Créer `get_comparison_algorithm()` factory
- [ ] Modifier `comparison_worker.py` pour utiliser l'algorithme sélectionné
- [ ] Tester chaque algorithme séparément
- [ ] Comparer les performances
- [ ] Documenter les résultats

---

## 📝 Notes Importantes

1. **Compatibilité Windows/Mac/Linux:**
   - scikit-learn: ✅ Tous
   - annoy: ✅ Tous
   - faiss-cpu: ✅ Tous
   - faiss-gpu: ⚠️ Linux + CUDA uniquement

2. **Installation FAISS GPU:**
   ```bash
   # Vérifier CUDA
   nvidia-smi

   # Installer FAISS GPU
   conda install -c pytorch faiss-gpu
   ```

3. **Gestion Mémoire:**
   - Ball Tree: ~2x la taille des hashes
   - Annoy: ~1x la taille des hashes
   - FAISS IVF: ~1.5x
   - FAISS HNSW: ~3x

4. **Trade-off Précision/Vitesse:**
   - Annoy: Ajuster `n_trees` (10-100)
   - FAISS: Ajuster `nprobe` pour IVF (1-100)

---

**Statut:** ✅ **UI IMPLÉMENTÉE - PRÊT POUR IMPLÉMENTATION DES ALGORITHMES**
