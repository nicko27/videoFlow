"""
Ce fichier est obsolète et a été remplacé par /main.py à la racine du projet.
Veuillez utiliser le fichier main.py à la racine du projet à la place.
"""

# Ce fichier est conservé pour des raisons de compatibilité
# mais ne devrait plus être utilisé.

import sys
import os

# Redirige vers le main.py à la racine
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
main_path = os.path.join(root_dir, 'main.py')

print(f"Ce fichier est obsolète. Veuillez utiliser {main_path} à la place.")
sys.exit(1)