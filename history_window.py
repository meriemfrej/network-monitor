from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class HistoryWindow(QWidget):
    def __init__(self, db, host_name):
        super().__init__()
        self.db = db
        self.host_name = host_name
        self.setWindowTitle(f"Historique des tests - {host_name}")
        self.setMinimumSize(600, 400)
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
                self.table.setItem(row, col, item)

        logger.info(f"Loaded {len(sorted_data)} historical records for {self.host_name}")

