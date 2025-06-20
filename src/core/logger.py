
import logging
import os
import sys
import json
import time
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from pathlib import Path
from typing import Dict, Any, Optional
import queue

class StructuredFormatter(logging.Formatter):
    """Formateur structuré pour les logs JSON"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'thread_name': record.threadName
        }
        
        # Ajouter les données supplémentaires
        if hasattr(record, 'extra_data'):
            log_entry['extra'] = record.extra_data
        
        # Ajouter l'exception si présente
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)

class ThreadSafeLogger:
    """Logger thread-safe avec queue"""
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        with self._lock:
            if self._initialized:
                return
            
            self._initialized = True
            self.log_queue = queue.Queue()
            self.setup_logging()
    
    def setup_logging(self):
        """Configure le système de logging thread-safe"""
        # Créer le répertoire de logs
        logs_dir = Path(__file__).parent.parent.parent / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        # Configurer les handlers
        handlers = []
        
        # Handler console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)
        
        # Handler fichier principal
        main_log_file = logs_dir / f'videoflow_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler = RotatingFileHandler(
            main_log_file,
            maxBytes=100*1024*1024,  # 100MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(console_formatter)
        handlers.append(file_handler)
        
        # Handler JSON structuré
        json_log_file = logs_dir / f'videoflow_structured_{datetime.now().strftime("%Y%m%d")}.jsonl'
        json_handler = RotatingFileHandler(
            json_log_file,
            maxBytes=100*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(StructuredFormatter())
        handlers.append(json_handler)
        
        # Handler d'erreurs séparé
        error_log_file = logs_dir / f'videoflow_errors_{datetime.now().strftime("%Y%m%d")}.log'
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=50*1024*1024,
            backupCount=10,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s\n'
            'Thread: %(threadName)s (%(thread)d)\n'
            '%(exc_info)s\n' + '-'*80
        ))
        handlers.append(error_handler)
        
        # Configurer le queue listener pour thread safety
        self.queue_listener = QueueListener(self.log_queue, *handlers, respect_handler_level=True)
        self.queue_listener.start()
        
        # Configurer le logger racine
        root_logger = logging.getLogger('VideoFlow')
        root_logger.setLevel(logging.DEBUG)
        
        # Ajouter un queue handler
        queue_handler = QueueHandler(self.log_queue)
        root_logger.addHandler(queue_handler)
        
        # Éviter la duplication avec le logger racine
        root_logger.propagate = False
        
        self.logger = root_logger
        self.logger.info("Logger thread-safe initialisé")
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """Retourne un logger configuré"""
        if name:
            return logging.getLogger(f'VideoFlow.{name}')
        return self.logger
    
    def log_with_context(self, level: int, message: str, **context):
        """Log avec contexte supplémentaire"""
        record = self.logger.makeRecord(
            self.logger.name, level, __file__, 0, message, (), None
        )
        record.extra_data = context
        self.logger.handle(record)
    
    def shutdown(self):
        """Arrête proprement le logging"""
        if hasattr(self, 'queue_listener'):
            self.queue_listener.stop()

# Instance globale
_logger_instance = ThreadSafeLogger()

class Logger:
    """Classe Logger pour compatibilité"""
    
    @staticmethod
    def get_logger(name: str = None) -> logging.Logger:
        return _logger_instance.get_logger(name)
    
    @staticmethod
    def log_with_context(level: int, message: str, **context):
        return _logger_instance.log_with_context(level, message, **context)
    
    @staticmethod
    def shutdown():
        return _logger_instance.shutdown()

# Fonctions utilitaires
def log_performance(func):
    """Décorateur pour mesurer les performances"""
    def wrapper(*args, **kwargs):
        logger = Logger.get_logger('Performance')
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.3f}s: {e}")
            raise
    
    return wrapper

def log_method_calls(cls):
    """Décorateur de classe pour logger les appels de méthodes"""
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and not attr_name.startswith('_'):
            setattr(cls, attr_name, log_performance(attr))
    return cls
