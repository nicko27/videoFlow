
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import os
import sys
import inspect
import importlib
import importlib.util
import traceback
from typing import List, Dict
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger

logger = Logger.get_logger('PluginManager')


class ThreadSafePluginManager:
    """Gestionnaire de plugins thread-safe"""
    
    def __init__(self):
        self.plugins = []
        self.plugins_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plugins')
        self._lock = threading.RLock()
        self._loaded = False
        
        # Ajouter le répertoire racine au PYTHONPATH
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
            logger.debug(f"Ajout de {root_dir} au PYTHONPATH")
    
    def load_plugins(self) -> List[PluginInterface]:
        """Charge tous les plugins de manière thread-safe"""
        with self._lock:
            if self._loaded:
                return self.plugins
            
            logger.debug("Chargement des plugins...")
            logger.debug(f"Dossier des plugins: {self.plugins_dir}")
            
            if not os.path.exists(self.plugins_dir):
                logger.error(f"Le dossier plugins n'existe pas: {self.plugins_dir}")
                return self.plugins
            
            # Charger en parallèle avec pool de threads
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                
                for plugin_folder in os.listdir(self.plugins_dir):
                    plugin_path = os.path.join(self.plugins_dir, plugin_folder)
                    
                    if not os.path.isdir(plugin_path) or plugin_folder.startswith('_'):
                        continue
                    
                    future = executor.submit(self._load_single_plugin, plugin_folder, plugin_path)
                    futures.append(future)
                
                # Récupérer les résultats
                for future in as_completed(futures):
                    try:
                        plugin = future.result(timeout=30)
                        if plugin:
                            self.plugins.append(plugin)
                    except Exception as e:
                        logger.error(f"Erreur chargement plugin: {e}")
            
            self._loaded = True
            logger.info(f"{len(self.plugins)} plugins chargés")
            return self.plugins
    
    def _load_single_plugin(self, plugin_folder: str, plugin_path: str) -> Optional[PluginInterface]:
        """Charge un plugin unique"""
        try:
            plugin_file = os.path.join(plugin_path, 'plugin.py')
            init_file = os.path.join(plugin_path, '__init__.py')
            
            if not os.path.exists(plugin_file) or not os.path.exists(init_file):
                logger.warning(f"Structure de plugin invalide dans {plugin_folder}")
                return None
            
            # Charger le module
            spec = importlib.util.spec_from_file_location(
                f"src.plugins.{plugin_folder}.plugin",
                plugin_file
            )
            
            if not spec or not spec.loader:
                logger.error(f"Impossible de créer le spec pour {plugin_file}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # Chercher la classe plugin
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PluginInterface) and 
                    obj != PluginInterface):
                    try:
                        plugin = obj()
                        logger.info(f"Plugin chargé : {plugin.name}")
                        return plugin
                    except Exception as e:
                        logger.error(f"Erreur instanciation plugin {name}: {e}")
                        return None
            
            logger.warning(f"Aucune classe plugin trouvée dans {plugin_folder}")
            return None
            
        except Exception as e:
            logger.error(f"Erreur chargement plugin {plugin_folder}: {e}")
            return None
    
    def setup_plugins(self, main_window):
        """Configure tous les plugins de manière thread-safe"""
        with self._lock:
            for plugin in self.plugins:
                try:
                    plugin.setup(main_window)
                    logger.debug(f"Plugin configuré : {plugin.name}")
                except Exception as e:
                    logger.error(f"Erreur configuration plugin {plugin.name}: {e}")
    
    def get_plugins(self) -> List[PluginInterface]:
        """Retourne la liste des plugins de manière thread-safe"""
        with self._lock:
            return self.plugins.copy()
    
    def reload_plugins(self):
        """Recharge tous les plugins"""
        with self._lock:
            self._loaded = False
            self.plugins.clear()
            self.load_plugins()

# Alias pour compatibilité
PluginManager = ThreadSafePluginManager


    def load_plugins(self) -> List[PluginInterface]:
        """Charge tous les plugins disponibles"""
        logger.debug("Chargement des plugins...")
        logger.debug(f"Dossier des plugins: {self.plugins_dir}")
        
        if not os.path.exists(self.plugins_dir):
            logger.error(f"Le dossier plugins n'existe pas: {self.plugins_dir}")
            return self.plugins

        # Parcourir tous les dossiers dans plugins/
        for plugin_folder in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, plugin_folder)
            logger.debug(f"Vérification du dossier: {plugin_path}")
            
            # Ignorer les fichiers et les dossiers commençant par _
            if not os.path.isdir(plugin_path) or plugin_folder.startswith('_'):
                continue
            
            # Vérifier la présence des fichiers nécessaires
            plugin_file = os.path.join(plugin_path, 'plugin.py')
            init_file = os.path.join(plugin_path, '__init__.py')
            
            if not os.path.exists(plugin_file) or not os.path.exists(init_file):
                logger.warning(f"Structure de plugin invalide dans {plugin_folder}")
                continue
            
            try:
                logger.debug(f"Tentative de chargement du plugin: {plugin_folder}")
                
                # Charger le module plugin.py
                spec = importlib.util.spec_from_file_location(
                    f"src.plugins.{plugin_folder}.plugin",
                    plugin_file
                )
                if not spec or not spec.loader:
                    logger.error(f"Impossible de créer le spec pour {plugin_file}")
                    continue
                
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                logger.debug(f"Module chargé: {module}")
                
                # Chercher une classe qui hérite de PluginInterface
                plugin_found = False
                for name, obj in inspect.getmembers(module):
                    logger.debug(f"Inspection de {name}")
                    if (inspect.isclass(obj) and 
                        issubclass(obj, PluginInterface) and 
                        obj != PluginInterface):
                        try:
                            plugin = obj()
                            self.plugins.append(plugin)
                            self.plugin_map[plugin.name] = plugin
                            logger.info(f"Plugin chargé : {plugin.name}")
                            plugin_found = True
                        except Exception as e:
                            logger.error(f"Erreur lors de l'instanciation du plugin {name}: {str(e)}")
                            logger.error(traceback.format_exc())
                
                if not plugin_found:
                    logger.warning(f"Aucune classe de plugin trouvée dans {plugin_folder}")
            
            except Exception as e:
                logger.error(f"Erreur lors du chargement du plugin {plugin_folder}: {str(e)}")
                logger.error(traceback.format_exc())
        
        logger.info(f"{len(self.plugins)} plugins chargés")
        return self.plugins

    def setup_plugins(self, main_window):
        """Configure tous les plugins"""
        for plugin in self.plugins:
            try:
                plugin.setup(main_window)
                logger.debug(f"Plugin configuré : {plugin.name}")
            except Exception as e:
                logger.error(f"Erreur lors de la configuration du plugin {plugin.name}: {str(e)}")
                logger.error(traceback.format_exc())

    def get_plugins(self) -> List[PluginInterface]:
        """Retourne la liste des plugins chargés"""
        return self.plugins
        
    def get_plugin_by_name(self, name: str) -> PluginInterface:
        """Retourne un plugin par son nom"""
        return self.plugin_map.get(name)
        
    def configure_plugins(self):
        """Méthode de compatibilité pour l'ancien code"""
        logger.warning("La méthode configure_plugins() est obsolète, utilisez setup_plugins(main_window) à la place")
        # Cette méthode ne fait rien, elle est là pour la compatibilité
