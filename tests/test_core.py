
"""
Tests pour les modules core
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Ajouter le projet au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import Logger
from src.core.error_handler import ErrorHandler, VideoFlowError, ErrorType, ErrorSeverity

class TestLogger(unittest.TestCase):
    """Tests pour le système de logging"""
    
    def setUp(self):
        self.logger = Logger.get_logger('Test')
    
    def test_logger_creation(self):
        """Test création du logger"""
        self.assertIsNotNone(self.logger)
        self.assertEqual(self.logger.name, 'VideoFlow.Test')
    
    def test_logging_levels(self):
        """Test des différents niveaux de log"""
        # Ces tests ne feront que vérifier que les appels ne lèvent pas d'exception
        self.logger.debug("Test debug")
        self.logger.info("Test info")
        self.logger.warning("Test warning")
        self.logger.error("Test error")

class TestErrorHandler(unittest.TestCase):
    """Tests pour le gestionnaire d'erreurs"""
    
    def setUp(self):
        self.error_handler = ErrorHandler()
    
    def test_error_creation(self):
        """Test création d'erreur personnalisée"""
        error = VideoFlowError(
            "Test error",
            ErrorType.VALIDATION,
            ErrorSeverity.MEDIUM
        )
        
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.error_type, ErrorType.VALIDATION)
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
    
    def test_error_handling(self):
        """Test gestion d'erreur"""
        test_error = ValueError("Test exception")
        
        handled_error = self.error_handler.handle_error(
            test_error,
            ErrorType.VALIDATION,
            ErrorSeverity.LOW
        )
        
        self.assertIsInstance(handled_error, VideoFlowError)
        self.assertEqual(handled_error.error_type, ErrorType.VALIDATION)

class TestValidators(unittest.TestCase):
    """Tests pour les validateurs"""
    
    def setUp(self):
        # Créer un fichier de test temporaire
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test_video.mp4"
        self.test_file.write_text("fake video content")
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_file_exists_validation(self):
        """Test validation existence fichier"""
        from src.core.validators import FileValidator
        
        # Fichier existant
        valid, msg = FileValidator.validate_video_file(self.test_file)
        # Note: Sera False car ce n'est pas un vrai fichier vidéo
        # mais au moins il existe
        self.assertIn("Fichier", msg)
        
        # Fichier inexistant
        fake_file = self.temp_dir / "nonexistent.mp4"
        valid, msg = FileValidator.validate_video_file(fake_file)
        self.assertFalse(valid)
        self.assertIn("inexistant", msg)

if __name__ == '__main__':
    unittest.main()
