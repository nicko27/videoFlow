#!/usr/bin/env python3
"""
Debug détaillé du flux du bouton Scènes.

Montre l'état du file_handler à chaque étape.
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

def debug_scene_flow():
    """Debug le flux complet du bouton Scènes."""

    print("="*80)
    print("DEBUG FLUX BOUTON SCÈNES")
    print("="*80)

    app = QApplication(sys.argv)

    try:
        from src.plugins.duplicate_finder import DuplicateFinderWindow

        # Créer la fenêtre
        window = DuplicateFinderWindow()
        print("\n✅ Fenêtre créée")

        # Vérifier l'état initial du file_handler
        print(f"\n📊 État initial file_handler:")
        print(f"   - get_file_count(): {window.file_handler.get_file_count()}")
        print(f"   - Dossier dernier: {window.file_handler.last_folder if hasattr(window.file_handler, 'last_folder') else 'N/A'}")

        # Fonction pour débugger
        def debug_start_scene():
            print("\n" + "="*80)
            print("🎬 APPEL start_scene_detection_mode()")
            print("="*80)

            # État AVANT l'appel
            print(f"\n📊 État AVANT start_scene_detection_mode():")
            print(f"   - file_handler.get_file_count(): {window.file_handler.get_file_count()}")

            # Inspecter le file_handler plus en détail
            if hasattr(window.file_handler, 'files'):
                print(f"   - file_handler.files: {len(window.file_handler.files) if window.file_handler.files else 0} fichiers")
            if hasattr(window.file_handler, '_files'):
                print(f"   - file_handler._files: {len(window.file_handler._files) if window.file_handler._files else 0} fichiers")

            # Appeler la méthode ET capturer ce qui se passe
            print("\n🔍 Appel de start_scene_detection_mode()...\n")

            try:
                # Monkey-patch pour intercepter les vérifications
                original_method = window.start_scene_detection_mode

                def wrapped_method():
                    print(f"   ↳ Dans start_scene_detection_mode()")
                    print(f"   ↳ file_count = file_handler.get_file_count()")
                    fc = window.file_handler.get_file_count()
                    print(f"   ↳ file_count = {fc}")

                    if fc < 2:
                        print(f"   ↳ ❌ file_count < 2 → Affichage du message WARNING")
                        print(f"   ↳ PROBLÈME: Le file_handler dit qu'il y a {fc} fichiers!")
                    else:
                        print(f"   ↳ ✅ file_count >= 2 → Continuation normale")

                    # Appeler la méthode originale
                    return original_method()

                wrapped_method()

            except Exception as e:
                print(f"\n❌ ERREUR: {e}")
                import traceback
                traceback.print_exc()

            # État APRÈS l'appel
            print(f"\n📊 État APRÈS start_scene_detection_mode():")
            print(f"   - file_handler.get_file_count(): {window.file_handler.get_file_count()}")

            # Fermer après un délai
            QTimer.singleShot(2000, app.quit)

        # Timer pour débugger après 2 secondes
        QTimer.singleShot(2000, debug_start_scene)

        # Afficher la fenêtre
        window.show()

        # Lancer l'app
        app.exec()

        print("\n" + "="*80)
        print("📊 ANALYSE DU PROBLÈME")
        print("="*80)
        print("\nSi file_count = 0 au début, c'est normal:")
        print("  → L'utilisateur doit d'abord CHARGER un dossier via l'interface")
        print("  → Le bouton Scènes ne peut PAS charger automatiquement les fichiers")
        print("\nSolution:")
        print("  1. L'utilisateur clique sur 'Charger Dossier'")
        print("  2. L'utilisateur sélectionne un dossier")
        print("  3. Les fichiers sont chargés dans file_handler")
        print("  4. ENSUITE l'utilisateur peut cliquer sur 'Scènes'")
        print()

        return True

    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}\n")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = debug_scene_flow()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompu par l'utilisateur")
        sys.exit(1)
