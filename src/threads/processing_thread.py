from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np

class ProcessingThread(QThread):
    progress = pyqtSignal(str, str)  # message, type
    progress_update = pyqtSignal(int, int)  # current, total
    preview_update = pyqtSignal(object, object)  # current_stack, header
    finished = pyqtSignal(bool, object, object)  # success, stacked_data, header
    
    def __init__(self, image_processor, files):
        super().__init__()
        self.image_processor = image_processor
        self.files = files
        self._is_cancelled = False
    
    def run(self):
        """Process images in a separate thread"""
        try:
            total_files = len(self.files)
            self.progress.emit(f"Starting to stack {total_files} files...", "INFO")
            self.progress_update.emit(0, total_files)
            
            # Process images one at a time
            success, stacked_data, header = self.image_processor.process_images(
                self.files,
                progress_callback=lambda msg, type: self.progress.emit(msg, type),
                update_callback=lambda current, total: self.progress_update.emit(current, total),
                preview_callback=lambda data, hdr: self.preview_update.emit(data, hdr)
            )
            
            if success:
                self.progress.emit(f"Successfully stacked {total_files} files", "SUCCESS")
                self.progress_update.emit(total_files, total_files)
                self.finished.emit(True, stacked_data, header)
            else:
                self.progress.emit("Failed to stack images", "ERROR")
                self.finished.emit(False, None, None)
                
        except Exception as e:
            self.progress.emit(f"Error during stacking: {str(e)}", "ERROR")
            self.finished.emit(False, None, None)
    
    def cancel(self):
        """Cancel the processing"""
        self._is_cancelled = True
