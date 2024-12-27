import re
from dataclasses import dataclass
from typing import Optional, Tuple
from src.core.logger import Logger

logger = Logger.get_logger('SequenceManager')

@dataclass
class SequencePattern:
    """Configuration d'un pattern de séquence."""
    type: str  # 'numeric' ou 'alpha'
    position: str  # 'start', 'end' ou position spécifique
    length: int
    case: str = 'any'  # 'upper', 'lower' ou 'any' pour alpha
    
    def __post_init__(self):
        if self.type not in ['numeric', 'alpha']:
            raise ValueError("Type doit être 'numeric' ou 'alpha'")
        if self.case not in ['upper', 'lower', 'any']:
            raise ValueError("Case doit être 'upper', 'lower' ou 'any'")

class SequenceManager:
    """Gestionnaire de séquences numériques et alphabétiques."""
    
    @staticmethod
    def detect_sequence(text: str, pattern: SequencePattern) -> Optional[Tuple[int, int]]:
        """
        Détecte une séquence selon le pattern spécifié.
        
        Args:
            text: Texte à analyser
            pattern: Configuration de la séquence à détecter
            
        Returns:
            Optional[Tuple[int, int]]: Position début et fin de la séquence si trouvée
        """
        if pattern.type == 'numeric':
            return SequenceManager._detect_numeric_sequence(text, pattern)
        else:
            return SequenceManager._detect_alpha_sequence(text, pattern)
    
    @staticmethod
    def _detect_numeric_sequence(text: str, pattern: SequencePattern) -> Optional[Tuple[int, int]]:
        """Détecte une séquence numérique."""
        # Pattern pour une séquence de chiffres de longueur spécifique
        regex = rf"\d{{{pattern.length}}}"
        
        if pattern.position == 'start':
            regex = f"^{regex}"
        elif pattern.position == 'end':
            regex = f"{regex}$"
        elif pattern.position.isdigit():
            pos = int(pattern.position)
            if pos >= len(text):
                return None
            # Vérifie à une position spécifique
            match = re.match(rf".{{{pos}}}{regex}", text)
            if match:
                return (pos, pos + pattern.length)
            return None
        
        match = re.search(regex, text)
        if match:
            return match.span()
        return None
    
    @staticmethod
    def _detect_alpha_sequence(text: str, pattern: SequencePattern) -> Optional[Tuple[int, int]]:
        """Détecte une séquence alphabétique."""
        # Pattern pour une séquence de lettres de longueur spécifique
        if pattern.case == 'upper':
            regex = rf"[A-Z]{{{pattern.length}}}"
        elif pattern.case == 'lower':
            regex = rf"[a-z]{{{pattern.length}}}"
        else:
            regex = rf"[A-Za-z]{{{pattern.length}}}"
        
        if pattern.position == 'start':
            regex = f"^{regex}"
        elif pattern.position == 'end':
            regex = f"{regex}$"
        elif pattern.position.isdigit():
            pos = int(pattern.position)
            if pos >= len(text):
                return None
            # Vérifie à une position spécifique
            match = re.match(rf".{{{pos}}}{regex}", text)
            if match:
                return (pos, pos + pattern.length)
            return None
        
        match = re.search(regex, text)
        if match:
            return match.span()
        return None
    
    @staticmethod
    def remove_sequence(text: str, pattern: SequencePattern) -> str:
        """
        Supprime une séquence du texte selon le pattern spécifié.
        
        Args:
            text: Texte à modifier
            pattern: Configuration de la séquence à supprimer
            
        Returns:
            str: Texte avec la séquence supprimée
        """
        sequence_pos = SequenceManager.detect_sequence(text, pattern)
        if sequence_pos:
            start, end = sequence_pos
            return text[:start] + text[end:]
        return text
