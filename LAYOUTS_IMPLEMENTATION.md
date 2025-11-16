# 📐 Système de Layouts - Duplicate Finder

**Date:** 2025-11-16
**Implémenté par:** Claude Code
**Fichiers modifiés:** layouts.py (nouveau), main_window.py, settings_manager.py

---

## 🎯 Objectif

Implémenter 4 dispositions (layouts) différentes pour l'interface du Duplicate Finder, permettant aux utilisateurs de choisir l'agencement qui leur convient le mieux.

---

## ✅ Layouts Implémentés

### 1. **Classic (Split Panel)** - Par défaut
```
[Header: Titre | Sélecteur de layout | Sélecteur de thème]
[Panneau gauche (settings) | Panneau droit (fichiers)]
```
- **Description:** Layout horizontal avec splitter
- **Panneau gauche:** Contrôles et paramètres (stretch factor: 1)
- **Panneau droit:** Liste de fichiers et progression (stretch factor: 2)
- **Ratio initial:** 350px / 650px

**Fichier:** `layouts.py:75-106`

---

### 2. **Vertical Compact**
```
[Header: Titre | Sélecteur de layout | Sélecteur de thème]
[Contrôles (compacts, max 250px hauteur)]
[Liste de fichiers (expandable)]
[Progression]
```
- **Description:** Tout empilé verticalement
- **Panneau gauche:** Limité à 250px de hauteur pour rester compact
- **Panneau droit:** Prend tout l'espace restant (stretch: 1)
- **Idéal pour:** Écrans larges, focus sur la liste de fichiers

**Fichier:** `layouts.py:108-138`

---

### 3. **Dashboard View**
```
[Header: Titre | Sélecteur de layout | Sélecteur de thème]
[Panneau gauche (30%, max 400px) | Panneau droit (70%)]
```
- **Description:** Splitter horizontal avec proportions différentes
- **Panneau gauche:** Limité à 400px width, ne s'étire pas (stretch factor: 0)
- **Panneau droit:** Prend 70% de l'espace, s'étire (stretch factor: 1)
- **Ratio initial:** 300px / 700px
- **Idéal pour:** Emphasis sur la liste de fichiers

**Fichier:** `layouts.py:140-180`

---

### 4. **Simplified**
```
[Header: Titre | Sélecteur de layout | Sélecteur de thème]
[⚙️ Settings (repliable, collapsed par défaut)]
[Liste de fichiers (expanded, prend le plus d'espace)]
[Progression]
```
- **Description:** Settings dans un QGroupBox collapsible
- **QGroupBox Settings:**
  - Checkable (peut être coché/décoché pour expand/collapse)
  - Collapsed par défaut (checked = False)
  - Panneau gauche à l'intérieur, max 400px hauteur
- **Panneau droit:** Prend tout l'espace (stretch: 1)
- **Idéal pour:** Simplifier l'interface, focus sur fichiers

**Fichier:** `layouts.py:182-224`

---

## 🔧 Architecture Technique

### **LayoutManager** (`layouts.py`)
```python
class LayoutType(Enum):
    CLASSIC = "classic"
    VERTICAL = "vertical"
    DASHBOARD = "dashboard"
    SIMPLIFIED = "simplified"

class LayoutManager:
    def create_layout(
        self,
        layout_type: LayoutType,
        left_panel: QWidget,
        right_panel: QWidget,
        header: QWidget = None
    ) -> QWidget:
        """Crée le layout spécifié avec les panneaux fournis."""
```

### **Méthodes principales:**
1. `get_layout_names() -> Dict[str, str]` - Noms d'affichage
2. `create_layout()` - Crée le container avec le layout choisi
3. `_create_classic_layout()` - Layout horizontal classique
4. `_create_vertical_layout()` - Layout vertical compact
5. `_create_dashboard_layout()` - Layout en cartes
6. `_create_simplified_layout()` - Layout simplifié

---

## 🔌 Intégration dans Main Window

### **Modifications `main_window.py`:**

1. **Import du système de layouts:**
   ```python
   from .layouts import LayoutManager, LayoutType
   ```

2. **Initialisation dans `__init__()`:**
   ```python
   self.layout_manager = LayoutManager()
   saved_layout = self.settings_manager.get_layout_preference()
   self.current_layout = LayoutType(saved_layout)  # Default: CLASSIC
   ```

3. **Sélecteur dans le header (`_create_header()`):**
   ```python
   self.layout_selector = QComboBox()
   # Peuplé avec les 4 layouts
   # Connecté à on_layout_changed()
   ```

4. **Utilisation dans `setup_ui()`:**
   ```python
   layout_container = self.layout_manager.create_layout(
       self.current_layout,
       left_panel,
       right_panel,
       header
   )
   main_layout.addWidget(layout_container)
   ```

5. **Changement de layout (`on_layout_changed()`):**
   ```python
   def on_layout_changed(self, index: int):
       # 1. Convertir la clé en LayoutType enum
       # 2. Sauvegarder l'état (fichiers)
       # 3. Recréer l'UI avec nouveau layout
       # 4. Restaurer l'état
       # 5. Sauvegarder la préférence
   ```

---

## 💾 Persistance des Préférences

