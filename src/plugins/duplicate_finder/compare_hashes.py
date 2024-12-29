import numpy as np

def compute_hash_similarity(hash1, hash2):
    """Calcule la similarité entre deux hashs
    
    Args:
        hash1: Premier hash à comparer (tableau numpy)
        hash2: Second hash à comparer (tableau numpy)
        
    Returns:
        float: Pourcentage de similarité entre 0 et 100
    """
    if hash1.shape != hash2.shape:
        return 0
    
    # Compare les bits des hashs
    matching_bits = np.sum(hash1 == hash2)
    total_bits = hash1.size
    
    # Calcule le pourcentage de similarité
    return (matching_bits / total_bits) * 100

def are_similar(hash1, hash2, duration1, duration2, threshold=0.9, ignore_duration=5):
    """Compare deux hashs de vidéos pour déterminer si elles sont similaires
    
    Args:
        hash1: Premier hash à comparer (tableau numpy)
        hash2: Second hash à comparer (tableau numpy)
        duration1: Durée de la première vidéo en secondes
        duration2: Durée de la seconde vidéo en secondes
        threshold: Seuil de similarité (entre 0 et 1)
        ignore_duration: Différence de durée maximale en minutes, ou float('inf') pour ignorer
        
    Returns:
        bool: True si les vidéos sont similaires, False sinon
    """
    # Vérifie d'abord la durée si on ne l'ignore pas
    if ignore_duration != float('inf'):
        duration_diff = abs(duration1 - duration2)
        max_diff = ignore_duration * 60  # Convertit en secondes
        if duration_diff > max_diff:
            return False
            
    # Compare les hashs
    if not isinstance(hash1, np.ndarray) or not isinstance(hash2, np.ndarray):
        return False
        
    # Vérifie que les hashs ont le même nombre d'images clés
    if len(hash1) != len(hash2):
        return False
        
    # Compare chaque image clé
    total_similarity = 0
    for frame1, frame2 in zip(hash1, hash2):
        similarity = compute_hash_similarity(frame1, frame2)
        total_similarity += similarity
        
    # Calcule la similarité moyenne
    avg_similarity = total_similarity / len(hash1)
    
    return avg_similarity >= (threshold * 100)  # Convertit le seuil en pourcentage
