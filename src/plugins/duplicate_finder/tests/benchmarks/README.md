Benchmarks prêts à l'emploi
===========================

Fichiers fournis :

- `pairs_scenes_example.json` : 4 paires avec attentes (positive/negative) et préférence FP/FN, séquence_score inclus.

**Note:** Les configurations de pipeline sont maintenant stockées en base de données.
Utilisez l'interface graphique pour créer et gérer vos pipelines de test.

Exécution depuis l'onglet Debug :
- Onglet Debug → section "Benchmarks pipeline" → choisir `pairs_scenes_example.json` + un pipeline depuis la base → saisir un label → bouton Lancer.

Préférences FP/FN :
- `preference: "fp"` = tolérer les faux positifs (favorise le rappel).
- `preference: "fn"` = tolérer les faux négatifs (favorise la précision).
- `preference: "balanced"` = équilibré.

Attendus :
- Chaque entrée porte `expected` ("positive" ou "negative") pour le calcul TP/FP/TN/FN.
