# Interface Graphique - Détection de Sous-Vidéos

## 📍 Emplacement dans l'interface

L'interface de détection de sous-vidéos est accessible dans :

**Panneau gauche → Onglet "⚙️ Settings" → Groupe "🎬 Subsequence Detection (Optional)"**

## 🎛️ Contrôles disponibles

### 1. **Enable subsequence detection** (Checkbox)
- **Type** : Case à cocher
- **Par défaut** : Décochée (désactivé)
- **Description** : Active ou désactive la fonctionnalité de détection de sous-vidéos
- **Position** : En haut du groupe, en gras

### 2. **Sample interval** (SpinBox)
- **Type** : Double spin box
- **Plage** : 1.0 - 10.0 secondes
- **Par défaut** : 3.0 secondes
- **Suffixe** : " sec"
- **Tooltip** : "Interval between sampled frames (default: 3.0s)"
- **Description** : Contrôle l'intervalle d'échantillonnage des frames
  - Valeur basse (1-2s) → Plus précis, plus de mémoire
  - Valeur moyenne (3-5s) → Équilibre optimal
  - Valeur haute (5-10s) → Économie mémoire

### 3. **Min match ratio** (SpinBox)
- **Type** : Double spin box
- **Plage** : 70.0% - 95.0%
- **Par défaut** : 80.0%
- **Suffixe** : "%"
- **Tooltip** : "Minimum match ratio to consider a subsequence (default: 80%)"
- **Description** : Ratio minimum de correspondance pour détecter une sous-vidéo
  - 70-75% → Détection permissive
  - 80-85% → Équilibre recommandé
  - 90-95% → Détection stricte

### 4. **Cache memory limit** (SpinBox)
- **Type** : Spin box
- **Plage** : 100 - 2000 MB
- **Par défaut** : 500 MB
- **Suffixe** : " MB"
- **Tooltip** : "Maximum memory for dense hash cache (default: 500MB)"
- **Description** : Limite mémoire du cache LRU
  - 100-200 MB → Systèmes avec RAM limitée
  - 500-1000 MB → Usage normal
  - 1000-2000 MB → Traitement massif

### 5. **Label informatif**
```
ℹ️ Detects when a short video is extracted from a longer video.
Uses more memory but protected by LRU cache with limit above.
```
- **Style** : Texte grisé, petit, sur 2 lignes
- **Description** : Explique brièvement la fonctionnalité

## 🎨 Organisation visuelle

```
┌─────────────────────────────────────────────────────────┐
│ 🎬 Subsequence Detection (Optional)                     │
├─────────────────────────────────────────────────────────┤
│ ☑ Enable subsequence detection                         │
│                                                          │
│ Sample interval:        [3.0] sec                       │
│ Min match ratio:        [80.0] %                        │
│ Cache memory limit:     [500] MB                        │
│                                                          │
│ ℹ️ Detects when a short video is extracted from a      │
│   longer video. Uses more memory but protected by       │
│   LRU cache with limit above.                           │
└─────────────────────────────────────────────────────────┘
```

## 🔄 Intégration avec le système

### Sauvegarde automatique
- **Déclencheur** : Modification de n'importe quel paramètre
- **Signal checkbox** : `stateChanged`
- **Signal spin boxes** : `valueChanged`
- **Callback** : `_on_settings_changed()`
- **Stockage** : QSettings → groupe "subsequence_detection"

### Persistance
Les paramètres sont sauvegardés dans :
```
[subsequence_detection]
enabled = false
sample_interval = 3.0
min_match_ratio = 80.0
cache_memory_mb = 500
```

### Chargement au démarrage
- Les valeurs sont chargées automatiquement au lancement
- Les widgets sont bloqués pendant le chargement (pas de sauvegarde déclenchée)
- Valeurs par défaut appliquées si aucune configuration existante

## 🎯 Utilisation

### Pour activer la détection de sous-vidéos :

1. **Ouvrir l'application**
   - Lancer Video Duplicate Detector

2. **Aller dans Settings**
   - Cliquer sur l'onglet "⚙️ Settings" dans le panneau gauche

3. **Scroller vers le bas**
   - Le groupe "🎬 Subsequence Detection" est après "🚀 Quick presets"

4. **Activer la fonctionnalité**
   - Cocher "Enable subsequence detection"

5. **Ajuster les paramètres (optionnel)**
   - Modifier l'intervalle d'échantillonnage si besoin
   - Ajuster le ratio de correspondance
   - Changer la limite mémoire selon votre RAM

6. **Les paramètres sont sauvegardés automatiquement**
   - Message "💾 Settings saved" apparaît brièvement

## 💡 Recommandations visuelles

### Couleurs et style
- **Checkbox** : Police en gras pour attirer l'attention
- **Labels** : Style standard Qt
- **Info label** : Couleur `#6C757D` (gris), taille 9px
- **Groupe** : Même style que les autres groupes de paramètres

### Disposition
- **Alignement** : Grid layout 2 colonnes
- **Espacement** : 10px entre les widgets
- **Padding** : Standard QGroupBox

### Accessibilité
- Tous les contrôles ont des tooltips explicatifs
- Les plages de valeurs sont limitées pour éviter les erreurs
- Le label informatif explique le compromis mémoire

## 🔗 Connexion avec le backend

Lorsque l'utilisateur lance l'analyse :

1. **Récupération des paramètres**
   ```python
   config = settings_manager.get_analysis_config(widgets)
   # config['subsequence_detection'] = {
   #     'enabled': True/False,
   #     'sample_interval': 3.0,
   #     'min_match_ratio': 0.80,
   #     'cache_memory_mb': 500
   # }
   ```

2. **Utilisation dans l'analyse**
   - Si `enabled == True`, créer un `SubsequenceDetector`
   - Passer les paramètres au constructeur
   - Exécuter la détection après les comparaisons standard

3. **Résultats**
   - Stockés dans la table `video_subsequences`
   - Accessibles via `db.get_pending_subsequences()`

## 📊 État final

✅ **Interface complète et fonctionnelle**

- Interface graphique ajoutée
- Tous les paramètres configurables
- Sauvegarde/chargement automatique
- Tooltips et aide intégrés
- Style cohérent avec le reste de l'application
- Prêt à être utilisé par l'utilisateur final

## 🚀 Prochaines étapes

Pour utiliser la détection de sous-vidéos avec l'UI :

1. Lancer l'application
2. Activer la fonctionnalité dans Settings
3. Ajouter des vidéos à analyser
4. Cliquer sur "🔍 START"
5. Les sous-vidéos seront détectées automatiquement

Les résultats apparaîtront dans la même interface de gestion des doublons, avec un indicateur spécial pour les sous-vidéos détectées.
