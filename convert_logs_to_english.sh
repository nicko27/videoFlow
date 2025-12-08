#!/bin/bash
# Script to convert all French log messages to English in VideoFlow plugins

# video_converter/converter.py - Remaining conversions
sed -i '' 's/logger\.warning(f"Cannot nettoyer/logger.warning(f"Cannot clean up/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.info(f"Tentative {attempt} pour/logger.info(f"Attempt {attempt} for/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.debug(f"Error lecture progrès:/logger.debug(f"Error reading progress:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.info(f"Mode compression itérative: cible=/logger.info(f"Iterative compression mode: target=/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.info(f"Itération {iteration}\/{max_iterations}:/logger.info(f"Iteration {iteration}\/{max_iterations}:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.warning(f"Itération {iteration} échouée:/logger.warning(f"Iteration {iteration} failed:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.info(f"Utilisation du meilleur résultat précédent/logger.info(f"Using best previous result/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.info(f"Résultat itération {iteration}:/logger.info(f"Iteration {iteration} result:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.info(f"✓ Taille cible atteinte:/logger.info(f"✓ Target size reached:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.info(f"✗ Taille encore trop grande:/logger.info(f"✗ Size still too large:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.warning(f"CRF max atteint/logger.warning(f"Max CRF reached/' src/plugins/video_converter/converter.py
sed -i '' 's/arrêt des itérations"/stopping iterations"/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.warning(f"Nombre max d.itérations atteint/logger.warning(f"Max number of iterations reached/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.debug(f"Saves créée:/logger.debug(f"Backup created:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.debug(f"Original remplacé:/logger.debug(f"Original replaced:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.info(f"Saves restaurée:/logger.info(f"Backup restored:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.error(f"Error during remplacement de l.original:/logger.error(f"Error replacing original file:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.debug(f"Original supprimé:/logger.debug(f"Original deleted:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.warning(f"Cannot remove l.original:/logger.warning(f"Cannot delete original:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.debug(f"Métadonnées enregistrées pour/logger.debug(f"Metadata saved for/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.warning(f"Impossible d.enregistrer les métadonnées:/logger.warning(f"Unable to save metadata:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.debug(f"Statistics enregistrées pour/logger.debug(f"Statistics saved for/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.warning(f"Impossible d.enregistrer les statistics:/logger.warning(f"Unable to save statistics:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.warning(f"Impossible d.enregistrer l.failed:/logger.warning(f"Unable to save failure:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.error(f"Error critique lors of the finalisation:/logger.error(f"Critical error during finalization:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.info(f"Démarrage compression itérative pour/logger.info(f"Starting iterative compression for/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.info(f"Tentative {self.current_attempt} échouée pour/logger.info(f"Attempt {self.current_attempt} failed for/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.error(f"Error critique in le worker:/logger.error(f"Critical error in worker:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.warning(f"Cannot marquer le file comme non-compressible:/logger.warning(f"Cannot mark file as non-compressible:/' src/plugins/video_converter/converter.py
sed -i '' 's/logger\.info(f"File marqué comme non-compressible:/logger.info(f"File marked as non-compressible:/' src/plugins/video_converter/converter.py

echo "video_converter/converter.py log messages converted to English"
