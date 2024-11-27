import sys
import os
import multiprocessing
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QFileDialog, QMessageBox, QProgressBar,
                           QPushButton, QDialog, QLabel, QSpinBox, QDialogButtonBox)
from PyQt6.QtCore import Qt

from widgets import (MenuPanel, PreviewWidget, FileListTabs, StatusBar)
from threads import LoadingThread, ProcessingThread, AnalysisThread
from preprocessing_dialog import PreprocessingDialog
from preview_dialog import PreviewDialog
from image_processor import ImageProcessor
from log_window import LogWindow

class ScoreDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Score Threshold")
        layout = QVBoxLayout(self)
        
        # Add score input
        score_layout = QHBoxLayout()
        score_layout.addWidget(QLabel("Minimum Score:"))
        self.score_spin = QSpinBox()
        self.score_spin.setRange(0, 100)
        self.score_spin.setValue(50)
        score_layout.addWidget(self.score_spin)
        layout.addLayout(score_layout)
        
        # Add buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stargazer - Astrophotography Processing")
        self.setMinimumSize(1400, 800)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Create left side layout (menu + preview + table)
        left_layout = QVBoxLayout()
        
        # Create horizontal layout for menu and preview
        top_layout = QHBoxLayout()
        
        # Create menu panel
        self.menu_panel = MenuPanel()
        self.menu_panel.load_light_button.clicked.connect(lambda: self.load_images("Light"))
        self.menu_panel.load_dark_button.clicked.connect(lambda: self.load_images("Dark"))
        self.menu_panel.load_flat_button.clicked.connect(lambda: self.load_images("Flat"))
        self.menu_panel.load_bias_button.clicked.connect(lambda: self.load_images("Bias"))
        self.menu_panel.preprocess_button.clicked.connect(self.preprocess_images)
        self.menu_panel.clear_list_button.clicked.connect(self.clear_list)
        self.menu_panel.select_score_button.clicked.connect(self.select_by_score)
        self.menu_panel.select_all_button.clicked.connect(self.select_all)
        self.menu_panel.select_none_button.clicked.connect(self.select_none)
        self.menu_panel.process_button.clicked.connect(self.process_images)
        top_layout.addWidget(self.menu_panel)
        
        # Create preview widget
        self.preview = PreviewWidget()
        top_layout.addWidget(self.preview)
        
        # Add top layout to left layout
        left_layout.addLayout(top_layout)
        
        # Create progress layout
        progress_layout = QHBoxLayout()
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar, stretch=1)
        
        # Add cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_loading)
        self.cancel_button.setVisible(False)
        progress_layout.addWidget(self.cancel_button)
        
        left_layout.addLayout(progress_layout)
        
        # Add tabbed file list
        self.file_tabs = FileListTabs(self)
        left_layout.addWidget(self.file_tabs)
        
        # Set left layout proportions
        left_layout.setStretch(0, 2)  # Top section (menu + preview)
        left_layout.setStretch(1, 0)  # Progress section
        left_layout.setStretch(2, 1)  # Table section
        
        # Add left layout to main layout
        main_layout.addLayout(left_layout, stretch=2)
        
        # Create and add log window
        self.log_window = LogWindow()
        main_layout.addWidget(self.log_window, stretch=1)
        
        # Create status bar
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)
        
        # Initialize image processor
        self.image_processor = ImageProcessor()
        self.processing_thread = None
        self.analysis_threads = []
        self.loading_thread = None
        
        # Track preprocessing progress
        self.preprocessing_total = 0
        self.preprocessing_completed = 0
        self.preprocessing_queue = []
    
    def select_all(self):
        """Select all files in the current table"""
        current_table = self.file_tabs.get_current_table()
        current_table.select_all_files()
        self.log_window.log("Selected all files")
    
    def select_none(self):
        """Deselect all files in the current table"""
        current_table = self.file_tabs.get_current_table()
        current_table.select_no_files()
        self.log_window.log("Deselected all files")
    
    def clear_list(self):
        """Clear the current file list"""
        current_table = self.file_tabs.get_current_table()
        if current_table.files:
            reply = QMessageBox.question(
                self,
                "Clear List",
                "Are you sure you want to clear the current list?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                current_table.clear()
                self.menu_panel.preprocess_button.setEnabled(False)
                self.menu_panel.clear_list_button.setEnabled(False)
                self.menu_panel.select_score_button.setEnabled(False)
                self.menu_panel.select_all_button.setEnabled(False)
                self.menu_panel.select_none_button.setEnabled(False)
                self.menu_panel.process_button.setEnabled(False)
                self.log_window.log("List cleared")
    
    def select_by_score(self):
        """Select files based on score threshold"""
        dialog = ScoreDialog(self)
        if dialog.exec():
            min_score = dialog.score_spin.value()
            current_table = self.file_tabs.get_current_table()
            selected_count = current_table.select_by_score(min_score)
            self.log_window.log(f"Selected {selected_count} files with score >= {min_score}")
    
    def preview_fits_file(self, filepath):
        """Display FITS file in preview window"""
        try:
            self.preview.display_fits(filepath)
            self.log_window.log(f"Previewing {os.path.basename(filepath)}")
        except Exception as e:
            self.log_window.log(f"Preview failed: {str(e)}", "ERROR")
    
    def update_progress(self, current, total):
        """Update progress bar"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        
        if hasattr(self, 'preprocessing_total') and self.preprocessing_total > 0:
            self.progress_bar.setFormat(f"Preprocessing: {current}/{total} files (%p%)")
            self.status_bar.showMessage(f"Preprocessing files: {current}/{total}")
        else:
            self.progress_bar.setFormat(f"Loading: {current}/{total} files (%p%)")
            self.status_bar.showMessage(f"Loading files: {current}/{total}")
    
    def cancel_loading(self):
        """Cancel the loading process"""
        if self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.cancel()
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText("Cancelling...")
            self.status_bar.showMessage("Cancelling file loading...")
    
    def handle_file_loaded(self, filepath, header, data):
        """Handle a loaded file"""
        current_table = self.file_tabs.get_current_table()
        current_table.add_file(filepath, header, data)
    
    def load_images(self, frame_type):
        """Handle image loading"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            f"Select {frame_type} Frames",
            "",
            "FITS Files (*.fits *.fit *.fts);;All Files (*.*)"
        )
        
        if files:
            # Select appropriate table based on frame type
            if frame_type == "Light":
                table = self.file_tabs.light_table
                self.file_tabs.setCurrentWidget(table)
            elif frame_type == "Dark":
                table = self.file_tabs.dark_table
                self.file_tabs.setCurrentWidget(table)
            elif frame_type == "Flat":
                table = self.file_tabs.flat_table
                self.file_tabs.setCurrentWidget(table)
            else:  # Bias
                table = self.file_tabs.bias_table
                self.file_tabs.setCurrentWidget(table)
            
            self.log_window.log(f"Starting to load {len(files)} {frame_type} frames...")
            self.status_bar.showMessage(f"Loading {len(files)} {frame_type} frames...")
            
            # Show progress controls
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.cancel_button.setVisible(True)
            self.cancel_button.setEnabled(True)
            self.cancel_button.setText("Cancel")
            
            # Disable buttons during loading
            self.menu_panel.load_light_button.setEnabled(False)
            self.menu_panel.load_dark_button.setEnabled(False)
            self.menu_panel.load_flat_button.setEnabled(False)
            self.menu_panel.load_bias_button.setEnabled(False)
            
            # Create and start loading thread
            self.loading_thread = LoadingThread(files)
            
            # Connect signals
            self.loading_thread.progress.connect(self.log_window.log)
            self.loading_thread.progress_update.connect(self.update_progress)
            self.loading_thread.file_loaded.connect(self.handle_file_loaded)
            self.loading_thread.error.connect(
                lambda filepath, error: self.log_window.log(f"Error loading {filepath}: {error}", "ERROR")
            )
            self.loading_thread.finished.connect(self.loading_finished)
            
            # Start loading
            self.loading_thread.start()
    
    def loading_finished(self):
        """Handle completion of file loading"""
        try:
            # Hide progress controls
            self.progress_bar.setVisible(False)
            self.cancel_button.setVisible(False)
            
            # Always re-enable load buttons
            self.menu_panel.load_light_button.setEnabled(True)
            self.menu_panel.load_dark_button.setEnabled(True)
            self.menu_panel.load_flat_button.setEnabled(True)
            self.menu_panel.load_bias_button.setEnabled(True)
            
            # Get current table and check if it has files
            current_table = self.file_tabs.get_current_table()
            if current_table is None:
                return
                
            # Check if files were loaded
            file_count = len(current_table.files) if hasattr(current_table, 'files') else 0
            has_files = file_count > 0
            
            # Enable or disable processing buttons based on file presence
            for button in [
                self.menu_panel.preprocess_button,
                self.menu_panel.clear_list_button,
                self.menu_panel.select_score_button,
                self.menu_panel.select_all_button,
                self.menu_panel.select_none_button,
                self.menu_panel.process_button
            ]:
                button.setEnabled(has_files)
            
            if has_files:
                self.log_window.log(f"File loading complete - {file_count} files loaded", "SUCCESS")
            
            self.status_bar.showMessage("Ready")
            
        except Exception as e:
            self.log_window.log(f"Error in loading_finished: {str(e)}", "ERROR")
            # Ensure buttons are enabled even if there's an error
            self.menu_panel.load_light_button.setEnabled(True)
            self.menu_panel.load_dark_button.setEnabled(True)
            self.menu_panel.load_flat_button.setEnabled(True)
            self.menu_panel.load_bias_button.setEnabled(True)
    
    def handle_analysis_progress(self, current, total):
        """Handle preprocessing progress updates"""
        self.preprocessing_completed += 1
        self.update_progress(self.preprocessing_completed, self.preprocessing_total)
        
        # Start next analysis if there are files in queue
        if self.preprocessing_queue:
            filepath = self.preprocessing_queue.pop(0)
            self.start_analysis_thread(filepath)
    
    def handle_analysis_finished(self, result, filepath):
        """Handle completion of a single file analysis"""
        current_table = self.file_tabs.get_current_table()
        current_table.update_analysis_data(filepath, result)
        
        if self.preprocessing_completed == self.preprocessing_total:
            self.progress_bar.setVisible(False)
            self.status_bar.showMessage("Preprocessing complete")
            self.log_window.log("Preprocessing complete", "SUCCESS")
    
    def start_analysis_thread(self, filepath):
        """Start a new analysis thread"""
        thread = AnalysisThread(filepath, self.preprocessing_total, self.preprocessing_completed, self.image_processor)
        thread.progress.connect(self.log_window.log)
        thread.progress_update.connect(self.handle_analysis_progress)
        thread.finished.connect(lambda result: self.handle_analysis_finished(result, filepath))
        self.analysis_threads.append(thread)
        thread.start()
    
    def preprocess_images(self):
        """Handle image preprocessing"""
        dialog = PreprocessingDialog(self)
        if dialog.exec():
            current_table = self.file_tabs.get_current_table()
            total_files = len(current_table.files)
            
            if total_files == 0:
                return
            
            self.log_window.log(f"Starting preprocessing of {total_files} files...")
            self.status_bar.showMessage("Preprocessing images...")
            
            # Show progress bar
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.preprocessing_total = total_files
            self.preprocessing_completed = 0
            
            # Clear any existing analysis threads
            self.analysis_threads.clear()
            
            # Initialize preprocessing queue
            self.preprocessing_queue = current_table.files.copy()
            
            # Start initial batch of analysis threads
            max_concurrent = max(1, multiprocessing.cpu_count())
            initial_batch = self.preprocessing_queue[:max_concurrent]
            self.preprocessing_queue = self.preprocessing_queue[max_concurrent:]
            
            for filepath in initial_batch:
                self.start_analysis_thread(filepath)
    
    def process_images(self):
        """Handle image processing"""
        current_table = self.file_tabs.get_current_table()
        selected_files = current_table.get_selected_files()
        
        if not selected_files:
            self.log_window.log("No images selected", "ERROR")
            QMessageBox.warning(self, "Error", "Please select images to process")
            return
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"Stacking: 0/{len(selected_files)} files (%p%)")
        
        # Disable processing button
        self.menu_panel.process_button.setEnabled(False)
        self.status_bar.showMessage("Stacking images...")
        
        # Create and start processing thread
        self.processing_thread = ProcessingThread(self.image_processor, selected_files)
        
        # Connect signals
        self.processing_thread.progress.connect(lambda msg, type: self.log_window.log(msg, type))
        self.processing_thread.progress_update.connect(self.update_stacking_progress)
        self.processing_thread.preview_update.connect(self.preview.display_array)
        self.processing_thread.finished.connect(self.processing_finished)
        
        # Start processing
        self.processing_thread.start()
    
    def update_stacking_progress(self, current, total):
        """Update stacking progress"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"Stacking: {current}/{total} files (%p%)")
        self.status_bar.showMessage(f"Stacking files: {current}/{total}")
    
    def processing_finished(self, success, stacked_data, header):
        """Handle completion of image processing"""
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        # Re-enable processing button
        self.menu_panel.process_button.setEnabled(True)
        
        if success and stacked_data is not None:
            # Show preview dialog
            preview = PreviewDialog(stacked_data, header, self)
            if preview.exec() == QDialog.DialogCode.Accepted:
                self.log_window.log("Stacked image saved", "SUCCESS")
                self.status_bar.showMessage("Processing complete", 5000)
            else:
                self.log_window.log("Stacked image discarded", "WARNING")
                self.status_bar.showMessage("Processing cancelled", 5000)
        else:
            self.log_window.log("Processing failed", "ERROR")
            self.status_bar.showMessage("Processing failed", 5000)
            QMessageBox.warning(self, "Error", "Failed to process images")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    app.exec()  # Remove sys.exit() to avoid numpy deprecation warning

if __name__ == "__main__":
    main()
