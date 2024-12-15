from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QStyle, QAbstractItemView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import  QIcon, QPalette, QColor
import logging

logger = logging.getLogger(__name__)

class HistoryWindow(QWidget):
    def __init__(self, db, host_name):
        super().__init__()
        self.db = db
        self.host_name = host_name
        self.init_ui()
        self.load_history()

    def init_ui(self):
        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Latence (ms)", "Paquets perdus (%)", "Upload (Mbps)", "Download (Mbps)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.setWindowIcon(QIcon('icons/history.png'))

        self.setWindowTitle("Scan Réseau")
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
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def load_history(self):
        logger.info(f"Loading history for host: {self.host_name}")
        host_id = self.db.get_host_id(self.host_name)
        if host_id is None:
            logger.warning(f"No host found with name: {self.host_name}")
            return

        latency_data = self.db.get_latency_history(host_id)
        bandwidth_data = self.db.get_bandwidth_history(host_id)

        # Combine latency and bandwidth data
        combined_data = {}
        for date, latency, packets_lost in latency_data:
            combined_data[date] = [latency, packets_lost, None, None]
        for date, upload, download in bandwidth_data:
            if date in combined_data:
                combined_data[date][2:] = [upload, download]
            else:
                combined_data[date] = [None, None, upload, download]

        # Sort by date (newest first)
        sorted_data = sorted(combined_data.items(), key=lambda x: x[0], reverse=True)

        self.table.setRowCount(len(sorted_data))
        for row, (date, data) in enumerate(sorted_data):
            self.table.setItem(row, 0, QTableWidgetItem(date))
            for col, value in enumerate(data, start=1):
                item = QTableWidgetItem(f"{value:.2f}" if value is not None else "N/A")
                item.setTextAlignment(Qt.AlignCenter)
                if col == 1:  # Latence
                    item.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
                elif col == 2:  # Paquets perdus
                    item.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
                elif col == 3:  # Upload
                    item.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
                elif col == 4:  # Download
                    item.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
                self.table.setItem(row, col, item)

        logger.info(f"Loaded {len(sorted_data)} historical records for {self.host_name}")

