from .plugin import RegexRenamerPlugin

def get_plugin():
    """Retourne l'instance du plugin."""
    return RegexRenamerPlugin()

def get_plugin_name():
    """Retourne le nom du plugin."""
    return "Regex Renamer"

def get_plugin_icon():
    """Retourne l'icône Unicode du plugin."""
    return "⚯"  # U+26AF TURNED BLACK MARS
