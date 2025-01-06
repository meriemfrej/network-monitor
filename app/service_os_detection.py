from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                            QPushButton, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QLineEdit)
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtCore import pyqtSlot, Qt
from network_scan import NetworkScanner

class ServiceOSDetection(QWidget):
    def __init__(self, target_ip):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.setWindowTitle("Détection des Anomalies")
        self.setMinimumSize(1000, 800)
        
        # Set the application style
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

        # Set a color palette
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.WindowText, QColor(44, 62, 80))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ToolTipText, QColor(44, 62, 80))
        palette.setColor(QPalette.Text, QColor(44, 62, 80))
        palette.setColor(QPalette.Button, QColor(52, 152, 219))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Highlight, QColor(52, 152, 219))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)

        # Set default font
        font = QFont("Segoe UI", 10)
        QApplication.setFont(font)

        self.port_range_input = QLineEdit()
        self.port_range_input.setPlaceholderText("Insérer un plage de ports (ex: 1-1024)")
        self.layout.addWidget(self.port_range_input)

        self.scan_button = QPushButton("Détecter Services et OS")
        self.scan_button.clicked.connect(self.start_detection)
        self.layout.addWidget(self.scan_button)

        self.results_display = QTextEdit()
        self.results_display.setMaximumHeight(80)
        self.layout.addWidget(self.results_display)

        # Add table for port status
        self.port_table = QTableWidget()
        self.port_table.setColumnCount(3)
        self.port_table.setHorizontalHeaderLabels(["Service", "Port", "Status"])
        self.port_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.port_table)

        self.network_scanner = NetworkScanner()
        self.target_ip = target_ip

        self.port_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.port_table.setFixedWidth(1000)
        self.results_display.setReadOnly(True)

    @pyqtSlot()
    def start_detection(self):
        ip = self.target_ip
        port_range = self.port_range_input.text()
        ports = self.network_scanner.scan_ports_anomaly(ip, port_range)
        os = self.network_scanner.detect_os(ip)

        self.port_table.clearContents()
        self.results_display.clear()
        self.results_display.append(f"IP: {ip}")
        self.results_display.append(f"OS détecté: {os}")
        # self.results_display.append("\nPorts ouverts et services:")
        
        # Populate the table
        self.port_table.setRowCount(len(ports))
        for row, port in enumerate(ports):
            service_item = QTableWidgetItem(f"{port['service']} {port['version']}" if port['service'] else "-")
            port_item = QTableWidgetItem(str(port['port']))
            status_item = QTableWidgetItem(port['status'])
            
            self.port_table.setItem(row, 0, service_item)
            self.port_table.setItem(row, 1, port_item)
            self.port_table.setItem(row, 2, status_item)
            
            if port['status'] == 'open':
                status_item.setBackground(QColor(255, 0, 0))  # Red background for open ports
                # self.results_display.append(f"Port {port['port']}: {port['service']} {port['version']}")

        # self.port_table.resizeColumnsToContents()
        # self.port_table.resizeRowsToContents()

