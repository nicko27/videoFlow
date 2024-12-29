#!/usr/bin/env python3
import sys
from PyQt6.QtWidgets import QApplication
from src.core.plugin_manager import PluginManager
from src.core.logger import Logger

logger = Logger.get_logger('VideoFlow.Main')

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Style moderne
    
    # Initialiser le gestionnaire de plugins
    plugin_manager = PluginManager()
    plugin_manager.load_plugins()
    plugin_manager.configure_plugins()
    
    # Lancer l'application
    sys.exit(app.exec())

if __name__ == '__main__':
    main()