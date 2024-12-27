import os
import importlib.util
import inspect
import sys
import traceback
from typing import List
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger

logger = Logger.get_logger('PluginManager')

class PluginManager:
    def __init__(self):
        self.plugins: List[PluginInterface] = []
        
        # Chemin absolu vers le dossier plugins
        self.plugins_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plugins')
        logger.info(f"PluginManager initialisé avec le dossier: {self.plugins_dir}")
        logger.debug(f"Le dossier existe: {os.path.exists(self.plugins_dir)}")
        
        if os.path.exists(self.plugins_dir):
            logger.debug("Contenu du dossier plugins:")
            for item in os.listdir(self.plugins_dir):
                item_path = os.path.join(self.plugins_dir, item)
                if os.path.isdir(item_path):
                    logger.debug(f"  - Dossier: {item}")
                    logger.debug(f"    Contenu:")
                    for subitem in os.listdir(item_path):
                        logger.debug(f"      - {subitem}")
                else:
                    logger.debug(f"  - Fichier: {item}")
        else:
            logger.error("Dossier plugins non trouvé")

    def load_plugins(self):
        """Charge tous les plugins disponibles"""
        logger.info("Début du chargement des plugins")
        try:
            if not os.path.exists(self.plugins_dir):
                logger.error(f"Le dossier plugins n'existe pas: {self.plugins_dir}")
                return

            plugin_folders = [d for d in os.listdir(self.plugins_dir) 
                            if os.path.isdir(os.path.join(self.plugins_dir, d)) and 
                            not d.startswith('__')]
            
            logger.debug(f"Dossiers de plugins trouvés: {plugin_folders}")
            
            for plugin_folder in plugin_folders:
                plugin_path = os.path.join(self.plugins_dir, plugin_folder)
                plugin_file = os.path.join(plugin_path, 'plugin.py')
                init_file = os.path.join(plugin_path, '__init__.py')
                
                logger.debug(f"Vérification du dossier {plugin_folder}:")
                logger.debug(f"  - plugin.py existe: {os.path.exists(plugin_file)}")
                logger.debug(f"  - __init__.py existe: {os.path.exists(init_file)}")
                
                if os.path.exists(plugin_file) and os.path.exists(init_file):
                    logger.debug(f"Tentative de chargement du plugin depuis: {plugin_file}")
                    try:
                        self._load_plugin(plugin_file, plugin_folder)
                    except Exception as e:
                        logger.error(f"Erreur lors du chargement du plugin {plugin_folder}: {str(e)}")
                        logger.error(f"Traceback complet:\n{traceback.format_exc()}")
                else:
                    logger.warning(f"Fichiers manquants dans: {plugin_path}")
                    if not os.path.exists(plugin_file):
                        logger.warning(f"  - plugin.py manquant")
                    if not os.path.exists(init_file):
                        logger.warning(f"  - __init__.py manquant")
            
            logger.info(f"Plugins chargés: {[type(p).__name__ for p in self.plugins]}")
            
            # Liste des plugins chargés avec leurs méthodes
            for plugin in self.plugins:
                logger.debug(f"Plugin {type(plugin).__name__}:")
                for name, method in inspect.getmembers(plugin, inspect.ismethod):
                    logger.debug(f"  - Méthode: {name}")
                    
        except Exception as e:
            logger.error(f"Erreur lors du chargement des plugins: {str(e)}")
            logger.error(f"Traceback complet:\n{traceback.format_exc()}")

    def _load_plugin(self, plugin_file: str, plugin_name: str):
        """Charge un plugin spécifique"""
        try:
            logger.debug(f"Chargement du plugin depuis: {plugin_file}")
            
            # Import du module
            spec = importlib.util.spec_from_file_location(f"src.plugins.{plugin_name}.plugin", plugin_file)
            if not spec or not spec.loader:
                logger.error(f"Impossible de créer le spec pour: {plugin_file}")
                return
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            logger.debug(f"Module chargé. Contenu:")
            for name, obj in inspect.getmembers(module):
                logger.debug(f"  - {name}: {type(obj)}")
            
            # Recherche de la classe Plugin
            if hasattr(module, 'Plugin'):
                plugin_class = getattr(module, 'Plugin')
                if inspect.isclass(plugin_class):
                    # Vérification que la classe hérite de PluginInterface
                    if issubclass(plugin_class, PluginInterface):
                        logger.debug(f"Classe Plugin valide trouvée dans {plugin_file}")
                        try:
                            plugin = plugin_class()
                            self.plugins.append(plugin)
                            logger.info(f"Plugin chargé avec succès: {plugin.get_name()}")
                        except Exception as e:
                            logger.error(f"Erreur lors de l'instanciation du plugin: {str(e)}")
                            logger.error(f"Traceback complet:\n{traceback.format_exc()}")
                    else:
                        logger.error(f"La classe Plugin dans {plugin_file} n'hérite pas de PluginInterface")
                else:
                    logger.error(f"'Plugin' n'est pas une classe dans: {plugin_file}")
            else:
                logger.error(f"Classe Plugin non trouvée dans: {plugin_file}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du plugin {plugin_file}: {str(e)}")
            logger.error(f"Traceback complet:\n{traceback.format_exc()}")
            raise

    def get_plugins(self) -> List[PluginInterface]:
        """Retourne la liste des plugins chargés"""
        logger.debug(f"Retourne {len(self.plugins)} plugins")
        return self.plugins
