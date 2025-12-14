# Phase 3 - Amélioration UI Benchmark Monitor V2

## 📐 MAQUETTE DE L'INTERFACE (TOUT SUR UNE PAGE)

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  BENCHMARK MONITOR - Test Set: "validation_set"                                 ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  ① PROGRESSION GLOBALE                                                          ║
║  ┌────────────────────────────────────────────────────────────────────────────┐ ║
║  │ Overall Progress: [██████████████░░░░░░░░░░░░░░░░░░░░░░]  33% (50/150)    │ ║
║  │ Elapsed: 2m 15s | ETA: 4m 30s | Speed: 0.37 pairs/sec | Status: ● Running│ ║
║  │ [▶ Start] [■ Stop] [↻ Reset] [💾 Export Results]                          │ ║
║  └────────────────────────────────────────────────────────────────────────────┘ ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  ② PROGRESSION DES HASHES (selon méthodes activées dans les pipelines)         ║
║  ┌────────────────────────────────────────────────────────────────────────────┐ ║
║  │ SHA-256:              [████████████████████████████████] 100% (45/45)     │ ║
║  │ Frame Hash:           [████████████████████████████████] 100% (45/45)     │ ║
║  │ DCT Coefficients:     [████████████████████████████████] 100% (45/45)     │ ║
║  │ SSIM Reference:       [████████████████████████████████] 100% (30/30)     │ ║
║  │ Optical Flow:         [██████████████████░░░░░░░░░░░░░░]  60% (18/30)     │ ║
║  │ Motion Analysis:      [████████████░░░░░░░░░░░░░░░░░░░░]  50% (15/30)     │ ║
║  │ Feature Descriptors:  [████████░░░░░░░░░░░░░░░░░░░░░░░░]  40% (12/30)     │ ║
║  │ Color Histogram:      [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]   0% (0/30)      │ ║
║  │ Edge Pattern:         [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]   0% (0/30)      │ ║
║  └────────────────────────────────────────────────────────────────────────────┘ ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  ③ PROGRESSION DES PIPELINES                                                    ║
║  ┌────────────────────────────────────────────────────────────────────────────┐ ║
║  │ Pipeline "Rapide":      [██████████████████░░░░░░░░░░░░]  50% (25/50)     │ ║
║  │   ├─ Accepted: 18  Rejected: 7  Errors: 0                                 │ ║
║  │   └─ Current: scene_013.mp4 ↔ full_movie.mp4 (2.1s)                      │ ║
║  │                                                                            │ ║
║  │ Pipeline "Précis":      [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]   0% (0/50)      │ ║
║  │   └─ Waiting...                                                            │ ║
║  │                                                                            │ ║
║  │ Pipeline "Équilibré":   [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]   0% (0/50)      │ ║
║  │   └─ Waiting...                                                            │ ║
║  └────────────────────────────────────────────────────────────────────────────┘ ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  ④ MÉTRIQUES EN TEMPS RÉEL (mise à jour automatique)                           ║
║  ┌──────────────┬──────────────┬──────────────┬──────────────┐                ║
║  │  F1 SCORE    │  PRECISION   │  RECALL      │  ACCURACY    │                ║
║  │              │              │              │              │                ║
║  │    0.92      │    0.90      │    0.95      │    0.88      │                ║
║  │  ━━━━━━━━    │  ━━━━━━━━    │  ━━━━━━━━    │  ━━━━━━━━    │                ║
║  │    92%       │    90%       │    95%       │    88%       │                ║
║  │   🟢 PASS    │   🟢 PASS    │   🟢 PASS    │   🟢 PASS    │                ║
║  └──────────────┴──────────────┴──────────────┴──────────────┘                ║
║                                                                                  ║
║  ┌────────────────────────────────────────────────────────────────────────────┐ ║
║  │ TP: 18  │  FP: 2  │  TN: 28  │  FN: 2  │  Total: 50                       │ ║
║  └────────────────────────────────────────────────────────────────────────────┘ ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  ⑤ PERFORMANCE TEMPS RÉEL                                                       ║
║  ┌────────────────────────────────────────────────────────────────────────────┐ ║
║  │ Total Time: 125.4s                                                         │ ║
║  │ ┌──────────────────────────────────────────────────────────────────────┐   │ ║
║  │ │ Hash precompute:     [████░░░░░░░░░░░░░░░░] 15.2s (12%)              │   │ ║
║  │ │ Pipeline execution:  [████████████████████] 105.8s (84%)             │   │ ║
║  │ │ Results processing:  [█░░░░░░░░░░░░░░░░░░░]  4.4s  (4%)              │   │ ║
║  │ └──────────────────────────────────────────────────────────────────────┘   │ ║
║  │                                                                            │ ║
║  │ Average per pair: 2.5s | Fastest: 0.8s | Slowest: 5.2s                   │ ║
║  │ Cache hit rate: 15/50 (30%) | Saved time: ~22.5s                          │ ║
║  └────────────────────────────────────────────────────────────────────────────┘ ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  ⑥ TEMPS PAR MÉTHODE                                                            ║
║  ┌────────────────────────────────────────────────────────────────────────────┐ ║
║  │ Method                  Calls  Avg Time  Total   % of Total               │ ║
║  │ ─────────────────────── ────── ───────── ─────── ──────────────            │ ║
║  │ audio_fingerprint         50     1.8s    90.0s   [████████████] 72%      │ ║
║  │ scene_detection           18     0.9s    16.2s   [███░░░░░░░░░] 13%      │ ║
║  │ visual_hash               12     0.5s     6.0s   [█░░░░░░░░░░░]  5%      │ ║
║  │ phash_confirmation         8     1.2s     9.6s   [██░░░░░░░░░░]  8%      │ ║
║  │ metadata_check            50     0.05s    2.5s   [░░░░░░░░░░░░]  2%      │ ║
║  └────────────────────────────────────────────────────────────────────────────┘ ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  ⑦ LOGS EN TEMPS RÉEL (dernières 10 lignes - auto-scroll)                      ║
║  ┌────────────────────────────────────────────────────────────────────────────┐ ║
║  │ [10:30:19] INFO  ✅ [Pipeline Rapide] PAIR 3/50 COMPLETED in 2.1s → ...   │ ║
║  │ [10:30:19] ERROR ❌ [Pipeline Rapide] PAIR 4/50 FAILED: Timeout (>120s)   │ ║
║  │ [10:30:20] INFO  📊 [Pipeline Rapide] Progress: 10/50 futures compl...    │ ║
║  │ [10:30:22] INFO  ✅ [Pipeline Rapide] PAIR 11/50 COMPLETED in 1.9s → ...  │ ║
║  │ [10:30:23] WARN  ⚠️  Low confidence match: scene_013.mp4 <-> full_m...    │ ║
║  │ [10:30:24] INFO  ✅ [Pipeline Rapide] PAIR 15/50 COMPLETED in 2.3s → ...  │ ║
║  │ [10:30:25] INFO  📊 [Pipeline Rapide] Progress: 20/50 futures compl...    │ ║
║  │ [10:30:27] INFO  ✅ [Pipeline Rapide] PAIR 23/50 COMPLETED in 2.1s → ...  │ ║
║  │ [10:30:28] INFO  ✅ [Pipeline Rapide] PAIR 25/50 COMPLETED in 1.7s → ...  │ ║
║  │ [10:30:29] INFO  🏁 [Pipeline Rapide] Completed. Processed 25/50 pairs    │ ║
║  └────────────────────────────────────────────────────────────────────────────┘ ║
║  │ [ ] Auto-scroll  [Clear Logs]  [💾 Export Logs]                            │ ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## 🎯 ZONES DÉTAILLÉES

