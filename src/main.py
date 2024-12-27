#!/usr/bin/env python3
"""
Point d'entrée principal de l'application VideoFlow
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.main.main_window import MainWindow

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
