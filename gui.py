#!/usr/bin/env python3
"""
Point d'entrée graphique de l'application VideoFlow
"""

import sys
import os

# Ajout du chemin du projet au PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from PyQt6.QtWidgets import QApplication
from src.ui.main.main_window import MainWindow

def main():
    """Fonction principale de l'application"""
    app = QApplication(sys.argv)
    
    # Configuration de l'application
    app.setApplicationName("VideoFlow")
    app.setOrganizationName("VideoFlow")
    app.setOrganizationDomain("videoflow.local")
    
    # Création et affichage de la fenêtre principale
    window = MainWindow()
    window.show()
    
    # Exécution de l'application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