### ① PROGRESSION GLOBALE
**Contenu** :
- Barre de progression pour TOUS les pipelines combinés
- Temps écoulé, ETA, vitesse
- Status (Running/Stopped/Completed)
- Boutons de contrôle (Start, Stop, Reset, Export)

**Options** :
- **A1** : Barre simple avec texte (comme montré)
- **A2** : Barre avec mini-graphique sparkline de vitesse
- **A3** : Barre compacte (juste % et ETA)

**Question 1** : Quelle option pour ① ? (A1, A2, ou A3)

---

### ② PROGRESSION DES HASHES
**Contenu** :
- Liste de TOUTES les méthodes de hash utilisées dans les pipelines
- Progression indépendante pour chaque type
- Détection automatique : si aucun pipeline n'utilise "Color Histogram", ne pas l'afficher

**Options** :
- **B1** : Liste complète avec toutes les méthodes possibles (même à 0%)
- **B2** : Liste dynamique (affiche uniquement les méthodes utilisées dans les pipelines)
- **B3** : Liste groupée par catégorie (Hash de base / Signatures visuelles / Signatures audio / Autres)

**Question 2** : Quelle option pour ② ? (B1, B2, ou B3)

---

### ③ PROGRESSION DES PIPELINES
**Contenu** :
- Une barre par pipeline
- Stats temps réel (Accepted/Rejected/Errors)
- Indication de la paire en cours de traitement
- État (Running/Waiting/Completed)

