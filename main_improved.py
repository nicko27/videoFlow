
#!/usr/bin/env python3
"""
VideoFlow - Application de gestion vidéo améliorée
Point d'entrée principal avec sécurités intégrées
"""

import sys
import os
import signal
import traceback
import atexit
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, qInstallMessageHandler, QtMsgType, QTimer

# Ajouter le dossier racine au PYTHONPATH
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Imports des modules améliorés
try:
    from src.core.logger import Logger, ThreadSafeLogger
    from src.core.error_handler import ErrorHandler, VideoFlowError, ErrorType, ErrorSeverity
    from src.core.signal_handler import SignalHandler, signal_handler
    from src.core.platform_utils import PlatformInfo, PathUtils, initialize_platform_dirs
    from src.ui.main_window import MainWindow
    from src.core.plugin_manager import ThreadSafePluginManager
except ImportError as e:
    print(f"Erreur critique: Impossible d'importer les modules nécessaires: {e}")
    print("Assurez-vous que tous les modules de réparation ont été correctement installés.")
    sys.exit(1)

# Logger global
logger = Logger.get_logger('VideoFlow.Main')
error_handler = ErrorHandler()

class VideoFlowApplication:
    """Application VideoFlow sécurisée"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.plugin_manager = None
        self._shutdown_requested = False
        
        # Configuration des gestionnaires
        self.setup_error_handling()
        self.setup_signal_handling()
        self.setup_qt_message_handling()
    
    def setup_error_handling(self):
        """Configure la gestion d'erreurs globale"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            """Gestionnaire d'exceptions non capturées"""
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            error_msg = f"Exception non gérée: {exc_type.__name__}: {exc_value}"
            logger.critical(error_msg, exc_info=(exc_type, exc_value, exc_traceback))
            
            # Afficher un dialogue d'erreur si Qt est disponible
            if self.app and not self._shutdown_requested:
                try:
                    QMessageBox.critical(
                        None,
                        "Erreur critique",
                        f"Une erreur critique s'est produite:

{error_msg}

"
                        "L'application va se fermer. Consultez les logs pour plus de détails."
                    )
                except Exception:
                    pass  # Qt peut ne pas être disponible
            
            self.shutdown(1)
        
        sys.excepthook = handle_exception
    
    def setup_signal_handling(self):
        """Configure la gestion des signaux"""
        def on_shutdown():
            """Gestionnaire d'arrêt gracieux"""
            if not self._shutdown_requested:
                logger.info("Arrêt gracieux demandé")
                self.shutdown(0)
        
        def on_cleanup():
            """Gestionnaire de nettoyage"""
            logger.info("Nettoyage demandé")
            self.cleanup_resources()
        
        signal_handler.shutdown_requested.connect(on_shutdown)
        signal_handler.cleanup_requested.connect(on_cleanup)
        
        # Enregistrer les callbacks de nettoyage
        signal_handler.add_shutdown_callback(self.cleanup_resources)
    
    def setup_qt_message_handling(self):
        """Configure la gestion des messages Qt"""
        def qt_message_handler(msg_type, context, message):
            """Gestionnaire des messages Qt"""
            if msg_type == QtMsgType.QtDebugMsg:
                logger.debug(f"Qt Debug: {message}")
            elif msg_type == QtMsgType.QtWarningMsg:
                logger.warning(f"Qt Warning: {message}")
            elif msg_type == QtMsgType.QtCriticalMsg:
                logger.error(f"Qt Critical: {message}")
            elif msg_type == QtMsgType.QtFatalMsg:
                logger.critical(f"Qt Fatal: {message}")
                self.shutdown(1)
        
        qInstallMessageHandler(qt_message_handler)
    
    def initialize_application(self):
        """Initialise l'application Qt"""
        try:
            # Créer l'application Qt
            self.app = QApplication(sys.argv)
            self.app.setStyle('Fusion')
            
            # Configuration de base
            self.app.setApplicationName("VideoFlow")
            self.app.setApplicationVersion("2.0.0")
            self.app.setOrganizationName("VideoFlow")
            
            # Gérer la fermeture de l'application
            self.app.aboutToQuit.connect(self.cleanup_resources)
            
            logger.info("Application Qt initialisée")
            return True
            
        except Exception as e:
            logger.critical(f"Erreur initialisation Qt: {e}")
            return False
    
    def initialize_plugins(self):
        """Initialise le système de plugins"""
        try:
            self.plugin_manager = ThreadSafePluginManager()
            plugins = self.plugin_manager.load_plugins()
            
            logger.info(f"{len(plugins)} plugins chargés")
            return True
            
        except Exception as e:
            logger.error(f"Erreur chargement plugins: {e}")
            return False
    
    def create_main_window(self):
        """Crée la fenêtre principale"""
        try:
            self.main_window = MainWindow()
            
            # Configurer les plugins
            if self.plugin_manager:
                self.plugin_manager.setup_plugins(self.main_window)
            
            # Afficher la fenêtre
            self.main_window.show()
            
            logger.info("Fenêtre principale créée et affichée")
            return True
            
        except Exception as e:
            logger.error(f"Erreur création fenêtre principale: {e}")
            return False
    
    def run(self):
        """Lance l'application"""
        try:
            logger.info("=== Démarrage de VideoFlow ===")
            logger.info(f"Plateforme: {PlatformInfo.get_platform_name()}")
            logger.info(f"Architecture: {PlatformInfo.get_architecture()}")
            
            # Initialiser les répertoires de la plateforme
            initialize_platform_dirs()
            
            # Initialiser Qt
            if not self.initialize_application():
                return 1
            
            # Initialiser les plugins
            if not self.initialize_plugins():
                logger.warning("Certains plugins n'ont pas pu être chargés")
            
            # Créer l'interface
            if not self.create_main_window():
                return 1
            
            # Programmer un nettoyage périodique
            cleanup_timer = QTimer()
            cleanup_timer.timeout.connect(self.periodic_cleanup)
            cleanup_timer.start(300000)  # 5 minutes
            
            logger.info("VideoFlow démarré avec succès")
            
            # Lancer la boucle d'événements
            return self.app.exec()
            
        except Exception as e:
            logger.critical(f"Erreur fatale lors du démarrage: {e}")
            return 1
        finally:
            self.cleanup_resources()
    
    def periodic_cleanup(self):
        """Nettoyage périodique des ressources"""
        try:
            import gc
            import psutil
            
            # Forcer le garbage collection
            collected = gc.collect()
            if collected > 0:
                logger.debug(f"Garbage collection: {collected} objets nettoyés")
            
            # Surveiller la mémoire
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > 1000:  # Plus de 1GB
                logger.warning(f"Utilisation mémoire élevée: {memory_mb:.1f}MB")
            
            logger.debug(f"Nettoyage périodique - Mémoire: {memory_mb:.1f}MB")
            
        except Exception as e:
            logger.error(f"Erreur nettoyage périodique: {e}")
    
    def cleanup_resources(self):
        """Nettoie toutes les ressources"""
        if self._shutdown_requested:
            return
        
        logger.info("Nettoyage des ressources...")
        
        try:
            # Nettoyer les plugins
            if self.plugin_manager:
                # Arrêter tous les workers en cours
                for plugin in self.plugin_manager.get_plugins():
                    if hasattr(plugin, 'cleanup'):
                        try:
                            plugin.cleanup()
                        except Exception as e:
                            logger.error(f"Erreur nettoyage plugin {plugin.name}: {e}")
            
            # Fermer la fenêtre principale
            if self.main_window:
                try:
                    self.main_window.close()
                except Exception as e:
                    logger.error(f"Erreur fermeture fenêtre: {e}")
            
            # Arrêter le logging
            try:
                Logger.shutdown()
            except Exception as e:
                print(f"Erreur arrêt logging: {e}")
            
            logger.info("Ressources nettoyées")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
    
    def shutdown(self, exit_code: int = 0):
        """Arrêt complet de l'application"""
        if self._shutdown_requested:
            return
        
        self._shutdown_requested = True
        logger.info(f"Arrêt de l'application (code: {exit_code})")
        
        try:
            self.cleanup_resources()
            
            if self.app:
                self.app.quit()
            
            sys.exit(exit_code)
            
        except Exception as e:
            logger.critical(f"Erreur lors de l'arrêt: {e}")
            os._exit(exit_code)

