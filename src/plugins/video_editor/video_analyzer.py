import cv2
import numpy as np
from moviepy.editor import VideoFileClip
import librosa
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.Analyzer')

class VideoAnalyzer:
    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    def detect_scenes(self, threshold=30.0, min_scene_length=15):
        """Détecte les changements de scène dans la vidéo"""
        logger.debug("Début de la détection des scènes")
        scenes = []
        prev_frame = None
        start_frame = 0
        
        for frame_idx in range(self.total_frames):
            ret, frame = self.cap.read()
            if not ret:
                break
                
            # Convertir en niveaux de gris
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if prev_frame is not None:
                # Calculer la différence entre les frames
                diff = cv2.absdiff(gray, prev_frame)
                mean_diff = np.mean(diff)
                
                # Si la différence est supérieure au seuil
                if mean_diff > threshold and (frame_idx - start_frame) >= min_scene_length:
                    scenes.append((start_frame, frame_idx))
                    start_frame = frame_idx
            
            prev_frame = gray
        
        # Ajouter la dernière scène
        if start_frame < self.total_frames - 1:
            scenes.append((start_frame, self.total_frames - 1))
        
        logger.debug(f"Détection terminée : {len(scenes)} scènes trouvées")
        return scenes
    
    def extract_waveform(self, samples=1000):
        """Extrait la forme d'onde audio de la vidéo"""
        logger.debug("Extraction de la forme d'onde audio")
        try:
            # Charger la vidéo avec moviepy
            video = VideoFileClip(self.video_path)
            
            # Extraire l'audio
            audio = video.audio
            if audio is None:
                logger.warning("Pas de piste audio trouvée")
                return None
                
            # Obtenir les données audio
            audio_array = audio.to_soundarray()
            
            # Convertir en mono si stéréo
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            # Rééchantillonner pour obtenir le nombre d'échantillons souhaité
            waveform = librosa.resample(
                audio_array,
                orig_sr=audio.fps,
                target_sr=samples
            )
            
            # Normaliser entre -1 et 1
            waveform = librosa.util.normalize(waveform)
            
            logger.debug("Extraction de la forme d'onde terminée")
            return waveform
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de la forme d'onde : {str(e)}")
            return None
    
    def extract_keyframes(self, interval=1):
        """Extrait les frames clés de la vidéo"""
        logger.debug("Extraction des frames clés")
        keyframes = []
        
        for frame_idx in range(0, self.total_frames, int(self.fps * interval)):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.cap.read()
            if ret:
                keyframes.append((frame_idx, frame))
        
        logger.debug(f"Extraction terminée : {len(keyframes)} frames clés")
        return keyframes
    
    def __del__(self):
        """Libère les ressources"""
        if self.cap is not None:
            self.cap.release()
