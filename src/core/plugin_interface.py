from abc import ABC, abstractmethod
from PyQt6.QtWidgets import QPushButton

class PluginInterface(ABC):
    """Interface abstraite que tous les plugins doivent implémenter"""
    
    def __init__(self):
        """Constructeur de base pour tous les plugins"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Retourne le nom du plugin"""
        pass
    
    @abstractmethod
    def get_button(self) -> QPushButton:
        """Retourne le bouton qui sera affiché dans la fenêtre principale"""
        pass