def check_dependencies():
    """Vérifie les dépendances requises"""
    missing_deps = []
    
    # Dépendances critiques
    critical_deps = [
        ('PyQt6', 'PyQt6'),
        ('cv2', 'opencv-python'),
        ('numpy', 'numpy'),
    ]
    
    for module_name, package_name in critical_deps:
        try:
            __import__(module_name)
        except ImportError:
            missing_deps.append(package_name)
    
    # Dépendances optionnelles
    optional_deps = [
        ('moviepy', 'moviepy'),
        ('ffmpeg', 'ffmpeg-python'),
        ('psutil', 'psutil'),
    ]
    
    missing_optional = []
    for module_name, package_name in optional_deps:
        try:
            __import__(module_name)
        except ImportError:
            missing_optional.append(package_name)
    
    if missing_deps:
        print("ERREUR: Dépendances critiques manquantes:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nInstallez avec: pip install " + " ".join(missing_deps))
        return False
    
    if missing_optional:
        print("ATTENTION: Dépendances optionnelles manquantes:")
        for dep in missing_optional:
            print(f"  - {dep}")
        print("\nCertaines fonctionnalités pourraient être limitées.")
    
    return True

def check_system_requirements():
    """Vérifie les prérequis système"""
    issues = []
    
    # Vérifier Python
    if sys.version_info < (3, 8):
        issues.append(f"Python 3.8+ requis (actuel: {sys.version})")
    
    # Vérifier l'espace disque
    try:
        from src.core.platform_utils import PathUtils
        import shutil
        
        temp_dir = PathUtils.get_temp_dir()
        free_space = shutil.disk_usage(temp_dir.parent).free
        
        if free_space < 1024 * 1024 * 1024:  # 1GB
            issues.append(f"Espace disque insuffisant: {free_space // (1024*1024)}MB disponibles")
    
    except Exception as e:
        issues.append(f"Impossible de vérifier l'espace disque: {e}")
    
    # Vérifier FFmpeg
    try:
        from src.core.platform_utils import FFmpegUtils
        if not FFmpegUtils.find_ffmpeg():
            issues.append("FFmpeg non trouvé dans le PATH")
    except Exception:
        issues.append("Impossible de vérifier FFmpeg")
    
    if issues:
        print("ATTENTION: Problèmes système détectés:")
        for issue in issues:
            print(f"  - {issue}")
        print()
    
    return len(issues) == 0

def main():
    """Point d'entrée principal"""
    print("VideoFlow - Gestionnaire de Vidéos (Version améliorée)")
    print("=" * 50)
    
    # Vérifications préliminaires
    if not check_dependencies():
        return 1
    
    check_system_requirements()  # Non bloquant
    
    # Créer et lancer l'application
    app = VideoFlowApplication()
    
    # Enregistrer le nettoyage à la sortie
    atexit.register(app.cleanup_resources)
    
    try:
        return app.run()
    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur")
        return 0
    except Exception as e:
        print(f"Erreur fatale: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
