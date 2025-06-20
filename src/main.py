"""
Ce fichier redirige vers le main.py principal à la racine du projet.
"""

import sys
import os
from pathlib import Path

# Rediriger vers le main.py à la racine
root_dir = Path(__file__).parent.parent
main_path = root_dir / 'main.py'

if main_path.exists():
    # Ajouter le répertoire racine au path
    sys.path.insert(0, str(root_dir))
    
    # Importer et exécuter le main principal
    import importlib.util
    spec = importlib.util.spec_from_file_location("main", main_path)
    main_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_module)
else:
    print(f"Erreur: {main_path} introuvable")
    sys.exit(1)