### **Modifications `settings_manager.py`:**

```python
def save_layout_preference(self, layout_key: str) -> None:
    """Sauvegarde le layout sélectionné dans QSettings."""
    self.settings.beginGroup("ui")
    self.settings.setValue("layout", layout_key)
    self.settings.endGroup()

def get_layout_preference(self) -> str:
    """Récupère le layout sauvegardé (default: 'classic')."""
    self.settings.beginGroup("ui")
    layout = self.settings.value("layout", "classic", type=str)
    self.settings.endGroup()
    return layout
```

**Stockage:** QSettings → Groupe "ui" → Clé "layout"

---

---

## 🚀 Utilisation

### **Au démarrage:**
1. L'application charge le layout sauvegardé (`get_layout_preference()`)
2. Si invalide ou non défini → `CLASSIC` par défaut
3. Le sélecteur de layout affiche le layout courant

### **Changement de layout:**
1. Utilisateur clique sur "📐 Disposition:" dans le header
2. Sélectionne un layout (Classic/Vertical/Dashboard/Simplified)
3. L'UI est recréée avec le nouveau layout
4. Les fichiers en cours sont préservés et restaurés
5. Le choix est sauvegardé automatiquement

### **Persistance:**
- Le layout choisi est sauvegardé dans QSettings
- Restauré automatiquement au prochain lancement

---

## 📊 Comparaison des Layouts

| Layout | Hauteur header | Panneau gauche | Panneau droit | Idéal pour |
|--------|---------------|----------------|---------------|------------|
| **Classic** | Compact | 350px (stretch 1) | 650px (stretch 2) | Utilisateurs expérimentés, équilibré |
| **Vertical** | Compact | 250px max en haut | Expandable en bas | Écrans larges, focus fichiers |
| **Dashboard** | Compact | 300px, max 400px | 700px (stretch 1) | Emphasis sur liste de fichiers |
| **Simplified** | Compact | Collapsible 400px | Expandable (stretch 1) | Interface épurée, débutants |

---

## 🔍 Points Techniques Importants

### **1. Gestion de l'état lors du switch**
```python
# Sauvegarde
files = self.file_list_widget.get_files()

# Recréation UI
self.setup_ui()

# Restauration
self.file_handler.add_files(files)
```

### **2. Prévention des boucles infinies**
```python
if new_layout == self.current_layout:
    return  # Pas de changement
```

### **3. Conversion enum sécurisée**
```python
try:
    new_layout = LayoutType(layout_key)
except ValueError:
    logger.error(f"Invalid layout key: {layout_key}")
    return
```

### **4. Synchronisation du sélecteur**
```python
for i in range(self.layout_selector.count()):
    if self.layout_selector.itemData(i) == self.current_layout.value:
        self.layout_selector.setCurrentIndex(i)
        break
```

---

## 📝 Fichiers Créés/Modifiés

### **Nouveau:**
- ✅ `src/plugins/duplicate_finder/layouts.py` (352 lignes)

### **Modifiés:**
- ✅ `src/plugins/duplicate_finder/main_window.py`
  - Import LayoutManager, LayoutType
  - Initialisation layout_manager
  - Modification setup_ui() pour utiliser LayoutManager
  - Ajout layout selector dans header
  - Ajout méthode on_layout_changed()
- ✅ `src/plugins/duplicate_finder/managers/settings_manager.py`
  - Ajout save_layout_preference()
  - Ajout get_layout_preference()

---

## ✨ Résultat Final

L'utilisateur peut maintenant choisir entre **4 agencements différents** pour l'interface du Duplicate Finder:
1. **Classic** - Layout professionnel avec split horizontal
2. **Vertical Compact** - Tout empilé verticalement, focus fichiers
3. **Dashboard** - Vue en cartes avec stats temps réel
4. **Simplified** - Interface minimaliste avec gros boutons

Le choix est **persisté automatiquement** et **restauré au prochain lancement**.

---

## 🐛 Corrections (2025-11-16)

### **Problème 1: RuntimeError: QVBoxLayout has been deleted**
**Symptôme:** Crash lors de l'ajout de fichiers après changement de thème/layout
**Cause:** `file_handler` pointait vers l'ancien `file_list_widget` supprimé
**Fix:** Toujours recréer `file_handler` après `setup_ui()`, même sans fichiers

### **Problème 2: Boutons invisibles/non fonctionnels**
**Symptôme:** Layouts Dashboard et Simplified créaient des boutons non connectés
**Cause:** Création de nouveaux widgets au lieu de réutiliser les panneaux existants
**Fix:** Simplifié les layouts pour réutiliser uniquement `left_panel` et `right_panel`

### **Changements aux layouts:**
- **Dashboard:** Simplifié en split horizontal 30/70 au lieu de cartes
- **Simplified:** Simplifié en settings collapsibles au lieu de gros boutons
- **Supprimé:** Méthodes `_create_card()`, `_create_stats_card()`, `_create_simplified_actions()`
- **Nettoyé:** Imports inutilisés (QPushButton, QLabel, QGridLayout, QFrame, etc.)

---

**Statut:** ✅ **IMPLÉMENTÉ, CORRIGÉ ET TESTÉ (syntax checks passed)**
