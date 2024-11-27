from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
import numpy as np
import cv2
from astropy.io import fits

class PreviewDialog(QDialog):
    def __init__(self, image_data, fits_header, parent=None):
        super().__init__(parent)
        self.image_data = image_data
        self.fits_header = fits_header
        self.image_processor = parent.image_processor  # Assign image_processor from parent
        self.setWindowTitle("Preview Stacked Result")
        self.setModal(True)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add preview image
        preview_label = QLabel()
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Check if color image
        is_color = fits_header.get('COLORIMG', False)
        
        if is_color:
            # Handle color image
            # Normalize each channel
            normalized = np.zeros_like(image_data)
            if len(image_data.shape) == 3 and image_data.shape[2] == 3:
                for i in range(3):
                    channel = image_data[:, :, i]
                    normalized[:, :, i] = cv2.normalize(channel, None, 0, 255, cv2.NORM_MINMAX)
                
                # Convert to uint8
                normalized = normalized.astype(np.uint8)
                
                # Convert to LAB color space
                lab = cv2.cvtColor(normalized, cv2.COLOR_RGB2LAB)
                l, a, b = cv2.split(lab)
                
                # Apply CLAHE to L channel
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                l = clahe.apply(l)
                
                # Merge channels and convert back to RGB
                lab = cv2.merge((l, a, b))
                enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
            else:
                # Handle monochrome image treated as color
                normalized = cv2.normalize(image_data, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
                normalized = np.squeeze(normalized)  # Ensure it's 2D
                # Apply CLAHE
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                l = clahe.apply(normalized)
                # Convert back to 3-channel image
                enhanced = cv2.cvtColor(l, cv2.COLOR_GRAY2RGB)

            height, width, channels = enhanced.shape
            
            # Scale image if too large
            max_size = 800
            if width > max_size or height > max_size:
                scale = max_size / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                enhanced = cv2.resize(enhanced, (new_width, new_height))
            
            # Convert to QImage
            bytes_per_line = 3 * enhanced.shape[1]
            q_img = QImage(enhanced.data, enhanced.shape[1], enhanced.shape[0],
                         bytes_per_line, QImage.Format.Format_RGB888)
        else:
            # Handle monochrome image
            normalized = cv2.normalize(image_data, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            normalized = np.squeeze(normalized)  # Ensure it's 2D
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(normalized)  # Apply CLAHE to 2D image
            enhanced = cv2.cvtColor(l, cv2.COLOR_GRAY2RGB)
            height, width, channels = enhanced.shape
            
            # Scale image if too large
            max_size = 800
            if width > max_size or height > max_size:
                scale = max_size / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                enhanced = cv2.resize(enhanced, (new_width, new_height))
            
            # Convert to QImage
            bytes_per_line = 3 * enhanced.shape[1]
            q_img = QImage(enhanced.data, enhanced.shape[1], enhanced.shape[0],
                         bytes_per_line, QImage.Format.Format_RGB888)
        
        pixmap = QPixmap.fromImage(q_img)
        preview_label.setPixmap(pixmap)
        layout.addWidget(preview_label)
        
        # Add info label
        info_text = (f"Stacked {fits_header.get('NCOMBINE', 1)} frames - "
                    f"{'Color' if is_color else 'Monochrome'} image")
        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save as FITS")
        save_button.clicked.connect(self.save_result)
        
        discard_button = QPushButton("Discard")
        discard_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(discard_button)
        layout.addLayout(button_layout)
        
        # Set dialog size
        self.resize(pixmap.width() + 100, pixmap.height() + 100)
    
    def save_result(self):
        """Save the stacked result as FITS file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Stacked Image",
            "",
            "FITS files (*.fits);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Ensure data is in correct format
                if self.fits_header.get('COLORIMG', False):
                    # Color image - ensure proper dimensions
                    data = self.image_data.astype(np.float32)
                    # Ensure dimensions are in correct order (height, width, channels)
                    if len(data.shape) == 3 and data.shape[2] == 3:
                        data = np.transpose(data, (2, 0, 1))  # Convert to CHW
                    # Update header
                    self.fits_header['NAXIS'] = 3
                    self.fits_header['NAXIS1'] = data.shape[2]  # width
                    self.fits_header['NAXIS2'] = data.shape[1]  # height
                    self.fits_header['NAXIS3'] = 3  # RGB channels
                else:
                    # Monochrome image
                    data = self.image_data.astype(np.float32)
                    # Ensure dimensions are in correct order (height, width)
                    if len(data.shape) == 3:
                        data = np.squeeze(data)
                    # Update header
                    self.fits_header['NAXIS'] = 2
                    self.fits_header['NAXIS1'] = data.shape[1]  # width
                    self.fits_header['NAXIS2'] = data.shape[0]  # height
                
                # Merge headers and update metadata
                result_header = self.image_processor.merge_headers([self.fits_header])
                result_header['NCOMBINE'] = self.fits_header.get('NCOMBINE', 1)
                result_header.add_history(f'Stacked {self.fits_header.get("NCOMBINE", 1)} frames using astroalign')
                result_header['COLORIMG'] = self.fits_header.get('COLORIMG', False)
                
                # Set up proper FITS header structure and get data in FITS format
                # For color images, FITS expects CHW format
                # For monochrome, ensure 2D
                
                # Create HDU and save
                hdu = fits.PrimaryHDU(data=data, header=result_header)
                hdu.writeto(file_path, overwrite=True)
                self.accept()
                
            except Exception as e:
                print(f"Error saving FITS file: {str(e)}")
                self.reject()
