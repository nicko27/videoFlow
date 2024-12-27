from PyQt6.QtWidgets import QMainWindow, QWidget, QGridLayout
from PyQt6.QtCore import Qt
from src.core.plugin_manager import PluginManager
from src.core.logger import Logger

logger = Logger.get_logger('MainWindow')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initialisation de la fenêtre principale")
        self.plugin_manager = PluginManager()
        self.init_ui()

    def init_ui(self):
        logger.debug("Initialisation de l'interface utilisateur")
        
        # Création du widget central et du layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        grid_layout = QGridLayout(central_widget)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(20, 20, 20, 20)
        
        # Chargement des plugins
        logger.debug("Chargement des plugins")
        self.plugin_manager.load_plugins()
        plugins = self.plugin_manager.get_plugins()
        logger.info(f"Nombre de plugins chargés: {len(plugins)}")
        
        # Calcul du nombre optimal de colonnes (2 colonnes par plugin)
        num_plugins = len(plugins)
        total_columns = num_plugins * 2  # 2 colonnes par plugin
        
        # Ajout des boutons des plugins
        for i, plugin in enumerate(plugins):
            try:
                logger.debug(f"Ajout du plugin {plugin.get_name()} à la position (0, {i*2})")
                button = plugin.get_button()
                # Chaque plugin occupe 2 colonnes
                grid_layout.addWidget(button, 0, i*2, 1, 2)
            except Exception as e:
                logger.error(f"Erreur lors de l'ajout du plugin {i}: {str(e)}", exc_info=True)
        
        # Configuration de la fenêtre
        self.setWindowTitle('VideoFlow')
        
        # Calcul de la taille de la fenêtre
        button_width = 200
        button_height = 100
        total_width = (button_width * total_columns) + (grid_layout.spacing() * (total_columns - 1)) + (grid_layout.contentsMargins().left() + grid_layout.contentsMargins().right())
        total_height = button_height + (grid_layout.contentsMargins().top() + grid_layout.contentsMargins().bottom())
        
        logger.debug(f"Dimensions de la fenêtre: {total_width}x{total_height}")
        self.setMinimumSize(total_width, total_height)
        self.setMaximumSize(total_width + 50, total_height + 50)
        
        logger.info("Interface utilisateur initialisée")
