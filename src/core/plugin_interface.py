from abc import ABC, abstractmethod

class PluginInterface(ABC):
    """Interface abstraite que tous les plugins doivent implémenter"""
    
    @abstractmethod
    def __init__(self):
        """Constructeur de base pour tous les plugins"""
        self.name = ""
        self.description = ""
        self.version = ""
        self.window = None
        self.main_window = None
    
    @abstractmethod
    def setup(self, main_window):
        """Configure le plugin"""
        pass
