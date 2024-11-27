from PyQt6.QtCore import QThread, pyqtSignal
from astropy.io import fits
import traceback
from image_processor import ImageProcessor

class AnalysisThread(QThread):
    progress = pyqtSignal(str, str)  # message, type
    progress_update = pyqtSignal(int, int)  # Current, total
    finished = pyqtSignal(dict)  # Analysis results
    
    def __init__(self, filepath, total, current, image_processor=None):
        super().__init__()
        self.filepath = filepath
        self.total = total
        self.current = current
        self._is_cancelled = False
        # Use provided image processor or create new one
        self.image_processor = image_processor if image_processor else ImageProcessor()
    
    def run(self):
        """Analyze a FITS file in a separate thread"""
        try:
            self.progress.emit(f"Analyzing {self.filepath}", "INFO")
            
            # Load FITS file
            with fits.open(self.filepath) as hdul:
                data = hdul[0].data
                header = hdul[0].header
                
                # Convert Bayer pattern to RGB if needed
                if self.image_processor.is_color_image(header, data) and 'BAYERPAT' in header:
                    data = self.image_processor.debayer_image(data, header)
                
                # Analyze image
                result = self.image_processor.analyze_image(data)
                
                # Add score based on star count and SNR
                score = min(100, max(0, int(
                    50 +  # Base score
                    min(25, result["star_count"] / 2) +  # Up to 25 points for stars
                    min(25, result["snr"])  # Up to 25 points for SNR
                )))
                result["Score"] = score
                
                # Format values for display
                result["Stars"] = str(result["star_count"])
                result["FWHM"] = f"{result.get('fwhm', '-')}"
                result["Sky Background"] = f"{result.get('sky_background', '-')}"
                result["Hot Pixels"] = "No"
                result["Star Trails"] = "No"
                
                self.progress_update.emit(self.current + 1, self.total)
                self.finished.emit(result)
                
        except Exception as e:
            self.progress.emit(f"Error analyzing {self.filepath}: {str(e)}", "ERROR")
            traceback.print_exc()
            # Return empty dict with required keys
            self.finished.emit({
                "Score": "-",
                "Stars": "-",
                "FWHM": "-",
                "Sky Background": "-",
                "Hot Pixels": "-",
                "Star Trails": "-"
            })
    
    def cancel(self):
        """Cancel the analysis"""
        self._is_cancelled = True
