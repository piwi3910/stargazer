from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                           QTabWidget, QCheckBox)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QColor
import os

class SortableTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))
        self.sort_value = value

    def __lt__(self, other):
        if isinstance(other, SortableTableWidgetItem):
            if isinstance(self.sort_value, (int, float)) and isinstance(other.sort_value, (int, float)):
                return self.sort_value < other.sort_value
        return super().__lt__(other)

class CheckBoxWidget(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QCheckBox { margin: 5px; }")

class FITSTableWidget(QTableWidget):
    file_selected = pyqtSignal(str, dict)
    
    # Define all possible FITS header keywords we want to display
    HEADER_COLUMNS = [
        "Select",  # New checkbox column
        "Filename",
        "Type",
        "Size",
        "Exposure",
        "Filter",
        "Score",
        "Stars",
        "FWHM",
        "Sky Background",
        "Hot Pixels",
        "Star Trails",
        "Temperature",
        "Date-Time",
        "Object",
        "Telescope",
        "Focal Length",
        "Aperture",
        "Gain",
        "Offset",
        "ROI",
        "Pixel Size",
        "Bit Depth",
        "Bayered"
    ]
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setColumnCount(len(self.HEADER_COLUMNS))
        self.setHorizontalHeaderLabels(self.HEADER_COLUMNS)
        
        header = self.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.sortIndicatorChanged.connect(self.sortItems)
        
        # Set checkbox column width
        self.setColumnWidth(0, 50)
        
        # Set other columns to resize to content
        for i in range(1, self.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        
        # Optimize table performance
        self.setUpdatesEnabled(False)  # Disable updates during batch operations
        self.verticalHeader().setDefaultSectionSize(20)  # Fixed row height
        self.horizontalHeader().setMinimumSectionSize(50)
        self.setShowGrid(False)  # Hide grid for better performance
        
        self.itemSelectionChanged.connect(self.on_selection_changed)
        self.files = []
        self.headers = {}
        self.analysis_data = {}
        
        # Batch update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.process_updates)
        self.update_timer.setInterval(16)  # ~60fps
        self.pending_updates = []
    
    def get_selected_files(self):
        """Get list of selected files"""
        selected_files = []
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_files.append(self.files[row])
        return selected_files
    
    def select_all_files(self):
        """Select all files in the table"""
        self.setUpdatesEnabled(False)
        try:
            for row in range(self.rowCount()):
                checkbox = self.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
        finally:
            self.setUpdatesEnabled(True)
    
    def select_no_files(self):
        """Deselect all files in the table"""
        self.setUpdatesEnabled(False)
        try:
            for row in range(self.rowCount()):
                checkbox = self.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(False)
        finally:
            self.setUpdatesEnabled(True)
    
    def select_by_score(self, min_score):
        """Select files with score >= min_score"""
        selected_count = 0
        self.setUpdatesEnabled(False)
        try:
            for row in range(self.rowCount()):
                filepath = self.files[row]
                score = self.get_file_score(filepath)
                checkbox = self.cellWidget(row, 0)
                if checkbox and score is not None and score >= min_score:
                    checkbox.setChecked(True)
                    selected_count += 1
                else:
                    checkbox.setChecked(False)
        finally:
            self.setUpdatesEnabled(True)
        return selected_count
    
    def get_file_score(self, filepath):
        """Get the score for a specific file"""
        if filepath in self.analysis_data:
            score = self.analysis_data[filepath].get("Score")
            if score is not None:
                try:
                    return float(score)
                except (ValueError, TypeError):
                    pass
        return None
    
    def set_files(self, new_files):
        """Update the table with a new list of files"""
        self.setUpdatesEnabled(False)
        try:
            # Clear current rows but keep the data
            self.setRowCount(0)
            
            # Keep only the files in the new list
            old_files = self.files
            self.files = []
            
            # Add rows for each file in the new list
            for filepath in new_files:
                if filepath in old_files:
                    # Re-add the file if it was in the old list
                    row = self.rowCount()
                    self.insertRow(row)
                    self.files.append(filepath)
                    
                    # Add checkbox
                    checkbox = CheckBoxWidget(self)
                    self.setCellWidget(row, 0, checkbox)
                    
                    # Restore the file's data
                    header = self.headers.get(filepath, {})
                    analysis = self.analysis_data.get(filepath, {})
                    
                    # Map common FITS keywords to our columns
                    info = {
                        "Filename": os.path.basename(filepath),
                        "Type": header.get('IMAGETYP', 'Light'),
                        "Size": f"{header.get('NAXIS1', '-')}x{header.get('NAXIS2', '-')}",
                        "Exposure": f"{header.get('EXPTIME', '-')}s",
                        "Filter": header.get('FILTER', '-'),
                        "Score": analysis.get('Score', '-'),
                        "Stars": analysis.get('Stars', '-'),
                        "FWHM": analysis.get('FWHM', '-'),
                        "Sky Background": analysis.get('Sky Background', '-'),
                        "Hot Pixels": analysis.get('Hot Pixels', '-'),
                        "Star Trails": analysis.get('Star Trails', '-'),
                        "Temperature": f"{header.get('CCD-TEMP', '-')}°C",
                        "Date-Time": header.get('DATE-OBS', '-'),
                        "Object": header.get('OBJECT', '-'),
                        "Telescope": header.get('TELESCOP', '-'),
                        "Focal Length": f"{header.get('FOCALLEN', '-')}mm",
                        "Aperture": f"{header.get('APERTURE', '-')}mm",
                        "Gain": header.get('GAIN', '-'),
                        "Offset": header.get('OFFSET', '-'),
                        "ROI": f"{header.get('XORGSUBF', '0')},{header.get('YORGSUBF', '0')}",
                        "Pixel Size": f"{header.get('XPIXSZ', '-')}µm",
                        "Bit Depth": header.get('BITPIX', '-'),
                        "Bayered": header.get('BAYERPAT', 'No')
                    }
                    
                    # Fill in all columns
                    for col, header_key in enumerate(self.HEADER_COLUMNS[1:], 1):  # Skip checkbox column
                        value = info.get(header_key, '-')
                        if isinstance(value, (int, float)):
                            item = SortableTableWidgetItem(value)
                        else:
                            item = QTableWidgetItem(str(value))
                        self.setItem(row, col, item)
            
            # Clean up data for removed files
            removed_files = set(old_files) - set(new_files)
            for filepath in removed_files:
                if filepath in self.headers:
                    del self.headers[filepath]
                if filepath in self.analysis_data:
                    del self.analysis_data[filepath]
                
        finally:
            self.setUpdatesEnabled(True)
    
    def on_selection_changed(self):
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if 0 <= row < len(self.files):
                filepath = self.files[row]
                self.main_window.preview_fits_file(filepath)
                if filepath in self.headers:
                    self.file_selected.emit(filepath, self.headers[filepath])

    def update_analysis_data(self, filepath, analysis):
        """Update table with analysis results"""
        try:
            if not filepath in self.files:
                return
                
            self.analysis_data[filepath] = analysis
            row = self.files.index(filepath)
            
            # Update columns with analysis data
            col_map = {
                "Score": analysis.get("Score", "-"),
                "Stars": analysis.get("Stars", "-"),
                "FWHM": analysis.get("FWHM", "-"),
                "Sky Background": analysis.get("Sky Background", "-"),
                "Hot Pixels": analysis.get("Hot Pixels", "-"),
                "Star Trails": analysis.get("Star Trails", "-")
            }
            
            # Temporarily disable sorting to prevent crashes during update
            was_sorting_enabled = self.isSortingEnabled()
            self.setSortingEnabled(False)
            
            try:
                for col_name, value in col_map.items():
                    col = self.HEADER_COLUMNS.index(col_name)
                    if isinstance(value, (int, float)):
                        item = SortableTableWidgetItem(value)
                    else:
                        item = QTableWidgetItem(str(value))
                    self.setItem(row, col, item)
            finally:
                # Re-enable sorting if it was enabled
                self.setSortingEnabled(was_sorting_enabled)
                
        except Exception as e:
            print(f"Error updating analysis data: {str(e)}")

    def add_file(self, filepath, header, data):
        """Queue a file to be added to the table"""
        self.pending_updates.append((filepath, header, data))
        if not self.update_timer.isActive():
            self.update_timer.start()
    
    def process_updates(self):
        """Process pending updates"""
        if not self.pending_updates:
            self.update_timer.stop()
            return
        
        # Process all pending updates at once
        updates = self.pending_updates
        self.pending_updates = []
        
        self.setUpdatesEnabled(False)
        try:
            for filepath, header, data in updates:
                # Add row
                row = self.rowCount()
                self.insertRow(row)
                
                # Add checkbox
                checkbox = CheckBoxWidget(self)
                self.setCellWidget(row, 0, checkbox)
                
                # Map common FITS keywords to our columns
                info = {
                    "Filename": os.path.basename(filepath),
                    "Type": header.get('IMAGETYP', 'Light'),
                    "Size": f"{data['shape'][1]}x{data['shape'][0]}",
                    "Exposure": f"{header.get('EXPTIME', '-')}s",
                    "Filter": header.get('FILTER', '-'),
                    "Score": "-",
                    "Stars": "-",
                    "FWHM": "-",
                    "Sky Background": "-",
                    "Hot Pixels": "-",
                    "Star Trails": "-",
                    "Temperature": f"{header.get('CCD-TEMP', '-')}°C",
                    "Date-Time": header.get('DATE-OBS', '-'),
                    "Object": header.get('OBJECT', '-'),
                    "Telescope": header.get('TELESCOP', '-'),
                    "Focal Length": f"{header.get('FOCALLEN', '-')}mm",
                    "Aperture": f"{header.get('APERTURE', '-')}mm",
                    "Gain": header.get('GAIN', '-'),
                    "Offset": header.get('OFFSET', '-'),
                    "ROI": f"{header.get('XORGSUBF', '0')},{header.get('YORGSUBF', '0')}",
                    "Pixel Size": f"{header.get('XPIXSZ', '-')}µm",
                    "Bit Depth": data['dtype'],
                    "Bayered": header.get('BAYERPAT', 'No')
                }
                
                # Fill in all columns
                for col, header_key in enumerate(self.HEADER_COLUMNS[1:], 1):  # Skip checkbox column
                    value = info.get(header_key, '-')
                    if isinstance(value, (int, float)):
                        item = SortableTableWidgetItem(value)
                    else:
                        item = QTableWidgetItem(str(value))
                    self.setItem(row, col, item)
                
                self.files.append(filepath)
                self.headers[filepath] = header
        finally:
            self.setUpdatesEnabled(True)
            
        if not self.pending_updates:
            self.update_timer.stop()

    def clear(self):
        """Clear all data from the table"""
        self.setUpdatesEnabled(False)
        try:
            self.setRowCount(0)
            self.files.clear()
            self.headers.clear()
            self.analysis_data.clear()
            self.pending_updates.clear()
        finally:
            self.setUpdatesEnabled(True)

class FileListTabs(QTabWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # Create tables for each type
        self.light_table = FITSTableWidget(main_window)
        self.dark_table = FITSTableWidget(main_window)
        self.flat_table = FITSTableWidget(main_window)
        self.bias_table = FITSTableWidget(main_window)
        
        # Add tabs
        self.addTab(self.light_table, "Light Frames")
        self.addTab(self.dark_table, "Dark Frames")
        self.addTab(self.flat_table, "Flat Frames")
        self.addTab(self.bias_table, "Bias/Offset Frames")
        
        # Set tab tooltips
        self.setTabToolTip(0, "Light frames - Main imaging frames")
        self.setTabToolTip(1, "Dark frames - For dark current subtraction")
        self.setTabToolTip(2, "Flat frames - For vignetting correction")
        self.setTabToolTip(3, "Bias/Offset frames - For bias subtraction")
    
    def get_current_table(self):
        return self.currentWidget()
    
    def clear_all_tables(self):
        self.light_table.clear()
        self.dark_table.clear()
        self.flat_table.clear()
        self.bias_table.clear()
