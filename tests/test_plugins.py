
"""
Tests pour les plugins
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import os

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.plugin_manager import ThreadSafePluginManager
from src.core.plugin_interface import PluginInterface

class MockPlugin(PluginInterface):
    """Plugin mock pour les tests"""
    
    def __init__(self):
        super().__init__()
        self.name = "Mock Plugin"
        self.description = "Plugin de test"
        self.version = "1.0.0"
        self.setup_called = False
    
    def setup(self, main_window):
        self.setup_called = True
        self.main_window = main_window

class TestPluginManager(unittest.TestCase):
    """Tests pour le gestionnaire de plugins"""
    
    def setUp(self):
        self.plugin_manager = ThreadSafePluginManager()
    
    def test_plugin_manager_creation(self):
        """Test création du gestionnaire"""
        self.assertIsNotNone(self.plugin_manager)
        self.assertIsInstance(self.plugin_manager.plugins, list)
    
    def test_thread_safety(self):
        """Test thread safety basique"""
        import threading
        
        results = []
        
        def load_plugins():
            plugins = self.plugin_manager.get_plugins()
            results.append(len(plugins))
        
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=load_plugins)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Tous les threads devraient retourner le même nombre
        self.assertTrue(all(r == results[0] for r in results))

class TestMockPlugin(unittest.TestCase):
    """Tests pour le plugin mock"""
    
    def test_plugin_interface(self):
        """Test interface du plugin"""
        plugin = MockPlugin()
        
        self.assertEqual(plugin.name, "Mock Plugin")
        self.assertEqual(plugin.description, "Plugin de test")
        self.assertEqual(plugin.version, "1.0.0")
        self.assertFalse(plugin.setup_called)
    
    def test_plugin_setup(self):
        """Test setup du plugin"""
        plugin = MockPlugin()
        mock_window = "mock_window"
        
        plugin.setup(mock_window)
        
        self.assertTrue(plugin.setup_called)
        self.assertEqual(plugin.main_window, mock_window)

if __name__ == '__main__':
    unittest.main()
