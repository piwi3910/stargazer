import numpy as np
from photutils.detection import DAOStarFinder
from photutils.background import Background2D, MedianBackground
from astropy.stats import sigma_clip

class ImageAnalysis:
    def __init__(self):
        """Initialize image analysis"""
        pass

    def normalize_image(self, data):
        """Normalize image data to positive values"""
        if len(data.shape) == 3:
            if data.shape[0] == 3:  # If channels first, transpose
                data = np.transpose(data, (1, 2, 0))
            normalized = np.zeros_like(data, dtype=np.float32)
            
            for i in range(3):
                channel = data[:,:,i]
                min_val = np.min(channel)
                channel = channel - min_val
                clipped = sigma_clip(channel, sigma=3, maxiters=5)
                max_val = np.max(clipped)
                if max_val > 0:
                    normalized[:,:,i] = channel / max_val
            return normalized
        else:
            min_val = np.min(data)
            data = data - min_val
            clipped = sigma_clip(data, sigma=3, maxiters=5)
            max_val = np.max(clipped)
            if max_val > 0:
                data = data / max_val
            return data

    def detect_stars(self, image):
        """Detect stars using DAOStarFinder"""
        try:
            if len(image.shape) == 3:
                if image.shape[0] == 3:
                    image = np.transpose(image, (1, 2, 0))
                data = image[:,:,1]  # Use green channel for color images
            else:
                data = image
            
            data = data - np.min(data)
            
            # Compute background
            bkg_estimator = MedianBackground()
            bkg = Background2D(data, (50, 50), filter_size=(3, 3),
                             bkg_estimator=bkg_estimator)
            
            data_sub = data - bkg.background
            
            # Find stars
            mean, median, std = np.mean(data_sub), np.median(data_sub), np.std(data_sub)
            daofind = DAOStarFinder(fwhm=3.0, threshold=5.*std)
            
            sources = daofind(data_sub)
            
            if sources is None:
                return []
            
            # Extract star information
            stars = []
            for source in sources:
                stars.append((source['xcentroid'], source['ycentroid'], source['flux']))
            
            stars.sort(key=lambda x: x[2], reverse=True)
            return stars
            
        except Exception as e:
            print(f"Error detecting stars: {str(e)}")
            return []

    def analyze_image(self, data):
        """Analyze image and compute statistics"""
        try:
            # If color image, use green channel for analysis
            if len(data.shape) == 3:
                if data.shape[0] == 3:  # If channels first, transpose
                    data = np.transpose(data, (1, 2, 0))
                analyze_data = data[:,:,1]  # Green channel
            else:
                analyze_data = data
            
            # Normalize data for analysis
            norm_data = self.normalize_image(analyze_data)
            
            # Detect stars
            stars = self.detect_stars(norm_data)
            star_count = len(stars)
            
            # Calculate basic statistics
            mean = np.mean(analyze_data)
            std = np.std(analyze_data)
            snr = mean / std if std > 0 else 0
            
            # Calculate average star intensity
            star_intensities = [flux for _, _, flux in stars]
            avg_star_intensity = np.mean(star_intensities) if star_intensities else 0
            
            return {
                "mean": mean,
                "std": std,
                "snr": snr,
                "star_count": star_count,
                "avg_star_intensity": avg_star_intensity
            }
            
        except Exception as e:
            raise Exception(f"Error analyzing image: {str(e)}")

    def compute_image_quality(self, data):
        """Compute various image quality metrics"""
        try:
            stats = self.analyze_image(data)
            
            # Additional quality metrics could be added here
            # For example: FWHM of stars, background uniformity, etc.
            
            return stats
        except Exception as e:
            print(f"Error computing image quality: {str(e)}")
            return None
