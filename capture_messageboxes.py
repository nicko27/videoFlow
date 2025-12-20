#!/usr/bin/env python3
"""
Capture et analyse tous les message boxes du bouton Scènes.

Ce script monkey-patche QMessageBox pour capturer tous les messages.
"""
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

# Liste pour capturer tous les message boxes
captured_messages = []

# Sauvegarder les méthodes originales
_original_information = QMessageBox.information
_original_warning = QMessageBox.warning
_original_critical = QMessageBox.critical
_original_question = QMessageBox.question

def capture_information(parent, title, text, buttons=QMessageBox.StandardButton.Ok, defaultButton=QMessageBox.StandardButton.NoButton):
    """Capture les QMessageBox.information"""
    captured_messages.append({
        'type': 'INFORMATION',
        'title': title,
        'text': text,
        'buttons': str(buttons)
    })
    print(f"\n{'='*80}")
    print(f"📘 MESSAGE BOX - INFORMATION")
    print(f"{'='*80}")
    print(f"Titre: {title}")
    print(f"Texte: {text}")
    print(f"{'='*80}\n")
    return _original_information(parent, title, text, buttons, defaultButton)

def capture_warning(parent, title, text, buttons=QMessageBox.StandardButton.Ok, defaultButton=QMessageBox.StandardButton.NoButton):
    """Capture les QMessageBox.warning"""
    captured_messages.append({
        'type': 'WARNING',
        'title': title,
        'text': text,
        'buttons': str(buttons)
    })
    print(f"\n{'='*80}")
    print(f"⚠️  MESSAGE BOX - WARNING")
    print(f"{'='*80}")
    print(f"Titre: {title}")
    print(f"Texte: {text}")
    print(f"{'='*80}\n")
    return _original_warning(parent, title, text, buttons, defaultButton)

def capture_critical(parent, title, text, buttons=QMessageBox.StandardButton.Ok, defaultButton=QMessageBox.StandardButton.NoButton):
    """Capture les QMessageBox.critical"""
    captured_messages.append({
        'type': 'CRITICAL',
        'title': title,
        'text': text,
        'buttons': str(buttons)
    })
    print(f"\n{'='*80}")
    print(f"🔴 MESSAGE BOX - CRITICAL")
    print(f"{'='*80}")
    print(f"Titre: {title}")
    print(f"Texte: {text}")
    print(f"{'='*80}\n")
    return _original_critical(parent, title, text, buttons, defaultButton)

def capture_question(parent, title, text, buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, defaultButton=QMessageBox.StandardButton.NoButton):
    """Capture les QMessageBox.question"""
    captured_messages.append({
        'type': 'QUESTION',
        'title': title,
        'text': text,
        'buttons': str(buttons)
    })
    print(f"\n{'='*80}")
    print(f"❓ MESSAGE BOX - QUESTION")
    print(f"{'='*80}")
    print(f"Titre: {title}")
    print(f"Texte: {text}")
    print(f"{'='*80}\n")
    return _original_question(parent, title, text, buttons, defaultButton)

# Monkey-patch QMessageBox
QMessageBox.information = staticmethod(capture_information)
QMessageBox.warning = staticmethod(capture_warning)
QMessageBox.critical = staticmethod(capture_critical)
QMessageBox.question = staticmethod(capture_question)

def test_scene_button():
    """Test le bouton Scènes et capture les messages."""

    print("="*80)
    print("CAPTURE MESSAGE BOXES - BOUTON SCÈNES")
    print("="*80)
    print("\nDémarrage de l'application...")
    print("Le script va automatiquement cliquer sur le bouton Scènes dans 2 secondes.\n")

    app = QApplication(sys.argv)

    try:
        from src.plugins.duplicate_finder import DuplicateFinderWindow

        # Créer la fenêtre
        window = DuplicateFinderWindow()
        print("✅ Fenêtre créée\n")

        # Fonction pour simuler le clic sur le bouton Scènes
        def click_scene_button():
            print("🎬 Simulation du clic sur le bouton Scènes...\n")

            # Trouver le bouton Scènes
            # Il devrait être accessible via start_scene_detection_mode()
            try:
                # Appeler directement la méthode
                window.start_scene_detection_mode()
                print("\n✅ Méthode start_scene_detection_mode() appelée\n")
            except Exception as e:
                print(f"\n❌ ERREUR lors de l'appel: {e}\n")
                import traceback
                traceback.print_exc()

            # Fermer l'application après un délai
            QTimer.singleShot(2000, app.quit)

        # Timer pour cliquer après 2 secondes
        QTimer.singleShot(2000, click_scene_button)

        # Afficher la fenêtre
        window.show()

        # Lancer l'app
        app.exec()

        # Afficher le résumé
        print("\n" + "="*80)
        print("📊 RÉSUMÉ DES MESSAGE BOXES CAPTURÉS")
        print("="*80)

        if not captured_messages:
            print("\n✅ AUCUN message box affiché - Comportement normal\n")
        else:
            print(f"\n⚠️  {len(captured_messages)} message box(es) affiché(s):\n")
            for i, msg in enumerate(captured_messages, 1):
                print(f"{i}. [{msg['type']}] {msg['title']}")
                print(f"   Texte: {msg['text'][:100]}{'...' if len(msg['text']) > 100 else ''}")
                print()

            # Analyse des problèmes
            print("="*80)
            print("🔍 ANALYSE DES PROBLÈMES")
            print("="*80)

            for msg in captured_messages:
                if msg['type'] in ['WARNING', 'CRITICAL']:
                    print(f"\n⚠️  PROBLÈME DÉTECTÉ:")
                    print(f"   Type: {msg['type']}")
                    print(f"   Titre: {msg['title']}")
                    print(f"   Message complet:")
                    print(f"   {msg['text']}")
                    print()

        return True

    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}\n")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = test_scene_button()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompu par l'utilisateur")
        sys.exit(1)
