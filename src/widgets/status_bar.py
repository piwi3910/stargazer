from PyQt6.QtWidgets import QStatusBar

class StatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QStatusBar { padding: 3px; }")
        self.showMessage("Ready")
