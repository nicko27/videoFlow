Benchmarks prêts à l'emploi
===========================

Fichiers fournis :

- `pairs_scenes_example.json` : 4 paires avec attentes (positive/negative) et préférence FP/FN, séquence_score inclus.
- `pipeline_scene_strict.json` : pipeline filtrage strict (précision, limite les faux positifs).
- `pipeline_scene_recall.json` : pipeline hybride orienté rappel (plus permissif, Strategy3 pondérée).

Exécution depuis l’onglet Debug :
- Onglet Debug → section "Benchmarks pipeline" → choisir `pairs_scenes_example.json` + un pipeline (strict ou recall) → saisir un label → bouton Lancer.

Exécution en CLI :
```bash
python -m src.plugins.duplicate_finder.benchmark_cli \
  --pairs src/plugins/duplicate_finder/tests/benchmarks/pairs_scenes_example.json \
  --pipeline-config src/plugins/duplicate_finder/tests/benchmarks/pipeline_scene_strict.json \
  --label bench_strict --debug
```

Préférences FP/FN :
- `preference: "fp"` = tolérer les faux positifs (favorise le rappel).
- `preference: "fn"` = tolérer les faux négatifs (favorise la précision).
- `preference: "balanced"` = équilibré.

Attendus :
- Chaque entrée porte `expected` ("positive" ou "negative") pour le calcul TP/FP/TN/FN.
