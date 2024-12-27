import os
import json
from typing import List, Dict
from src.core.logger import Logger

logger = Logger.get_logger('RegexRenamer.PatternManager')

class PatternManager:
    """Gère la sauvegarde et le chargement des patterns regex."""
    
    def __init__(self):
        """Initialise le gestionnaire de patterns."""
        self.data_dir = os.path.join("data", "regex_renamer")
        self.patterns_file = os.path.join(self.data_dir, "patterns.json")
        self.patterns: List[Dict] = []
        
        # Créer le dossier si nécessaire
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.load_patterns()
    
    def load_patterns(self) -> None:
        """Charge les patterns depuis le fichier JSON."""
        try:
            if os.path.exists(self.patterns_file):
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    self.patterns = json.load(f)
                logger.debug(f"Patterns chargés : {len(self.patterns)} patterns trouvés")
            else:
                self.patterns = []
                logger.debug("Aucun pattern existant")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des patterns : {e}")
            self.patterns = []
    
    def save_patterns(self) -> None:
        """Sauvegarde les patterns dans le fichier JSON."""
        try:
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.patterns, f, indent=2, ensure_ascii=False)
            logger.debug(f"Patterns sauvegardés : {len(self.patterns)} patterns")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des patterns : {e}")
    
    def add_pattern(self, pattern: str, replace_with: str = "", enabled: bool = True) -> None:
        """Ajoute un nouveau pattern à la liste."""
        new_pattern = {
            "pattern": pattern,
            "replace_with": replace_with,
            "enabled": enabled
        }
        self.patterns.append(new_pattern)
        self.save_patterns()
        logger.debug(f"Pattern ajouté : {pattern}")
    
    def remove_pattern(self, index: int) -> None:
        """Supprime un pattern de la liste."""
        if 0 <= index < len(self.patterns):
            removed = self.patterns.pop(index)
            self.save_patterns()
            logger.debug(f"Pattern supprimé : {removed['pattern']}")
    
    def toggle_pattern(self, index: int) -> None:
        """Active/désactive un pattern."""
        if 0 <= index < len(self.patterns):
            self.patterns[index]['enabled'] = not self.patterns[index]['enabled']
            self.save_patterns()
            logger.debug(f"Pattern {self.patterns[index]['pattern']} : {'activé' if self.patterns[index]['enabled'] else 'désactivé'}")
    
    def get_active_patterns(self) -> List[Dict]:
        """Retourne la liste des patterns actifs."""
        return [p for p in self.patterns if p['enabled']]
    
    def get_all_patterns(self) -> List[Dict]:
        """Retourne tous les patterns."""
        return self.patterns
