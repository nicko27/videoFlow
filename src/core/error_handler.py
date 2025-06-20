
"""
import time
Gestionnaire d'erreurs amélioré pour VideoFlow
"""

import logging
import traceback
import sys
from enum import Enum
from typing import Optional, Dict, Any, Callable
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Niveaux de gravité des erreurs"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorType(Enum):
    """Types d'erreurs"""
    FILE_IO = "file_io"
    NETWORK = "network"
    VALIDATION = "validation"
    THREAD = "thread"
    MEMORY = "memory"
    OPENCV = "opencv"
    FFMPEG = "ffmpeg"
    PLUGIN = "plugin"
    UI = "ui"
    UNKNOWN = "unknown"

class VideoFlowError(Exception):
    """Exception personnalisée pour VideoFlow"""
    
    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNKNOWN, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_type = error_type
        self.severity = severity
        self.details = details or {}
        self.timestamp = time.time()

class ErrorHandler(QObject):
    """Gestionnaire centralisé d'erreurs"""
    
    error_occurred = pyqtSignal(object)  # VideoFlowError
    
    def __init__(self):
        super().__init__()
        self.error_callbacks: Dict[ErrorType, Callable] = {}
    
    def register_callback(self, error_type: ErrorType, callback: Callable):
        """Enregistre un callback pour un type d'erreur"""
        self.error_callbacks[error_type] = callback
    
    def handle_error(self, error: Exception, error_type: ErrorType = ErrorType.UNKNOWN,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None) -> VideoFlowError:
        """Gère une erreur de manière centralisée"""
        
        # Créer une VideoFlowError si nécessaire
        if not isinstance(error, VideoFlowError):
            details = {"original_error": str(error)}
            if context:
                details.update(context)
            
            vf_error = VideoFlowError(
                str(error), 
                error_type=error_type,
                severity=severity,
                details=details
            )
        else:
            vf_error = error
        
        # Logger l'erreur
        self._log_error(vf_error)
        
        # Exécuter le callback spécifique
        if vf_error.error_type in self.error_callbacks:
            try:
                self.error_callbacks[vf_error.error_type](vf_error)
            except Exception as e:
                logger.error(f"Erreur dans callback {vf_error.error_type}: {e}")
        
        # Émettre le signal
        self.error_occurred.emit(vf_error)
        
        return vf_error
    
    def _log_error(self, error: VideoFlowError):
        """Log une erreur selon sa gravité"""
        log_message = f"[{error.error_type.value}] {error}"
        
        if error.details:
            log_message += f" | Détails: {error.details}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=True)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, exc_info=True)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def show_user_error(self, error: VideoFlowError, parent=None):
        """Affiche une erreur à l'utilisateur"""
        if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            QMessageBox.critical(parent, "Erreur critique", str(error))
        elif error.severity == ErrorSeverity.MEDIUM:
            QMessageBox.warning(parent, "Attention", str(error))
        else:
            QMessageBox.information(parent, "Information", str(error))

# Instance globale
error_handler = ErrorHandler()

def safe_execute(func, error_type: ErrorType = ErrorType.UNKNOWN, 
                severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                default_return=None, context: Optional[Dict[str, Any]] = None):
    """Décorateur pour exécution sécurisée"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_handler.handle_error(e, error_type, severity, context)
            return default_return
    return wrapper
