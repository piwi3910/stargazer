from PyQt6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QGroupBox
from PyQt6.QtCore import Qt

class MenuPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setMinimumWidth(200)
        self.setMaximumWidth(250)
        
        layout = QVBoxLayout(self)
        
        # Registration and Stacking section
        reg_group = QGroupBox("Registration and Stacking")
        reg_layout = QVBoxLayout(reg_group)
        
        # Load buttons group
        load_group = QGroupBox("Open Files")
        load_layout = QVBoxLayout(load_group)
        
        # Create load buttons for different types
        self.load_light_button = QPushButton("Light frames...")
        self.load_dark_button = QPushButton("Dark frames...")
        self.load_flat_button = QPushButton("Flat frames...")
        self.load_bias_button = QPushButton("Bias/Offset frames...")
        
        # Style buttons
        for btn in [self.load_light_button, self.load_dark_button, 
                   self.load_flat_button, self.load_bias_button]:
            btn.setStyleSheet("text-align: left; padding: 5px;")
        
        load_layout.addWidget(self.load_light_button)
        load_layout.addWidget(self.load_dark_button)
        load_layout.addWidget(self.load_flat_button)
        load_layout.addWidget(self.load_bias_button)
        
        reg_layout.addWidget(load_group)
        
        # List management group
        list_group = QGroupBox("List Management")
        list_layout = QVBoxLayout(list_group)
        
        self.select_all_button = QPushButton("Select All")
        self.select_none_button = QPushButton("Select None")
        self.select_score_button = QPushButton("Select min Score...")
        self.clear_list_button = QPushButton("Clear List")
        
        # Style list management buttons
        for btn in [self.select_all_button, self.select_none_button,
                   self.select_score_button, self.clear_list_button]:
            btn.setStyleSheet("text-align: left; padding: 5px;")
            btn.setEnabled(False)
        
        list_layout.addWidget(self.select_all_button)
        list_layout.addWidget(self.select_none_button)
        list_layout.addWidget(self.select_score_button)
        list_layout.addWidget(self.clear_list_button)
        
        reg_layout.addWidget(list_group)
        
        # Process buttons
        self.preprocess_button = QPushButton("Preprocess...")
        self.preprocess_button.setStyleSheet("text-align: left; padding: 5px;")
        self.preprocess_button.setEnabled(False)
        reg_layout.addWidget(self.preprocess_button)
        
        self.process_button = QPushButton("Stack checked pictures...")
        self.process_button.setStyleSheet("text-align: left; padding: 5px;")
        self.process_button.setEnabled(False)
        reg_layout.addWidget(self.process_button)
        
        layout.addWidget(reg_group)
        # Add stretch to push everything to the top
        layout.addStretch()
