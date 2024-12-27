"""
Classe pour gérer les patterns de remplacement
"""

import re

class ReplacePattern:
    def __init__(self, find="", replace="", is_regex=True, description=""):
        self.find = find
        self.replace = replace
        self.is_regex = is_regex
        self.description = description

    def apply(self, text):
        """Applique le pattern de remplacement au texte"""
        try:
            if self.is_regex:
                pattern = re.compile(self.find)
                if callable(self.replace):
                    return pattern.sub(self.replace, text)
                return pattern.sub(self.replace, text)
            return text.replace(self.find, self.replace)
        except re.error:
            # Si l'expression régulière est invalide, faire un remplacement simple
            return text.replace(self.find, self.replace)

    @staticmethod
    def get_predefined_patterns():
        """Retourne la liste des patterns prédéfinis"""
        return [
            ReplacePattern(r"\s+", "_", True, "Espaces → _"),
            ReplacePattern(r"[^\w\s-]", "", True, "Supprimer caractères spéciaux"),
            ReplacePattern(r"^(\d+)", r"episode_\1", True, "Préfixer numéros avec 'episode_'"),
            ReplacePattern(r"[A-Z]", lambda m: m.group().lower(), True, "Majuscules → minuscules"),
            ReplacePattern(r"_+", "_", True, "Multiples _ → un seul"),
            ReplacePattern(r"(\d+)", lambda m: m.group(1).zfill(2), True, "Padding numéros avec 0"),
        ]
