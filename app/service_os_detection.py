from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit
from PyQt5.QtCore import pyqtSlot
from network_scan import NetworkScanner
from PyQt5.QtGui import  QPalette, QColor

class ServiceOSDetection(QWidget):
    def __init__(self, target_ip):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        self.setWindowTitle("Detection OS")
        self.setMinimumSize(1000, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #3498db;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
                transition: background-color 0.3s;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2573a7;
            }
            QTableWidget {
                gridline-color: #d3d3d3;
                background-color: #ffffff;
                border: 1px solid #3498db;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 6px;
                border: 1px solid #2980b9;
                font-weight: bold;
            }
            QLineEdit {
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 5px;
                background-color: #ffffff;
            }
            QListWidget {
                border: 1px solid #3498db;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QLabel {
                color: #2c3e50;
            }
        """)


        palette = self.palette()
       
        palette.setColor(QPalette.Button, QColor(52, 152, 219))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        
        self.setPalette(palette)

        self.scan_button = QPushButton("Détecter Services et OS")
        self.scan_button.clicked.connect(self.start_detection)
        self.layout.addWidget(self.scan_button)

        self.results_display = QTextEdit()
        self.layout.addWidget(self.results_display)
        self.results_display.setEnabled(False)
        self.network_scanner = NetworkScanner()
        self.target_ip = target_ip

    @pyqtSlot()
    def start_detection(self):
        ip = self.target_ip
        ports = self.network_scanner.scan_ports(ip, "1-1024")
        os = self.network_scanner.detect_os(ip)

        self.results_display.clear()
        self.results_display.append(f"IP: {ip}")
        self.results_display.append(f"OS détecté: {os}")
        self.results_display.append("\nPorts ouverts et services:")
        for port in ports:
            self.results_display.append(f"Port {port['port']}: {port['service']} {port['version']}")

