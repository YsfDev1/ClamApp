#!/usr/bin/env python3
import sys
import os

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from gui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication
from backend.logging_setup import setup_logging

def main():
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("ClamApp")
    
    window = MainWindow()
    window.setMinimumSize(400, 300) # Ensure it doesn't open too small
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
