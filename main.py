#!/usr/bin/env python3
# Import required system modules
import sys
import os
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.core.plugin_manager import PluginManager
from src.core.logger import Logger

# Ajout du dossier racine au PYTHONPATH
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Initialize logger for the main module
logger = Logger.get_logger('Main')

def main():
    # Log application start
    logger.info("Démarrage de l'application")
    try:
        # Initialize Qt application
        app = QApplication(sys.argv)
        app.setStyle('Fusion')  # Style moderne
        
        # Create main window
        window = MainWindow()
        
        # Initialize plugin manager and setup plugins
        plugin_manager = PluginManager()
        plugin_manager.setup_plugins(window)
        
        # Show main window
        window.show()
        logger.info("Fenêtre principale affichée")
        
        # Start application event loop and exit with its return code
        sys.exit(app.exec())
    except Exception as e:
        # Log any fatal errors and exit with error code
        logger.error(f"Erreur fatale: {str(e)}", exc_info=True)
        sys.exit(1)

# Execute main function only if script is run directly
if __name__ == "__main__":
    main()
