# 🔍 BUG #6 - THRESHOLD NORMALIZATION ANALYSIS

**Date:** 2025-12-14
**Bug:** Tolerance thresholds not normalized
**Gravité:** 🟡 MOYEN
**Statut:** ⏳ NEEDS DEEPER INVESTIGATION

---

## 🔍 CURRENT STATE

### Database Storage (Percentages 0-100)
```sql
SELECT name, methods_json FROM saved_pipelines LIMIT 3;

🎨 Color Histogram Only: threshold=85.0
📐 Edge Pattern Only: threshold=80.0
🎬 Motion Analysis Only: correlation_threshold=85.0
```

### Code Usage (Mixed)
```python
# advanced_pipeline.py - Uses decimals (0.0-1.0)
level1_threshold = config.get('level1_threshold', 0.7)  # 0.7 = 70%
level2_threshold = config.get('level2_threshold', 0.8)  # 0.8 = 80%

# Database - Uses percentages (0-100)
threshold: 85.0  # 85%
threshold: 80.0  # 80%
```

---

## ❓ INVESTIGATION REQUIRED

To properly fix this bug, we need to:

1. **Audit all threshold usage** across the codebase
2. **Determine standard range**: Should we use 0-1 or 0-100?
3. **Add conversion functions** where needed
4. **Update documentation** to specify expected ranges

### Recommendation: Use 0-1 Range (Standard)

**Reasoning:**
- Most scientific libraries use 0-1 (scipy, sklearn, etc.)
- Advanced pipeline already uses 0-1
- Database can continue storing 0-100 for user readability
- Add conversion layer: `db_threshold / 100.0` when loading

---

## 🚧 DEFERRED FOR NOW

**Reason:** This requires extensive codebase audit and testing to ensure we don't break existing pipeline configurations.

**Estimated Time:** 3-4 hours (full audit + testing)

**Impact:** Low - current system works, just inconsistent internally

**Recommendation:** Move to Phase 3 or dedicated refactoring session

---

**Analysis Date:** 2025-12-14
**Decision:** DEFER to later phase
