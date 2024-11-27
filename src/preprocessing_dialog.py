from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QSlider, QCheckBox, QGroupBox, QTabWidget,
                           QWidget)
from PyQt6.QtCore import Qt
import cv2
import numpy as np
from astropy.io import fits
from scipy import ndimage
from skimage.feature import peak_local_max

class PreprocessingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Register Settings")
        self.setMinimumWidth(500)
        
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Actions tab
        actions_tab = QWidget()
        actions_layout = QVBoxLayout(actions_tab)
        
        # Star detection group
        star_group = QGroupBox("Star detection")
        star_layout = QVBoxLayout(star_group)
        
        # Star detection threshold
        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("Star detection threshold")
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(1, 100)
        self.threshold_slider.setValue(10)
        self.threshold_value = QLabel("10%")
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_value.setText(f"{v}%"))
        
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_value)
        star_layout.addLayout(threshold_layout)
        
        # Compute stars button
        self.compute_stars_btn = QPushButton("Compute the number of detected stars")
        star_layout.addWidget(self.compute_stars_btn)
        
        actions_layout.addWidget(star_group)
        
        # Noise reduction group
        noise_group = QGroupBox("Noise Reduction")
        noise_layout = QVBoxLayout(noise_group)
        
        self.reduce_noise_cb = QCheckBox("Reduce noise by using a median filter")
        noise_layout.addWidget(self.reduce_noise_cb)
        
        actions_layout.addWidget(noise_group)
        
        # Hot pixel detection group
        hot_pixel_group = QGroupBox("Hot Pixel Detection")
        hot_pixel_layout = QVBoxLayout(hot_pixel_group)
        
        self.detect_hot_pixels_cb = QCheckBox("Detect and mark hot pixels")
        hot_pixel_layout.addWidget(self.detect_hot_pixels_cb)
        
        actions_layout.addWidget(hot_pixel_group)
        
        # Star trail detection group
        trail_group = QGroupBox("Star Trail Detection")
        trail_layout = QVBoxLayout(trail_group)
        
        self.detect_trails_cb = QCheckBox("Detect star trails")
        trail_layout.addWidget(self.detect_trails_cb)
        
        actions_layout.addWidget(trail_group)
        
        # Add actions tab
        tab_widget.addTab(actions_tab, "Actions")
        
        # Add Advanced tab (placeholder)
        advanced_tab = QWidget()
        tab_widget.addTab(advanced_tab, "Advanced")
        
        layout.addWidget(tab_widget)
        
        # Add bottom buttons
        button_layout = QHBoxLayout()
        
        self.recommended_btn = QPushButton("Recommended Settings...")
        self.stacking_btn = QPushButton("Stacking Settings...")
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.recommended_btn)
        button_layout.addWidget(self.stacking_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    @staticmethod
    def analyze_image(filepath):
        """Analyze a FITS image and return quality metrics"""
        with fits.open(filepath) as hdul:
            data = hdul[0].data
            
            # Normalize data
            normalized = cv2.normalize(data, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            
            # Detect stars
            stars = peak_local_max(normalized, min_distance=5, 
                                 threshold_rel=0.2,
                                 num_peaks=1000)
            num_stars = len(stars)
            
            # Calculate FWHM (average star width)
            fwhm_values = []
            for star in stars[:20]:  # Use first 20 stars for speed
                y, x = star
                if y-5 >= 0 and y+6 <= data.shape[0] and x-5 >= 0 and x+6 <= data.shape[1]:
                    star_region = data[y-5:y+6, x-5:x+6]
                    fwhm = np.mean([star_region.shape[0], star_region.shape[1]]) / 2
                    fwhm_values.append(fwhm)
            fwhm = np.mean(fwhm_values) if fwhm_values else 0
            
            # Calculate background sky level
            mask = np.zeros_like(normalized, dtype=bool)
            for star in stars:
                y, x = star
                y, x = int(y), int(x)
                mask[max(0, y-3):min(mask.shape[0], y+4),
                     max(0, x-3):min(mask.shape[1], x+4)] = True
            sky_level = np.median(normalized[~mask])
            sky_background = (sky_level / 255.0) * 100
            
            # Detect hot pixels
            hot_pixel_threshold = np.percentile(data, 99.9)
            hot_pixels = np.sum(data > hot_pixel_threshold)
            
            # Detect star trails
            edges = cv2.Canny(normalized, 100, 200)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, 
                                  minLineLength=20, maxLineGap=5)
            has_trails = lines is not None and len(lines) > 10
            
            # Calculate overall score (0-100)
            score = 0
            score += min(num_stars * 2, 40)  # Up to 40 points for stars
            score += max(0, 20 - (fwhm * 2))  # Up to 20 points for sharpness
            score += max(0, 20 - (sky_background / 5))  # Up to 20 points for dark sky
            score -= min(hot_pixels / 100, 10)  # Subtract up to 10 points for hot pixels
            score -= 20 if has_trails else 0  # Subtract 20 points for star trails
            
            return {
                "Score": round(score, 2),
                "Stars": num_stars,
                "FWHM": round(fwhm, 2),
                "Sky Background": f"{round(sky_background, 2)}%",
                "Hot Pixels": hot_pixels,
                "Star Trails": "Yes" if has_trails else "No"
            }
