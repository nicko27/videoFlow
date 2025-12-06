# i18n Migration Guide - Duplicate Finder

**Status**: Framework Complete, Migration In Progress
**Issue**: ISSUE #11 - Incomplete i18n (95% of UI strings hardcoded in French)
**Goal**: Migrate all hardcoded UI strings to use the i18n translation system

---

## Table of Contents

1. [Overview](#overview)
2. [Current Status](#current-status)
3. [i18n System](#i18n-system)
4. [Migration Strategy](#migration-strategy)
5. [Step-by-Step Guide](#step-by-step-guide)
6. [Translation Files](#translation-files)
7. [Testing Translations](#testing-translations)
8. [Common Patterns](#common-patterns)
9. [Progress Tracking](#progress-tracking)

---

## Overview

### The Problem

Currently, 95% of UI strings are hardcoded in French directly in the Python code:

```python
# ❌ BAD - Hardcoded French
button.setText("Démarrer l'analyse")
label.setText("Fichiers sélectionnés")
```

This makes the application:
- Unusable for non-French speakers
- Difficult to maintain (strings scattered everywhere)
- Impossible to add new languages

### The Solution

A complete i18n (internationalization) system already exists in `i18n/`:
- `translator.py` - Translation engine
- `translations/en.json` - English translations
- `translations/fr.json` - French translations

We need to migrate hardcoded strings to use this system:

```python
# ✅ GOOD - Using i18n
from i18n import get_translator
tr = get_translator().tr

button.setText(tr("ui.buttons.start_analysis"))
label.setText(tr("ui.labels.files_selected"))
```

---

## Current Status

### Framework: ✅ Complete

The i18n infrastructure is fully implemented:
- ✅ Translator class with language switching
- ✅ JSON-based translation files
- ✅ Nested key support (e.g., `ui.buttons.start`)
- ✅ String formatting support (e.g., `{count} files`)
- ✅ Fallback to English if translation missing
- ✅ Logging for missing translations

### Translations: ✅ Available

- ✅ English (`en.json`) - ~150 strings
- ✅ French (`fr.json`) - ~150 strings
- ⚠️ Coverage: ~50% of all UI strings

### Code Migration: ⚠️ In Progress

Files migrated to i18n:
- ⚠️ `main_window.py` - 0% (62 functions, many hardcoded strings)
- ⚠️ `comparison_dialog.py` - 0%
- ⚠️ `progress_widgets.py` - 0%
- ⚠️ `ui/panels.py` - 0%
- ⚠️ `handlers/*.py` - 0%

**Estimated**: 200+ hardcoded strings need migration

---

## i18n System

### Architecture

```
i18n/
├── __init__.py              # Package exports
├── translator.py            # Translator class
├── translations.py          # Enhanced translation utilities
└── translations/
    ├── en.json              # English translations
    └── fr.json              # French translations
```

### How It Works

1. **Translation Files** (JSON):
   ```json
   {
     "language_name": "English",
     "ui": {
       "buttons": {
         "start_analysis": "Start Analysis",
         "stop_analysis": "Stop Analysis"
       },
       "labels": {
         "files_selected": "{count} files selected"
       }
     }
   }
   ```

2. **Translator** (Python):
   ```python
   from i18n import get_translator
   tr = get_translator().tr

   # Simple translation
   text = tr("ui.buttons.start_analysis")
   # → "Start Analysis" (if English)
   # → "Démarrer l'analyse" (if French)

   # With formatting
   text = tr("ui.labels.files_selected", count=5)
   # → "5 files selected"
   ```

3. **Language Switching**:
   ```python
   from i18n import set_language

   set_language('en')  # English
   set_language('fr')  # French
   ```

---

## Migration Strategy

### Approach: Gradual, File-by-File

**Don't**: Try to migrate everything at once (too risky)
**Do**: Migrate file by file, test each file

### Priority Order

1. **High Priority** (user-facing):
   - `ui/panels.py` - Main UI panels
   - `main_window.py` - Main window
   - `comparison_dialog.py` - Comparison dialog
   - `progress_widgets.py` - Progress displays

2. **Medium Priority** (dialogs):
   - `subsequence_comparison_dialog.py`
   - `advanced_progress_dialog.py`
   - Settings dialogs

3. **Low Priority** (backend):
   - `handlers/*.py` - Mostly log messages
   - `workers/*.py` - Background workers
   - Internal modules

### Migration Workflow

```
For each file:
1. Read the file
2. Find all hardcoded strings
3. Add missing translations to en.json + fr.json
4. Replace hardcoded strings with tr() calls
5. Test the file
6. Commit changes
```

---

## Step-by-Step Guide

### Step 1: Find Hardcoded Strings

Use grep to find French strings:

```bash
# Find potential hardcoded strings
grep -n '"[A-ZÀÉÈÊ]' file.py | grep -v '"""'

# Example output:
# 45: button.setText("Démarrer l'analyse")
# 67: label.setText("Fichiers sélectionnés")
```

### Step 2: Add Translations

For each string, add entries to both JSON files:

**en.json**:
```json
{
  "ui": {
    "buttons": {
      "start_analysis": "Start Analysis"
    }
  }
}
```

**fr.json**:
```json
{
  "ui": {
    "buttons": {
      "start_analysis": "Démarrer l'analyse"
    }
  }
}
```

### Step 3: Update Code

Import translator at top of file:

```python
from i18n import get_translator
tr = get_translator().tr
```

Replace hardcoded strings:

```python
# Before
button.setText("Démarrer l'analyse")

# After
button.setText(tr("ui.buttons.start_analysis"))
```

### Step 4: Handle Formatted Strings

For strings with variables:

**Add to JSON**:
```json
{
  "ui": {
    "progress": {
      "files_processed": "{current}/{total} files processed"
    }
  }
}
```

**Use in code**:
```python
# Before
text = f"{current}/{total} fichiers traités"

# After
text = tr("ui.progress.files_processed", current=10, total=100)
```

### Step 5: Test

```bash
# Run the application
python main.py

# Test both languages
# In settings: change language to English/French
# Verify all strings appear correctly
```

---

## Translation Files

### JSON Structure

Organize translations hierarchically:

```json
{
  "language_name": "English",

  "ui": {
    "buttons": {
      "start_analysis": "Start Analysis",
      "stop_analysis": "Stop Analysis",
      "add_files": "Add Files",
      "add_folder": "Add Folder",
      "clear_list": "Clear List"
    },

    "labels": {
      "files_selected": "{count} files selected",
      "similarity": "Similarity: {percent}%",
      "time_elapsed": "Time elapsed: {time}"
    },

    "dialogs": {
      "comparison": {
        "title": "Video Comparison",
        "keep_first": "Keep First",
        "keep_second": "Keep Second",
        "keep_both": "Keep Both"
      }
    }
  },

  "messages": {
    "errors": {
      "file_not_found": "File not found: {path}",
      "invalid_video": "Invalid video file"
    },

    "info": {
      "analysis_complete": "Analysis complete: {count} duplicates found",
      "no_duplicates": "No duplicates found"
    }
  }
}
```

### Key Naming Convention

Use descriptive, hierarchical keys:

```
{category}.{subcategory}.{element}_{action}

Examples:
ui.buttons.start_analysis
ui.labels.files_selected
ui.dialogs.comparison.title
messages.errors.file_not_found
```

**Guidelines**:
- Use lowercase with underscores
- Be specific but concise
- Group related items under same parent
- Use verbs for actions (`start`, `stop`, `add`)
- Use nouns for labels (`files`, `similarity`)

---

## Testing Translations

### Manual Testing

1. **Test English**:
   ```python
   from i18n import set_language
   set_language('en')
   # Launch UI, verify all text in English
   ```

2. **Test French**:
   ```python
   set_language('fr')
   # Launch UI, verify all text in French
   ```

3. **Test Missing Translations**:
   - Check logs for "Translation not found" warnings
   - Add missing translations

### Automated Testing

Create a test to verify all UI strings use i18n:

```python
import re

def test_no_hardcoded_strings():
    """Verify no hardcoded French strings in UI code."""

    # Files to check
    ui_files = [
        'main_window.py',
        'comparison_dialog.py',
        'progress_widgets.py'
    ]

    for filepath in ui_files:
        with open(filepath, 'r') as f:
            content = f.read()

        # Find potential hardcoded strings
        # (This is a simple heuristic)
        matches = re.findall(r'setText\(["\'](?!tr\()[^"\']+["\']\)', content)

        assert len(matches) == 0, f"Found hardcoded strings in {filepath}: {matches}"
```

---

## Common Patterns

### Pattern 1: Simple Button Text

```python
# Before
btn = QPushButton("Démarrer l'analyse")

# After
btn = QPushButton(tr("ui.buttons.start_analysis"))
```

### Pattern 2: Formatted Strings

```python
# Before
label.setText(f"{count} fichiers traités")

# After
label.setText(tr("ui.progress.files_processed", count=count))
```

### Pattern 3: Dialog Titles

```python
# Before
dialog = QDialog()
dialog.setWindowTitle("Comparaison de Vidéos")

# After
dialog = QDialog()
dialog.setWindowTitle(tr("ui.dialogs.comparison.title"))
```

### Pattern 4: Status Messages

```python
# Before
self.status_bar.showMessage("Analyse terminée")

# After
self.status_bar.showMessage(tr("messages.status.analysis_complete"))
```

### Pattern 5: Error Messages

```python
# Before
QMessageBox.warning(
    self,
    "Erreur",
    f"Fichier introuvable: {filepath}"
)

# After
QMessageBox.warning(
    self,
    tr("messages.dialogs.error"),
    tr("messages.errors.file_not_found", path=filepath)
)
```

### Pattern 6: Tooltips

```python
# Before
btn.setToolTip("Cliquer pour démarrer l'analyse")

# After
btn.setToolTip(tr("ui.tooltips.start_analysis"))
```

---

## Progress Tracking

### Migration Checklist

**UI Files** (High Priority):
- [ ] `ui/panels.py` - ~20 strings
- [ ] `main_window.py` - ~60 strings
- [ ] `comparison_dialog.py` - ~15 strings
- [ ] `progress_widgets.py` - ~25 strings
- [ ] `video_preview_widget.py` - ~10 strings

**Dialog Files** (Medium Priority):
- [ ] `subsequence_comparison_dialog.py` - ~20 strings
- [ ] `advanced_progress_dialog.py` - ~15 strings
- [ ] Settings dialogs - ~30 strings

**Handler Files** (Low Priority):
- [ ] `handlers/file_handler.py` - ~10 strings (mostly logs)
- [ ] `handlers/analysis_handler.py` - ~15 strings
- [ ] `handlers/duplicate_handler.py` - ~10 strings
- [ ] `handlers/audio_first_handler.py` - ~10 strings

**Worker Files** (Lowest Priority):
- [ ] `workers/*.py` - ~20 strings total (mostly logs)

**Estimated Total**: ~250 strings

### Coverage Goals

- **Phase 1** (Critical UI): 50+ strings → ~20% coverage
- **Phase 2** (All UI): 130+ strings → ~50% coverage
- **Phase 3** (Dialogs): 170+ strings → ~70% coverage
- **Phase 4** (Handlers): 210+ strings → ~85% coverage
- **Phase 5** (Complete): 250+ strings → ~100% coverage

---

## Best Practices

### DO ✅

- Use hierarchical keys (`ui.buttons.start` not `start_button`)
- Add both EN and FR translations simultaneously
- Test both languages after each migration
- Use descriptive key names
- Format strings with placeholders (`{count}`)
- Group related strings together

### DON'T ❌

- Don't hardcode strings anymore
- Don't use generic keys (`button1`, `text2`)
- Don't translate log messages (they're for developers)
- Don't forget to add English translations
- Don't translate variable names or code
- Don't rush - migrate carefully

---

## Tools and Helpers

### Find Hardcoded Strings

```bash
# Find all potential French strings
grep -rn '"[A-ZÀÉÈÊ]' --include="*.py" . | grep setText

# Find all potential hardcoded strings in a file
grep -n 'setText("' main_window.py

# Count hardcoded strings
grep -r 'setText("' --include="*.py" . | wc -l
```

### Check Translation Coverage

```python
from i18n import get_translator
tr = get_translator()

# Get coverage stats
print(tr.get_translation_coverage())
# → {'en': 100.0, 'fr': 95.5}

# Find missing French translations
missing = tr.get_missing_translations('fr')
print(f"Missing {len(missing)} French translations")
```

---

## Migration Example

### Before Migration

```python
# ui/panels.py (excerpt)
class FileManagementPanel(QWidget):
    def setup_ui(self):
        # Buttons
        self.add_files_btn = QPushButton("📄 Ajouter des fichiers")
        self.add_folder_btn = QPushButton("📂 Ajouter un dossier")
        self.clear_btn = QPushButton("🗑️ Effacer la liste")

        # Status
        self.status_label = QLabel("Aucun fichier sélectionné")
```

### After Migration

```python
# ui/panels.py (migrated)
from i18n import get_translator
tr = get_translator().tr

class FileManagementPanel(QWidget):
    def setup_ui(self):
        # Buttons
        self.add_files_btn = QPushButton(
            f"📄 {tr('ui.buttons.add_files')}"
        )
        self.add_folder_btn = QPushButton(
            f"📂 {tr('ui.buttons.add_folder')}"
        )
        self.clear_btn = QPushButton(
            f"🗑️ {tr('ui.buttons.clear_list')}"
        )

        # Status
        self.status_label = QLabel(tr('ui.status.no_files_selected'))
```

**Translations added to en.json**:
```json
{
  "ui": {
    "buttons": {
      "add_files": "Add files",
      "add_folder": "Add folder",
      "clear_list": "Clear list"
    },
    "status": {
      "no_files_selected": "No files selected"
    }
  }
}
```

---

## Next Steps

### Immediate Actions

1. **Start with `ui/panels.py`** (smallest, most isolated)
2. **Add missing translations** to en.json and fr.json
3. **Test thoroughly** before moving to next file
4. **Document progress** (check off items in this guide)

### Long-term Goals

1. **Phase 1**: Migrate all UI files (main_window, dialogs, widgets)
2. **Phase 2**: Add language selector to settings
3. **Phase 3**: Add more languages (Spanish, German, etc.)
4. **Phase 4**: Automated tests for translation coverage

---

## Support

### Getting Help

- **Documentation**: See this guide
- **Translation System**: Check `i18n/translator.py`
- **Examples**: Look at existing translations in `i18n/translations/*.json`
- **Issues**: Report problems on GitHub

### Contributing

If you'd like to help with i18n migration:
1. Pick a file from the checklist above
2. Follow the migration steps
3. Test your changes
4. Submit a pull request

---

**Status**: Framework complete, migration in progress
**Progress**: ~50% (framework + 150 translations)
**Remaining**: ~250 hardcoded strings to migrate

**The i18n system is ready - we just need to use it!** 🌍
