#!/usr/bin/env python3
"""
Analyse la distribution des scores dans res.json pour trouver le threshold optimal.
"""

import json
import numpy as np
from pathlib import Path

# Lire les résultats
with open('res.json', 'r') as f:
    data = json.load(f)

# Extraire les scores par catégorie
tp_scores = []  # Vrais positifs
fp_scores = []  # Faux positifs
tn_scores = []  # Vrais négatifs
fn_scores = []  # Faux négatifs

for result in data['results']:
    score = result['score']
    expected = result['expected']
    is_dup = result['is_duplicate']

    if expected == 'scene_found':
        if is_dup:
            tp_scores.append(score)  # TP
        else:
            fn_scores.append(score)  # FN
    elif expected == 'negative':
        if is_dup:
            fp_scores.append(score)  # FP
        else:
            tn_scores.append(score)  # TN

print("=" * 80)
print("ANALYSE DES SCORES - Audio Fingerprint (Shazam)")
print("=" * 80)
print()

# Statistiques TP (scene_found détecté)
if tp_scores:
    print("📊 VRAIS POSITIFS (TP) - Scene détectée correctement:")
    print(f"   Count:   {len(tp_scores)}")
    print(f"   Min:     {min(tp_scores):.0f} votes")
    print(f"   Max:     {max(tp_scores):.0f} votes")
    print(f"   Mean:    {np.mean(tp_scores):.0f} votes")
    print(f"   Median:  {np.median(tp_scores):.0f} votes")
    print(f"   Std:     {np.std(tp_scores):.0f} votes")
    print(f"   Q1:      {np.percentile(tp_scores, 25):.0f} votes")
    print(f"   Q3:      {np.percentile(tp_scores, 75):.0f} votes")
    print()

# Statistiques FP (erreur)
if fp_scores:
    print("❌ FAUX POSITIFS (FP) - Scènes différentes détectées à tort:")
    print(f"   Count:   {len(fp_scores)}")
    print(f"   Min:     {min(fp_scores):.0f} votes")
    print(f"   Max:     {max(fp_scores):.0f} votes")
    print(f"   Mean:    {np.mean(fp_scores):.0f} votes")
    print(f"   Median:  {np.median(fp_scores):.0f} votes")
    print(f"   Std:     {np.std(fp_scores):.0f} votes")
    print()
    print("   Détail des FP:")
    for result in data['results']:
        if result['expected'] == 'negative' and result['is_duplicate']:
            v1 = Path(result['video1']).name
            v2 = Path(result['video2']).name
            print(f"      {result['score']:.0f} votes - {v1} vs {v2}")
    print()

# Statistiques TN (OK)
if tn_scores:
    print("✅ VRAIS NÉGATIFS (TN) - Scènes différentes correctement rejetées:")
    print(f"   Count:   {len(tn_scores)}")
    print(f"   Min:     {min(tn_scores):.0f} votes")
    print(f"   Max:     {max(tn_scores):.0f} votes")
    print(f"   Mean:    {np.mean(tn_scores):.0f} votes")
    print(f"   Median:  {np.median(tn_scores):.0f} votes")
    print(f"   Std:     {np.std(tn_scores):.0f} votes")
    print(f"   Top 10:  {sorted(tn_scores, reverse=True)[:10]}")
    print()

# Statistiques FN (erreur)
if fn_scores:
    print("❌ FAUX NÉGATIFS (FN) - Scene manquée:")
    print(f"   Count:   {len(fn_scores)}")
    for result in data['results']:
        if result['expected'] == 'scene_found' and not result['is_duplicate']:
            v1 = Path(result['video1']).name
            v2 = Path(result['video2']).name
            print(f"      {result['score']:.0f} votes - {v1} vs {v2}")
    print()

# Analyse du gap entre FP et TP
if fp_scores and tp_scores:
    max_fp = max(fp_scores)
    min_tp = min(tp_scores)
    gap = min_tp - max_fp

    print("=" * 80)
    print("GAP ANALYSIS")
    print("=" * 80)
    print(f"Max FP score:        {max_fp:.0f} votes")
    print(f"Min TP score:        {min_tp:.0f} votes")
    print(f"Gap:                 {gap:.0f} votes ({min_tp/max_fp:.1f}x)")
    print()

    # Threshold optimal = milieu du gap
    optimal_threshold = (max_fp + min_tp) / 2
    print(f"✨ THRESHOLD OPTIMAL: {optimal_threshold:.0f} votes")
    print(f"   (milieu entre max FP et min TP)")
    print()

    # Thresholds alternatifs
    print("📌 THRESHOLDS ALTERNATIFS:")
    print(f"   Conservateur (95% TP): {np.percentile(tp_scores, 5):.0f} votes")
    print(f"   Équilibré (gap/2):     {optimal_threshold:.0f} votes")
    print(f"   Agressif (2x max FP):  {max_fp * 2:.0f} votes")
    print()

# Calcul des métriques avec différents thresholds
print("=" * 80)
print("IMPACT DU THRESHOLD")
print("=" * 80)
print()

thresholds_to_test = [200, 500, 1000, 2000, 4000, 8000]

for thresh in thresholds_to_test:
    tp = sum(1 for s in tp_scores if s >= thresh)
    fp = sum(1 for s in tn_scores if s >= thresh)
    fn = len(tp_scores) - tp
    tn = len(tn_scores) - fp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"Threshold = {thresh:5.0f}:")
    print(f"   TP={tp:3d}  FP={fp:3d}  FN={fn:3d}  TN={tn:3d}")
    print(f"   Precision: {precision*100:5.1f}%  Recall: {recall*100:5.1f}%  F1: {f1*100:5.1f}%")
    print()

print("=" * 80)
