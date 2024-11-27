from PyQt6.QtCore import QThread, pyqtSignal
from astropy.io import fits
from concurrent.futures import ThreadPoolExecutor, as_completed

class LoadingThread(QThread):
    progress = pyqtSignal(str, str)  # message, type
    file_loaded = pyqtSignal(str, dict, dict)  # filepath, header, data
    finished = pyqtSignal()
    error = pyqtSignal(str, str)  # filepath, error message
    
    def __init__(self, files, max_workers=4):
        super().__init__()
        self.files = files
        self.max_workers = max_workers
    
    def load_single_file(self, filepath):
        """Load a single FITS file"""
        try:
            self.progress.emit(f"Loading {filepath}", "INFO")
            
            with fits.open(filepath) as hdul:
                header = dict(hdul[0].header.items())
                data = {
                    "shape": hdul[0].data.shape,
                    "dtype": str(hdul[0].data.dtype)
                }
            
            # Emit result immediately
            self.file_loaded.emit(filepath, header, data)
            self.progress.emit(f"Successfully loaded {filepath}", "SUCCESS")
            
            return True
            
        except Exception as e:
            self.error.emit(filepath, str(e))
            self.progress.emit(f"Failed to load {filepath}: {str(e)}", "ERROR")
            return False
    
    def run(self):
        total = len(self.files)
        self.progress.emit(f"Starting to load {total} files...", "INFO")
        
        try:
            # Create thread pool for parallel loading
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all files to the thread pool
                future_to_file = {
                    executor.submit(self.load_single_file, filepath): filepath 
                    for filepath in self.files
                }
                
                # Process completed files as they finish
                for future in as_completed(future_to_file):
                    filepath = future_to_file[future]
                    try:
                        success = future.result()
                    except Exception as e:
                        self.error.emit(filepath, str(e))
                        self.progress.emit(f"Failed to load {filepath}: {str(e)}", "ERROR")
            
            self.progress.emit("File loading complete", "SUCCESS")
            
        except Exception as e:
            self.progress.emit(f"Critical error during loading: {str(e)}", "ERROR")
        
        finally:
            self.finished.emit()
