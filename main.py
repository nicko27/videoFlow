import sys
import os
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.core.logger import Logger

# Ajout du dossier racine au PYTHONPATH
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

logger = Logger.get_logger('Main')

def main():
    logger.info("Démarrage de l'application")
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        logger.info("Fenêtre principale affichée")
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Erreur fatale: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