**Options** :
- **C1** : Vue détaillée avec sous-lignes (comme montré)
- **C2** : Vue compacte (juste barre + stats sur même ligne)
- **C3** : Vue expandable (clic pour voir détails)

**Question 3** : Quelle option pour ③ ? (C1, C2, ou C3)

---

### ④ MÉTRIQUES EN TEMPS RÉEL
**Contenu** :
- Cartes F1/Precision/Recall/Accuracy
- Confusion matrix (TP/FP/TN/FN)
- Mise à jour en direct pendant le benchmark

**Options** :
- **D1** : Cartes grandes avec barres de progression (comme montré)
- **D2** : Cartes avec couleurs conditionnelles (vert si >seuil, jaune si proche, rouge si <seuil)
- **D3** : Cartes avec mini trend (flèche ↑↓ si amélioration/dégradation vs dernier run)

**Question 4** : Quelle option pour ④ ? (D1, D2, ou D3)

---

### ⑤ PERFORMANCE TEMPS RÉEL
**Contenu** :
- Breakdown du temps total (Hash / Execution / Processing)
- Stats par paire (avg/min/max)
- Cache hit rate

**Options** :
- **E1** : Barres horizontales avec breakdown (comme montré)
- **E2** : Pie chart pour le breakdown
- **E3** : Vue compacte (juste texte, pas de graphique)

**Question 5** : Quelle option pour ⑤ ? (E1, E2, ou E3)

---

### ⑥ TEMPS PAR MÉTHODE
**Contenu** :
- Table avec toutes les méthodes appelées
- Nombre d'appels, temps moyen, temps total
- Barres visuelles pour % du temps total

**Options** :
- **F1** : Table complète avec barres (comme montré)
- **F2** : Top 5 seulement (méthodes les plus coûteuses)
- **F3** : Tree map (surface proportionnelle au temps)

**Question 6** : Quelle option pour ⑥ ? (F1, F2, ou F3)

---

### ⑦ LOGS EN TEMPS RÉEL
**Contenu** :
- Affichage des derniers logs
- Auto-scroll optionnel
- Filtrage par niveau (INFO/WARN/ERROR)

**Options** :
- **G1** : Dernières 10 lignes, auto-scroll (comme montré)
- **G2** : Zone scrollable complète avec tous les logs
- **G3** : Vue compacte (juste dernière ligne + compteur)

**Question 7** : Quelle option pour ⑦ ? (G1, G2, ou G3)

---

## 🎨 OPTIONS DE DISPOSITION

### Layout Option 1 : **Compact** (tout visible sans scroll)
- Hauteur fenêtre : ~800px
- Zones ②③ côte à côte (50/50)
- Zone ⑦ réduite (5 lignes max)
- Police plus petite

### Layout Option 2 : **Confortable** (petit scroll possible)
- Hauteur fenêtre : ~1000px
- Zones empilées verticalement (comme montré)
- Zone ⑦ moyenne (10 lignes)
- Police normale

### Layout Option 3 : **Détaillé** (scroll vertical)
- Hauteur fenêtre : illimitée
- Zones empilées avec espacements généreux
- Zone ⑦ grande (20+ lignes scrollables)
- Police grande, tout bien lisible

**Question 8** : Quelle option de layout ? (Compact, Confortable, ou Détaillé)

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

**Question 9** : Quel style général ? (Modern Minimal, Professional Dark, ou Classic Light)

---

## 📝 FONCTIONNALITÉS SUPPLÉMENTAIRES

### Notification de fin
- **N1** : Pop-up système quand benchmark terminé
- **N2** : Son de notification
- **N3** : Rien (juste changement status)

**Question 10** : Notification de fin ? (N1, N2, N3, ou N1+N2)

### Export automatique
- **X1** : Toujours exporter automatiquement à la fin
- **X2** : Demander si on veut exporter
- **X3** : Manuel seulement (bouton Export)

**Question 11** : Export automatique ? (X1, X2, ou X3)

---

## 📝 RÉPONDS SIMPLEMENT :

```
1. Progression globale: A?
2. Hashes: B?
3. Pipelines: C?
4. Métriques: D?
5. Performance: E?
6. Temps par méthode: F?
7. Logs: G?
8. Layout: Compact/Confortable/Détaillé
9. Style: Modern Minimal/Professional Dark/Classic Light
10. Notification: N?
11. Export: X?
```

**Ou explique ce que tu veux changer/ajouter !**
