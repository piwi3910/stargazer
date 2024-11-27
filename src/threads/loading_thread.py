from PyQt6.QtCore import QThread, pyqtSignal
from astropy.io import fits
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import multiprocessing
import traceback
import gc
import psutil
from queue import Queue
from threading import Lock, Event
import hashlib
import tempfile
import json
import mmap

class LoadingThread(QThread):
    progress = pyqtSignal(str, str)  # message, type
    progress_update = pyqtSignal(int, int)  # current, total
    file_loaded = pyqtSignal(str, dict, dict)  # filepath, header, data
    finished = pyqtSignal()
    error = pyqtSignal(str, str)  # filepath, error message
    
    def __init__(self, files):
        super().__init__()
        self.files = files
        self.max_workers = max(1, multiprocessing.cpu_count() * 2)  # Double the workers
        self.cancel_event = Event()
        self.cache_dir = os.path.join(tempfile.gettempdir(), 'stargazer_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def read_fits_file(self, filepath):
        """Read FITS file with fallback methods"""
        try:
            # First try: Direct read
            with fits.open(filepath) as hdul:
                header = dict(hdul[0].header.items())
                data = {
                    "shape": hdul[0].data.shape if hdul[0].data is not None else None,
                    "dtype": str(hdul[0].data.dtype) if hdul[0].data is not None else None
                }
                return header, data
        except Exception as e1:
            try:
                # Second try: Memory mapping with readonly
                with fits.open(filepath, memmap=True, mode='readonly') as hdul:
                    header = dict(hdul[0].header.items())
                    data = {
                        "shape": hdul[0].data.shape if hdul[0].data is not None else None,
                        "dtype": str(hdul[0].data.dtype) if hdul[0].data is not None else None
                    }
                    return header, data
            except Exception as e2:
                try:
                    # Third try: Copy to temp file first
                    temp_file = os.path.join(self.cache_dir, f"temp_{os.path.basename(filepath)}")
                    with open(filepath, 'rb') as src, open(temp_file, 'wb') as dst:
                        dst.write(src.read())
                    
                    with fits.open(temp_file) as hdul:
                        header = dict(hdul[0].header.items())
                        data = {
                            "shape": hdul[0].data.shape if hdul[0].data is not None else None,
                            "dtype": str(hdul[0].data.dtype) if hdul[0].data is not None else None
                        }
                    
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                        
                    return header, data
                except Exception as e3:
                    raise Exception(f"Failed to read FITS file after all attempts: {str(e1)}, {str(e2)}, {str(e3)}")
    
    def load_single_file(self, filepath):
        """Load a single FITS file"""
        try:
            if self.cancel_event.is_set():
                return False
            
            # Check cache first
            cache_path = os.path.join(self.cache_dir, hashlib.md5(filepath.encode()).hexdigest() + '.json')
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r') as f:
                        cached_data = json.load(f)
                        header = cached_data['header']
                        data = cached_data['data']
                except:
                    header, data = self.read_fits_file(filepath)
            else:
                header, data = self.read_fits_file(filepath)
                
                # Cache the results
                try:
                    with open(cache_path, 'w') as f:
                        json.dump({'header': header, 'data': data}, f)
                except:
                    pass  # Ignore cache write errors
            
            # Emit result immediately
            self.file_loaded.emit(filepath, header, data)
            return True
            
        except Exception as e:
            self.error.emit(filepath, str(e))
            self.progress.emit(f"Error loading {os.path.basename(filepath)}: {str(e)}", "ERROR")
            return False
    
    def run(self):
        total = len(self.files)
        self.progress.emit(f"Starting to load {total} files using {self.max_workers} CPU cores...", "INFO")
        self.progress_update.emit(0, total)
        
        try:
            completed = 0
            failed = 0
            
            # Create thread pool for parallel loading
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all files to the thread pool
                future_to_file = {
                    executor.submit(self.load_single_file, filepath): filepath 
                    for filepath in self.files
                }
                
                # Process completed files as they finish
                for future in as_completed(future_to_file):
                    if self.cancel_event.is_set():
                        break
                        
                    filepath = future_to_file[future]
                    try:
                        success = future.result()
                        if success:
                            completed += 1
                        else:
                            failed += 1
                        self.progress_update.emit(completed + failed, total)
                        
                    except Exception as e:
                        failed += 1
                        self.error.emit(filepath, str(e))
                        self.progress.emit(f"Failed to load {os.path.basename(filepath)}: {str(e)}", "ERROR")
            
            if self.cancel_event.is_set():
                self.progress.emit("File loading cancelled", "WARNING")
            else:
                self.progress.emit(
                    f"File loading complete. Successfully loaded {completed}/{total} files"
                    + (f" ({failed} failed)" if failed > 0 else ""),
                    "SUCCESS" if failed == 0 else "WARNING"
                )
            
            # Wait for UI to process all files
            self.msleep(500)
            
        except Exception as e:
            self.progress.emit(f"Critical error during loading: {str(e)}", "ERROR")
            self.progress.emit(traceback.format_exc(), "ERROR")
        
        finally:
            # Ensure all files are processed before finishing
            self.msleep(500)
            self.finished.emit()
