"""
Optimized video preview widget for duplicate comparison
"""

import os
import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QFont
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.VideoPreview')


class VideoPreviewWidget(QWidget):
    """Simple and efficient video preview widget"""

    # Signal emitted when a frame is loaded
    frame_loaded = pyqtSignal(int)
    
    def __init__(self, video_path, side_name="Video", parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.side_name = side_name
        self.cap = None
        self.total_frames = 0
        self.fps = 30.0
        self.duration = 0.0
        self.current_frame = 0
        
        self.setup_ui()
        self.load_video_info()
        
    def setup_ui(self):
        """Configure the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Main preview area
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(350, 280)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px solid #DDDDDD;
                border-radius: 8px;
                background-color: #000000;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setText("Loading...")
        layout.addWidget(self.preview_label)

        # Compact information section
        info_frame = self.create_info_section()
        layout.addWidget(info_frame)
        
    def create_info_section(self):
        """Create the information section"""
        frame = QFrame()
        frame.setMinimumHeight(65)
        frame.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #E9ECEF;
                border-radius: 4px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Filename
        filename = os.path.basename(self.video_path)
        if len(filename) > 60:
            filename = filename[:57] + "..."

        self.filename_label = QLabel(filename)
        self.filename_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.filename_label.setStyleSheet("color: #495057;")
        self.filename_label.setWordWrap(True)
        layout.addWidget(self.filename_label)

        # Technical info
        self.info_label = QLabel("Analysis in progress...")
        self.info_label.setFont(QFont("Arial", 12))
        self.info_label.setStyleSheet("color: #6C757D;")
        layout.addWidget(self.info_label)

        return frame
        
    def load_video_info(self):
        """Load video information and display a frame at 10%"""
        try:
            # File information
            file_size = os.path.getsize(self.video_path)
            size_text = self.format_file_size(file_size)

            # Video information with OpenCV
            cv2.setLogLevel(0)
            self.cap = cv2.VideoCapture(self.video_path)

            if self.cap.isOpened():
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
                self.duration = self.total_frames / self.fps if self.fps > 0 else 0

                # Update info display
                duration_text = self.format_duration(self.duration)
                self.info_label.setText(f"{size_text} • {duration_text}")

                # Show frame at 10% from the start
                frame_at_10_percent = int(self.total_frames * 0.1) if self.total_frames > 0 else 0
                self.show_frame(frame_at_10_percent)

            else:
                self.info_label.setText(f"{size_text} • Read error")
                self.preview_label.setText("❌ Cannot open")

            cv2.setLogLevel(1)

        except Exception as e:
            logger.error(f"Error loading {self.video_path}: {e}")
            self.info_label.setText("Error")
            self.preview_label.setText("❌ Loading error")
    
    def show_frame(self, frame_number):
        """Display a specific frame"""
        if not self.cap or not self.cap.isOpened() or self.total_frames == 0:
            return

        try:
            # Limit frame number
            frame_number = max(0, min(frame_number, self.total_frames - 1))
            self.current_frame = frame_number

            # Read the frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = self.cap.read()

            if ret and frame is not None:
                # Convert to QPixmap
                pixmap = self.frame_to_pixmap(frame)
                if pixmap:
                    self.preview_label.setPixmap(pixmap)
                    self.frame_loaded.emit(frame_number)
                else:
                    self.preview_label.setText("Conversion error")
            else:
                self.preview_label.setText(f"Frame {frame_number} unavailable")

        except Exception as e:
            logger.error(f"Error displaying frame {frame_number}: {e}")
            self.preview_label.setText("Display error")
    
    def seek_to_position(self, position):
        """Seek to a relative position (0.0 to 1.0)"""
        if self.total_frames > 0:
            frame_number = int(position * (self.total_frames - 1))
            self.show_frame(frame_number)

    def frame_to_pixmap(self, frame):
        """Convert an OpenCV frame to a resized QPixmap"""
        try:
            # Resize while maintaining aspect ratio
            label_size = self.preview_label.size()
            target_width = label_size.width() - 4  # Margin for border
            target_height = label_size.height() - 4

            height, width = frame.shape[:2]
            aspect_ratio = width / height

            # Calculate new dimensions
            if aspect_ratio > target_width / target_height:
                new_width = target_width
                new_height = int(target_width / aspect_ratio)
            else:
                new_height = target_height
                new_width = int(target_height * aspect_ratio)

            # Resize
            resized_frame = cv2.resize(frame, (new_width, new_height))

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

            # Create QImage
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

            return QPixmap.fromImage(qt_image)

        except Exception as e:
            logger.error(f"Error converting frame: {e}")
            return None
    
    def format_file_size(self, size_bytes):
        """Format file size"""
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.0f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.0f}MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"

    def format_duration(self, seconds):
        """Format duration"""
        if seconds >= 3600:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h{minutes:02d}m"
        else:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"

    def get_frame_at_percent(self, percent):
        """Get frame number at a given percentage"""
        if self.total_frames > 0:
            return int((percent / 100.0) * (self.total_frames - 1))
        return 0

    def cleanup(self):
        """Release resources"""
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
        except Exception as e:
            logger.error(f"Error cleaning up {self.video_path}: {e}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()