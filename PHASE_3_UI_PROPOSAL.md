# Phase 3 - Amélioration UI Benchmark Monitor

## 📐 MAQUETTE DE L'INTERFACE

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  BENCHMARK MONITOR - Pipeline: "Pipeline Rapide" | Test Set: "validation_set"  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  [① OVERVIEW] [② DETAILS] [③ PERFORMANCE] [④ HISTORY] [⑤ LOGS]                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                  ║
║  ┌────────────────────────────────────────────────────────────────────────────┐ ║
║  │ ⑥ ZONE PRINCIPALE (Contenu selon l'onglet sélectionné)                    │ ║
║  │                                                                            │ ║
║  │  [Le contenu change selon l'onglet - voir détails ci-dessous]            │ ║
║  │                                                                            │ ║
║  │                                                                            │ ║
║  │                                                                            │ ║
║  │                                                                            │ ║
║  │                                                                            │ ║
║  │                                                                            │ ║
║  │                                                                            │ ║
║  │                                                                            │ ║
║  │                                                                            │ ║
║  └────────────────────────────────────────────────────────────────────────────┘ ║
║                                                                                  ║
║  ┌─────────────────────────────────────────────────────────────────────┐        ║
║  │ ⑦ BARRE DE STATUS & CONTRÔLES                                      │        ║
║  │  Status: ● Running | 45/100 pairs | ETA: 2m 30s                    │        ║
║  │  [▶ Start] [■ Stop] [↻ Reset] [💾 Export Results]                  │        ║
║  └─────────────────────────────────────────────────────────────────────┘        ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ① ONGLET "OVERVIEW" (Vue d'ensemble)

**Objectif** : Vue rapide des métriques principales

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⑥-A : MÉTRIQUES PRINCIPALES (Cartes de statistiques)                    │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ F1 SCORE    │  │ PRECISION   │  │ RECALL      │  │ ACCURACY    │   │
│  │             │  │             │  │             │  │             │   │
│  │   0.92      │  │   0.90      │  │   0.95      │  │   0.88      │   │
│  │  ━━━━━━━━   │  │  ━━━━━━━━   │  │  ━━━━━━━━   │  │  ━━━━━━━━   │   │
│  │   92%       │  │   90%       │  │   95%       │  │   88%       │   │
│  │  🟢 PASS    │  │  🟢 PASS    │  │  🟢 PASS    │  │  🟢 PASS    │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ ⑥-B : MATRICE DE CONFUSION (Visualisation graphique)                    │
│                                                                          │
│           Predicted                                                      │
│         Pos    Neg                                                       │
│  Actual ┌──────┬──────┐                                                 │
│    Pos  │  TP  │  FN  │          ┌─────────────────────────────┐        │
│         │  18  │   2  │          │  ████████████████████ 18 TP │        │
│         ├──────┼──────┤          │  ██ 2 FN                    │        │
│    Neg  │  FP  │  TN  │          │  ███ 2 FP                   │        │
│         │   2  │  28  │          │  ████████████████████████ 28│        │
│         └──────┴──────┘          └─────────────────────────────┘        │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ ⑥-C : PROGRESSION EN TEMPS RÉEL                                         │
│                                                                          │
│  Hash Progress:    [████████████████████████████████████] 100% (45/45)  │
│  Pipeline 1/3:     [██████████████████░░░░░░░░░░░░░░░░░░]  50% (25/50)  │
│  Pipeline 2/3:     [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]   0% (0/50)   │
│  Pipeline 3/3:     [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]   0% (0/50)   │
│                                                                          │
│  Overall Progress: [██████████████░░░░░░░░░░░░░░░░░░░░░░]  33% (50/150) │
│  Elapsed: 2m 15s | ETA: 4m 30s | Speed: 0.37 pairs/sec                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Propositions pour zone ⑥-A** :
- A1 : Cartes grandes avec couleurs (vert/jaune/rouge selon seuils)
- A2 : Mini graphiques sparkline montrant l'évolution
- A3 : Tooltip au survol avec détails (seuils, delta vs derniers runs)

**Propositions pour zone ⑥-B** :
- B1 : Matrice numérique classique (tableau 2×2)
- B2 : Graphique en barres horizontales (comme montré)
- B3 : Heatmap colorée (rouge pour erreurs, vert pour corrects)

**Propositions pour zone ⑥-C** :
- C1 : Barres de progression simples (comme montré)
- C2 : Timeline graphique avec marqueurs de progrès
- C3 : Vue compacte (juste overall progress + ETA)

---

## ② ONGLET "DETAILS" (Détails des paires)

**Objectif** : Voir toutes les paires testées avec filtres

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⑥-D : FILTRES & RECHERCHE                                               │
│                                                                          │
│  🔍 Search: [____________]  Classification: [All ▼] [TP][FP][TN][FN]    │
│  Pipeline: [All ▼]  Show only: [ ] Failures  [ ] From cache             │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ ⑥-E : TABLE DES PAIRES (Scrollable)                                     │
│                                                                          │
│  # │ Video 1         │ Video 2         │Class│Result│Time │ Methods     │
│ ───┼─────────────────┼─────────────────┼─────┼──────┼─────┼────────────│
│  1 │ scene_001.mp4   │ full_movie.mp4  │ TP  │ 0.95 │ 2.4s│ ✓✓✓ (3/3)  │
│  2 │ scene_002.mp4   │ full_movie.mp4  │ TN  │ 0.35 │ 1.8s│ ✗-- (0/3)  │
│  3 │ scene_042.mp4   │ full_movie_v2...│ FN  │ 0.45 │ 2.1s│ ✗-- (0/3)  │
│  4 │ different_1.mp4 │ different_2.mp4 │ FP  │ 0.72 │ 1.5s│ ✓✗- (1/3)  │
│ ...│ ...             │ ...             │ ... │ ...  │ ... │ ...        │
│                                                                          │
│  [Click sur une ligne pour voir détails méthodes ci-dessous]            │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ ⑥-F : DÉTAILS DE LA PAIRE SÉLECTIONNÉE                                  │
│                                                                          │
│  Pair #3: scene_042.mp4 ↔ full_movie_v2.mp4                            │
│  Expected: POSITIVE (scene_found) | Predicted: NEGATIVE | Result: ❌ FN │
│                                                                          │
│  Method Results:                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ • audio_fingerprint   ✗ REJECTED  Score: 0.45  Threshold: 0.85    │ │
│  │   Execution: 1.9s | Match ratio: 0.45 | Position: 512.3s          │ │
│  │   ⚠️ Score proche du seuil - possibilité de faux négatif          │ │
│  │                                                                    │ │
│  │ • scene_detection     - SKIPPED (rejected by audio)               │ │
│  │ • visual_hash         - SKIPPED (rejected by audio)               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  [🎬 Preview Videos] [📊 Show Graphs] [💾 Export This Pair]             │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Propositions pour zone ⑥-D** :
- D1 : Filtres simples (dropdowns + checkboxes comme montré)
- D2 : Filtres avancés (plage de temps, similarité min/max, méthodes spécifiques)
- D3 : Saved filters (sauvegarder filtres fréquents)

**Propositions pour zone ⑥-E** :
- E1 : Table simple triable (clic sur headers)
- E2 : Table avec row coloring (vert TP/TN, rouge FP/FN)
- E3 : Vue compacte avec expand/collapse par paire

**Propositions pour zone ⑥-F** :
- F1 : Panel détaillé avec tous les champs (comme montré)
- F2 : Vue simplifiée (juste erreur + raison principale)
- F3 : Timeline visuelle des méthodes exécutées

---

## ③ ONGLET "PERFORMANCE" (Analyse de performance)

**Objectif** : Comprendre où le temps est passé

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⑥-G : MÉTRIQUES DE PERFORMANCE GLOBALES                                 │
│                                                                          │
│  Total Time: 125.4s                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Hash precompute:     [████░░░░░░░░░░░░░░░░] 15.2s (12%)         │    │
│  │ Pipeline execution:  [████████████████████] 105.8s (84%)        │    │
│  │ Results processing:  [█░░░░░░░░░░░░░░░░░░░]  4.4s  (4%)         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Average per pair: 2.5s | Fastest: 0.8s | Slowest: 5.2s                │
│  Cache hit rate: 15/50 (30%) | Saved time: ~22.5s                       │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ ⑥-H : TEMPS PAR MÉTHODE                                                 │
│                                                                          │
│  Method                  Calls  Avg Time  Total   % of Total            │
│  ─────────────────────── ────── ───────── ─────── ────────────          │
│  audio_fingerprint         50     1.8s    90.0s   [████████████] 72%   │
│  scene_detection           18     0.9s    16.2s   [███░░░░░░░░░] 13%   │
│  visual_hash               12     0.5s     6.0s   [█░░░░░░░░░░░]  5%   │
│  phash_confirmation         8     1.2s     9.6s   [██░░░░░░░░░░]  8%   │
│  metadata_check            50     0.05s    2.5s   [░░░░░░░░░░░░]  2%   │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ ⑥-I : DISTRIBUTION DES TEMPS (Histogramme)                              │
│                                                                          │
│   Count                                                                  │
│    │                                                                     │
│ 15 │     ██                                                              │
│ 10 │     ██  ██                                                          │
│  5 │  ██ ██  ██  ██                                                      │
│  0 │  ██ ██  ██  ██  ██  ░░                                              │
│    └────────────────────────────────────────                            │
│     0-1s 1-2s 2-3s 3-4s 4-5s >5s                                         │
│                                                                          │
│  Most pairs (60%) complete in 1-3 seconds                               │
│  Outliers (>4s): 3 pairs - see Details tab for investigation            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Propositions pour zone ⑥-G** :
- G1 : Breakdown simple avec barres (comme montré)
- G2 : Pie chart des phases principales
- G3 : Timeline interactive montrant quand chaque phase s'exécute

**Propositions pour zone ⑥-H** :
- H1 : Table simple triée par temps total (comme montré)
- H2 : Tree map (surface proportionnelle au temps)
- H3 : Flame graph (hierarchical call graph)

**Propositions pour zone ⑥-I** :
- I1 : Histogramme simple (comme montré)
- I2 : Box plot (médiane, quartiles, outliers)
- I3 : Scatter plot (temps vs index de paire)

---

## ④ ONGLET "HISTORY" (Historique des benchmarks)

**Objectif** : Comparer plusieurs runs pour suivre l'évolution

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⑥-J : LISTE DES RUNS PRÉCÉDENTS                                         │
│                                                                          │
│  ID │ Date       │ Test Set        │ Pipelines │ F1    │ Time  │ Status │
│  ───┼────────────┼─────────────────┼───────────┼───────┼───────┼────────│
│  42 │ 2025-12-14 │ validation_set  │ 3         │ 0.92  │ 125s  │ 🟢 PASS│
│  41 │ 2025-12-13 │ validation_set  │ 3         │ 0.88  │ 142s  │ 🟢 PASS│
│  40 │ 2025-12-12 │ test_set_large  │ 1         │ 0.76  │ 850s  │ 🟡 WARN│
│  39 │ 2025-12-11 │ validation_set  │ 2         │ 0.85  │ 98s   │ 🟢 PASS│
│ ... │ ...        │ ...             │ ...       │ ...   │ ...   │ ...    │
│                                                                          │
│  [Select runs to compare] ☑ #42  ☑ #41  ☐ #40  ☑ #39                   │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ ⑥-K : COMPARAISON DES RUNS SÉLECTIONNÉS                                 │
│                                                                          │
│  F1 Score Evolution:                                                     │
│  1.0 │                                  ● #42 (0.92)                     │
│  0.9 │                          ● #41 (0.88)                             │
│  0.8 │                                                                   │
│  0.7 │      ● #39 (0.85)                                                 │
│  0.6 │                                                                   │
│      └────────────────────────────────────────                          │
│       12/11  12/12  12/13  12/14                                         │
│                                                                          │
│  Metrics Comparison:                                                     │
│                Run #42    Run #41    Run #39    Δ (42 vs 41)            │
│  F1 Score      0.92       0.88       0.85       +0.04 (↑ 4.5%)         │
│  Precision     0.90       0.85       0.82       +0.05 (↑ 5.9%)         │
│  Recall        0.95       0.91       0.88       +0.04 (↑ 4.4%)         │
│  Exec Time     125s       142s       98s        -17s  (↓ 12%)          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Propositions pour zone ⑥-J** :
- J1 : Table simple avec tri/filtre (comme montré)
- J2 : Vue calendar (runs groupés par jour)
- J3 : Timeline avec mini sparklines

**Propositions pour zone ⑥-K** :
- K1 : Line charts + table de comparaison (comme montré)
- K2 : Radar chart (multi-métriques)
- K3 : Diff view (highlight what changed between runs)

---

## ⑤ ONGLET "LOGS" (Logs en temps réel)

**Objectif** : Debugging et suivi détaillé

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⑥-L : FILTRES DE LOGS                                                   │
│                                                                          │
│  Level: [All ▼] [INFO] [WARNING] [ERROR]                                │
│  Pipeline: [All ▼]  Auto-scroll: [✓]  [Clear Logs]                     │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ ⑥-M : CONSOLE DE LOGS (Auto-scroll si activé)                           │
│                                                                          │
│  [10:30:15] INFO  🚀 [Pipeline Rapide] Starting parallel processing...  │
│  [10:30:15] INFO  📦 [Pipeline Rapide] Using BATCH PROCESSING: 2 batch..│
│  [10:30:16] DEBUG 📤 [Pipeline Rapide] Submitting batch 1/2 (25 pairs)..│
│  [10:30:16] INFO  ✅ [Pipeline Rapide] PAIR 1/50 COMPLETED in 2.4s → ...│
│  [10:30:17] INFO  ✅ [Pipeline Rapide] PAIR 2/50 COMPLETED in 1.8s → ...│
│  [10:30:18] WARN  ⚠️  Low confidence match: scene_013.mp4 <-> full_m... │
│  [10:30:19] INFO  ✅ [Pipeline Rapide] PAIR 3/50 COMPLETED in 2.1s → ...│
│  [10:30:19] ERROR ❌ [Pipeline Rapide] PAIR 4/50 FAILED: Timeout (>1...│
│  [10:30:20] INFO  📊 [Pipeline Rapide] Progress: 10/50 futures compl... │
│  ...                                                                     │
│  [Auto-scrolling to bottom...]                                           │
│                                                                          │
│  [💾 Export Logs] [📋 Copy Selected]                                     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Propositions pour zone ⑥-L** :
- L1 : Filtres simples (comme montré)
- L2 : Recherche full-text dans les logs
- L3 : Filtres par pattern regex

**Propositions pour zone ⑥-M** :
- M1 : Console simple monospace avec couleurs (comme montré)
- M2 : Structured logs (colonnes: time, level, component, message)
- M3 : Collapsible sections (grouper logs par paire/batch)

---

## ⑦ BARRE DE STATUS & CONTRÔLES

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⑦-A : STATUS BAR (Gauche)                                               │
│  ● Running | Pipeline 1/3 | 45/150 pairs total | ETA: 4m 30s            │
│                                                                          │
│ ⑦-B : BOUTONS D'ACTION (Droite)                                         │
│  [▶ Start Benchmark] [■ Stop] [↻ Reset] [💾 Export Results]             │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Propositions pour zone ⑦-A** :
- A1 : Status simple textuel (comme montré)
- A2 : Status avec mini progress bar
- A3 : Status avec icônes animées (spinner pendant running)

**Propositions pour zone ⑦-B** :
- B1 : Boutons simples toujours visibles (comme montré)
- B2 : Boutons avec shortcuts keyboard (Ctrl+R = run, Ctrl+S = stop)
- B3 : Menu dropdown pour actions avancées (Export format, Compare runs, etc.)

---

## 🎨 OPTIONS DE STYLE

### Style Option 1 : **Modern Minimal**
- Flat design, pas de bordures
- Couleurs pastel (bleu/vert/orange doux)
- Typographie: Sans-serif moderne
- Espacement généreux

### Style Option 2 : **Professional Dark**
- Dark mode (fond gris foncé)
- Accent colors vifs (cyan, magenta, jaune)
- Typographie: Monospace pour chiffres
- Contraste élevé

### Style Option 3 : **Classic Light**
- Design traditionnel avec bordures
- Couleurs standards (bleu, vert, rouge)
- Typographie: System default
- Compact, maximum d'info visible

---

## 📝 QUESTIONS POUR TOI

**Pour chaque zone, dis-moi tes préférences :**

1. **Onglet OVERVIEW (①)** :
   - Quelle option pour ⑥-A (Métriques) ? A1, A2, ou A3 ?
   - Quelle option pour ⑥-B (Matrice) ? B1, B2, ou B3 ?
   - Quelle option pour ⑥-C (Progression) ? C1, C2, ou C3 ?

2. **Onglet DETAILS (②)** :
   - Quelle option pour ⑥-D (Filtres) ? D1, D2, ou D3 ?
   - Quelle option pour ⑥-E (Table) ? E1, E2, ou E3 ?
   - Quelle option pour ⑥-F (Détails paire) ? F1, F2, ou F3 ?

3. **Onglet PERFORMANCE (③)** :
   - Quelle option pour ⑥-G (Métriques globales) ? G1, G2, ou G3 ?
   - Quelle option pour ⑥-H (Temps par méthode) ? H1, H2, ou H3 ?
   - Quelle option pour ⑥-I (Distribution) ? I1, I2, ou I3 ?

4. **Onglet HISTORY (④)** :
   - Quelle option pour ⑥-J (Liste runs) ? J1, J2, ou J3 ?
   - Quelle option pour ⑥-K (Comparaison) ? K1, K2, ou K3 ?

5. **Onglet LOGS (⑤)** :
   - Quelle option pour ⑥-L (Filtres) ? L1, L2, ou L3 ?
   - Quelle option pour ⑥-M (Console) ? M1, M2, ou M3 ?

6. **Status Bar (⑦)** :
   - Quelle option pour ⑦-A (Status) ? A1, A2, ou A3 ?
   - Quelle option pour ⑦-B (Boutons) ? B1, B2, ou B3 ?

7. **Style général** :
   - Modern Minimal, Professional Dark, ou Classic Light ?

---

**Réponds simplement avec les codes, par exemple :**
```
1. OVERVIEW: A1, B2, C1
2. DETAILS: D1, E2, F1
3. PERFORMANCE: G1, H1, I2
4. HISTORY: J1, K1
5. LOGS: L1, M1
6. STATUS: A2, B1
7. STYLE: Modern Minimal
```

**Ou si tu veux mixer/personnaliser, explique ce que tu veux changer !**
