
"""
Gestionnaire de signaux système pour VideoFlow
"""

import signal
import sys
import threading
import time
from typing import Callable, Dict, List
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class SignalHandler(QObject):
    """Gestionnaire des signaux système"""
    
    shutdown_requested = pyqtSignal()
    cleanup_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.shutdown_callbacks: List[Callable] = []
        self.cleanup_callbacks: List[Callable] = []
        self._shutdown_initiated = False
        self._lock = threading.RLock()
        
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Configure les gestionnaires de signaux"""
        if sys.platform != 'win32':
            # Unix/Linux/macOS
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGHUP, self._cleanup_handler)
        else:
            # Windows
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGBREAK, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Gestionnaire principal des signaux d'arrêt"""
        with self._lock:
            if self._shutdown_initiated:
                return  # Éviter les appels multiples
            
            self._shutdown_initiated = True
            signal_name = signal.Signals(signum).name
            logger.info(f"Signal {signal_name} reçu, arrêt en cours...")
            
            # Émettre le signal Qt
            self.shutdown_requested.emit()
            
            # Exécuter les callbacks d'arrêt
            for callback in self.shutdown_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Erreur callback arrêt: {e}")
            
            # Programmer l'arrêt forcé après délai
            QTimer.singleShot(10000, self._force_shutdown)  # 10 secondes
    
    def _cleanup_handler(self, signum, frame):
        """Gestionnaire pour les signaux de nettoyage"""
        logger.info(f"Signal {signal.Signals(signum).name} reçu, nettoyage...")
        
        self.cleanup_requested.emit()
        
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Erreur callback nettoyage: {e}")
    
    def _force_shutdown(self):
        """Arrêt forcé si l'arrêt gracieux échoue"""
        logger.warning("Arrêt forcé après timeout")
        sys.exit(1)
    
    def add_shutdown_callback(self, callback: Callable):
        """Ajoute un callback d'arrêt"""
        with self._lock:
            self.shutdown_callbacks.append(callback)
    
    def add_cleanup_callback(self, callback: Callable):
        """Ajoute un callback de nettoyage"""
        with self._lock:
            self.cleanup_callbacks.append(callback)
    
    def remove_shutdown_callback(self, callback: Callable):
        """Supprime un callback d'arrêt"""
        with self._lock:
            if callback in self.shutdown_callbacks:
                self.shutdown_callbacks.remove(callback)
    
    def remove_cleanup_callback(self, callback: Callable):
        """Supprime un callback de nettoyage"""
        with self._lock:
            if callback in self.cleanup_callbacks:
                self.cleanup_callbacks.remove(callback)
    
    def graceful_shutdown(self):
        """Arrêt gracieux programmatique"""
        self._signal_handler(signal.SIGTERM, None)

# Instance globale
signal_handler = SignalHandler()

def register_cleanup(func: Callable):
    """Décorateur pour enregistrer une fonction de nettoyage"""
    signal_handler.add_cleanup_callback(func)
    return func

def register_shutdown(func: Callable):
    """Décorateur pour enregistrer une fonction d'arrêt"""
    signal_handler.add_shutdown_callback(func)
    return func
