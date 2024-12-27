import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import sys

class Logger:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not Logger._initialized:
            Logger._initialized = True
            self._setup_logger()

    def _setup_logger(self):
        """Configure le système de logging"""
        # Configuration du logger principal
        self.logger = logging.getLogger('VideoFlow')
        self.logger.setLevel(logging.DEBUG)

        # Handler pour console avec plus de détails
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)  # Changé à DEBUG pour voir tous les messages
        
        # Format des messages console
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        # Ajout du handler console
        self.logger.addHandler(console_handler)

        try:
            # Créer le dossier logs s'il n'existe pas
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
            os.makedirs(logs_dir, exist_ok=True)

            # Nom du fichier de log avec la date
            log_file = os.path.join(logs_dir, f'videoflow_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

            # Handler pour fichier avec rotation
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=100*1024*1024,  # 100MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)

            # Format des messages fichier
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)

            # Ajout du handler fichier
            self.logger.addHandler(file_handler)
        except Exception as e:
            self.logger.error(f"Erreur lors de la configuration du fichier de log: {str(e)}", exc_info=True)

        self.logger.info("Logger initialisé")

    @classmethod
    def get_logger(cls, name: str = None) -> logging.Logger:
        """Retourne un logger configuré"""
        instance = cls()
        if name:
            return logging.getLogger(f'VideoFlow.{name}')
        return instance.logger
