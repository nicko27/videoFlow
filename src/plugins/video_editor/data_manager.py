import json
import os
from datetime import datetime
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.DataManager')

class DataManager:
    def __init__(self, video_path):
        self.video_path = video_path
        self.data_dir = os.path.join(os.path.dirname(video_path), '.videoflow')
        self.data_file = os.path.join(
            self.data_dir,
            f"{os.path.splitext(os.path.basename(video_path))[0]}.json"
        )
        
        # Créer le dossier de données si nécessaire
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # Charger ou créer les données
        self.load_data()
    
    def load_data(self):
        """Charge les données du fichier JSON"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
                logger.debug(f"Données chargées depuis {self.data_file}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement des données : {str(e)}")
                self.init_data()
        else:
            self.init_data()
    
    def init_data(self):
        """Initialise les données par défaut"""
        self.data = {
            'video_path': self.video_path,
            'last_modified': datetime.now().isoformat(),
            'segments': [],
            'scenes': [],
            'markers': [],
            'history': [],
            'metadata': {}
        }
        self.save_data()
    
    def save_data(self):
        """Sauvegarde les données dans le fichier JSON"""
        try:
            self.data['last_modified'] = datetime.now().isoformat()
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=4)
            logger.debug(f"Données sauvegardées dans {self.data_file}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données : {str(e)}")
    
    def add_segment(self, start_time, end_time, name=None):
        """Ajoute un segment"""
        segment = {
            'start': start_time,
            'end': end_time,
            'name': name or f"Segment {len(self.data['segments']) + 1}",
            'created_at': datetime.now().isoformat()
        }
        self.data['segments'].append(segment)
        self.save_data()
        return segment
    
    def remove_segment(self, index):
        """Supprime un segment"""
        if 0 <= index < len(self.data['segments']):
            segment = self.data['segments'].pop(index)
            self.save_data()
            return segment
        return None
    
    def update_segment(self, index, **kwargs):
        """Met à jour un segment"""
        if 0 <= index < len(self.data['segments']):
            self.data['segments'][index].update(kwargs)
            self.save_data()
            return self.data['segments'][index]
        return None
    
    def add_marker(self, time, name, color=None):
        """Ajoute un marqueur"""
        marker = {
            'time': time,
            'name': name,
            'color': color or '#FF0000',
            'created_at': datetime.now().isoformat()
        }
        self.data['markers'].append(marker)
        self.save_data()
        return marker
    
    def remove_marker(self, index):
        """Supprime un marqueur"""
        if 0 <= index < len(self.data['markers']):
            marker = self.data['markers'].pop(index)
            self.save_data()
            return marker
        return None
    
    def add_scene(self, start_frame, end_frame):
        """Ajoute une scène détectée"""
        scene = {
            'start_frame': start_frame,
            'end_frame': end_frame,
            'created_at': datetime.now().isoformat()
        }
        self.data['scenes'].append(scene)
        self.save_data()
        return scene
    
    def add_to_history(self, action, details):
        """Ajoute une action à l'historique"""
        history_entry = {
            'action': action,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.data['history'].append(history_entry)
        self.save_data()
        return history_entry
    
    def update_metadata(self, key, value):
        """Met à jour les métadonnées"""
        self.data['metadata'][key] = value
        self.save_data()
    
    def get_segments(self):
        """Retourne tous les segments"""
        return self.data['segments']
    
    def get_markers(self):
        """Retourne tous les marqueurs"""
        return self.data['markers']
    
    def get_scenes(self):
        """Retourne toutes les scènes"""
        return self.data['scenes']
    
    def get_history(self):
        """Retourne l'historique"""
        return self.data['history']
    
    def get_metadata(self, key=None):
        """Retourne les métadonnées"""
        if key is None:
            return self.data['metadata']
        return self.data['metadata'].get(key)
