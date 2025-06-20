
"""
Gestionnaire d'états UI centralisé pour VideoFlow
"""

from enum import Enum
from typing import Dict, Any, Optional, Callable, Set
from PyQt6.QtCore import QObject, pyqtSignal
import threading

class UIState(Enum):
    """États possibles de l'interface"""
    IDLE = "idle"
    LOADING = "loading"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    CONVERTING = "converting"
    EXPORTING = "exporting"
    ERROR = "error"

class UIStateManager(QObject):
    """Gestionnaire centralisé des états UI"""
    
    state_changed = pyqtSignal(object, object)  # old_state, new_state
    
    def __init__(self):
        super().__init__()
        self._current_state = UIState.IDLE
        self._state_stack = []
        self._lock = threading.RLock()
        self._state_listeners: Dict[UIState, Set[Callable]] = {}
        
        # Contexte de l'état actuel
        self._context: Dict[str, Any] = {}
    
    def get_state(self) -> UIState:
        """Retourne l'état actuel"""
        with self._lock:
            return self._current_state
    
    def set_state(self, new_state: UIState, context: Optional[Dict[str, Any]] = None):
        """Change l'état de manière thread-safe"""
        with self._lock:
            old_state = self._current_state
            self._current_state = new_state
            
            if context:
                self._context.update(context)
            else:
                self._context.clear()
            
            # Notifier les listeners
            if new_state in self._state_listeners:
                for listener in self._state_listeners[new_state]:
                    try:
                        listener(old_state, new_state, self._context.copy())
                    except Exception as e:
                        logger.error(f"Erreur listener état {new_state}: {e}")
            
            # Émettre le signal
            self.state_changed.emit(old_state, new_state)
    
    def push_state(self, new_state: UIState, context: Optional[Dict[str, Any]] = None):
        """Empile un nouvel état (permet de revenir au précédent)"""
        with self._lock:
            self._state_stack.append((self._current_state, self._context.copy()))
            self.set_state(new_state, context)
    
    def pop_state(self):
        """Revient à l'état précédent"""
        with self._lock:
            if self._state_stack:
                old_state, old_context = self._state_stack.pop()
                self.set_state(old_state, old_context)
                return True
            return False
    
    def get_context(self, key: str = None) -> Any:
        """Retourne le contexte de l'état actuel"""
        with self._lock:
            if key:
                return self._context.get(key)
            return self._context.copy()
    
    def add_state_listener(self, state: UIState, callback: Callable):
        """Ajoute un listener pour un état spécifique"""
        with self._lock:
            if state not in self._state_listeners:
                self._state_listeners[state] = set()
            self._state_listeners[state].add(callback)
    
    def remove_state_listener(self, state: UIState, callback: Callable):
        """Supprime un listener"""
        with self._lock:
            if state in self._state_listeners:
                self._state_listeners[state].discard(callback)
    
    def is_busy(self) -> bool:
        """Vérifie si l'application est occupée"""
        with self._lock:
            return self._current_state not in [UIState.IDLE, UIState.ERROR]

# Instance globale
ui_state_manager = UIStateManager()
