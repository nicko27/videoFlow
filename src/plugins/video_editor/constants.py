"""Constants for the plugin Video Editor"""

# Formats vidéo supportés
SUPPORTED_VIDEO_FORMATS = {
    'mp4': 'MP4 (*.mp4)',
    'mov': 'QuickTime (*.mov)',
    'avi': 'AVI (*.avi)',
    'mkv': 'Matroska (*.mkv)',
    'webm': 'WebM (*.webm)',
}

# Codecs vidéo supportés
VIDEO_CODECS = {
    'libx264': 'H.264 (recommandé)',
    'libx265': 'H.265/HEVC (haute compression)',
    'libvpx-vp9': 'VP9 (open source)',
}

# Codecs audio supportés
AUDIO_CODECS = {
    'aac': 'AAC (recommandé)',
    'libmp3lame': 'MP3',
    'libvorbis': 'Vorbis',
}

# Préréglages de qualité
QUALITY_PRESETS = {
    'high': {
        'video_codec': 'libx264',
        'video_bitrate': '5000k',
        'audio_codec': 'aac',
        'audio_bitrate': '192k',
        'crf': 18,
    },
    'medium': {
        'video_codec': 'libx264',
        'video_bitrate': '2500k',
        'audio_codec': 'aac',
        'audio_bitrate': '128k',
        'crf': 23,
    },
    'low': {
        'video_codec': 'libx264',
        'video_bitrate': '1000k',
        'audio_codec': 'aac',
        'audio_bitrate': '96k',
        'crf': 28,
    },
}

# Settings de détection de scènes
SCENE_DETECTION = {
    'threshold': 30.0,  # Seuil de différence entre the frames
    'min_scene_length': 15,  # Longueur minimale d'une scène en frames
}

# Settings d'interface
UI = {
    'min_window_width': 1200,
    'min_window_height': 800,
    'preview_width': 640,
    'preview_height': 360,
    'waveform_height': 100,
    'timeline_height': 50,
    'segments_table_height': 150,
}

# Messages d'error
ERROR_MESSAGES = {
    'no_video': "Aucune vidéo n'est ouverte",
    'no_segments': "Aucun segment à save",
    'invalid_segment': "Le segment est invalide",
    'save_error': "Error saving",
    'load_error': "Error loading",
    'codec_error': "Codec non supporté",
}

# Messages d'information
INFO_MESSAGES = {
    'scene_detection': "Détection des scènes in progress...",
    'save_success': "Vidéo sauvegardée with success !",
    'processing': "Processing...",
    'ready': "Ready",
}
