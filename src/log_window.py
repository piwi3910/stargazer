from PyQt6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QTextCursor
from datetime import datetime

class LogWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Log")
        title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Courier', 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #333333;
            }
        """)
        layout.addWidget(self.log_text)
    
    @pyqtSlot(str)
    def log(self, message, message_type="INFO"):
        """Add a message to the log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding based on message type
        color = {
            "INFO": "#FFFFFF",    # White
            "SUCCESS": "#00FF00", # Green
            "WARNING": "#FFA500", # Orange
            "ERROR": "#FF0000"    # Red
        }.get(message_type, "#FFFFFF")
        
        # Format message with HTML
        formatted_message = f'<span style="color: #888888">[{timestamp}]</span> <span style="color: {color}">{message}</span><br>'
        
        # Add message to log
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        self.log_text.insertHtml(formatted_message)
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear(self):
        """Clear the log window"""
        self.log_text.clear()
