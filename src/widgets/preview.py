from PyQt6.QtWidgets import QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
import numpy as np
import cv2
from astropy.io import fits

class PreviewWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setMinimumSize(400, 400)
        
        # Create preview label
        self.preview_label = QLabel(self)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(380, 380)
        self.preview_label.setStyleSheet("QLabel { background-color: black; }")
        
        # Center the label in the frame
        self.preview_label.setGeometry(10, 10, 380, 380)
    
    def enhance_mono_image(self, data):
        """Enhance monochrome image"""
        # Normalize to 0-255 range and convert to uint8
        normalized = cv2.normalize(data, None, 0, 255, cv2.NORM_MINMAX)
        normalized = normalized.astype(np.uint8)
        return normalized
    
    def display_fits(self, filepath):
        """Display a FITS file"""
        try:
            with fits.open(filepath) as hdul:
                data = hdul[0].data
                header = hdul[0].header
                
                # Check if color image
                is_color = header.get('COLORIMG', False)
                
                if is_color:
                    # Handle color image
                    if len(data.shape) == 3 and data.shape[2] == 3:
                        # Process each channel separately
                        enhanced = np.zeros((data.shape[0], data.shape[1], 3), dtype=np.uint8)
                        for i in range(3):
                            enhanced[:,:,i] = self.enhance_mono_image(data[:,:,i])
                    else:
                        # Handle monochrome image treated as color
                        mono = self.enhance_mono_image(data)
                        enhanced = np.stack([mono, mono, mono], axis=2)
                else:
                    # Handle monochrome image
                    mono = self.enhance_mono_image(data)
                    enhanced = np.stack([mono, mono, mono], axis=2)
                
                # Scale image to fit preview
                height, width = enhanced.shape[:2]
                max_size = 380
                if width > max_size or height > max_size:
                    scale = max_size / max(width, height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    enhanced = cv2.resize(enhanced, (new_width, new_height))
                
                # Convert to QImage and display
                height, width, channels = enhanced.shape
                bytes_per_line = 3 * width
                q_img = QImage(enhanced.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_img)
                self.preview_label.setPixmap(pixmap)
                
        except Exception as e:
            print(f"Error displaying FITS file: {str(e)}")
            self.preview_label.setText("Error loading image")
    
    def display_array(self, data, header=None):
        """Display a numpy array"""
        try:
            # Check if color image
            is_color = header.get('COLORIMG', False) if header else len(data.shape) == 3
            
            if is_color:
                # Handle color image
                if len(data.shape) == 3 and data.shape[2] == 3:
                    # Process each channel separately
                    enhanced = np.zeros((data.shape[0], data.shape[1], 3), dtype=np.uint8)
                    for i in range(3):
                        enhanced[:,:,i] = self.enhance_mono_image(data[:,:,i])
                else:
                    # Handle monochrome image treated as color
                    mono = self.enhance_mono_image(data)
                    enhanced = np.stack([mono, mono, mono], axis=2)
            else:
                # Handle monochrome image
                mono = self.enhance_mono_image(data)
                enhanced = np.stack([mono, mono, mono], axis=2)
            
            # Scale image to fit preview
            height, width = enhanced.shape[:2]
            max_size = 380
            if width > max_size or height > max_size:
                scale = max_size / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                enhanced = cv2.resize(enhanced, (new_width, new_height))
            
            # Convert to QImage and display
            height, width, channels = enhanced.shape
            bytes_per_line = 3 * width
            q_img = QImage(enhanced.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            self.preview_label.setPixmap(pixmap)
            
        except Exception as e:
            print(f"Error displaying array: {str(e)}")
            self.preview_label.setText("Error displaying image")
