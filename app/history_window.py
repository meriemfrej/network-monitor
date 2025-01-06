from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QStyle, QAbstractItemView, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPalette, QColor
import pyqtgraph as pg
import logging
from datetime import datetime
import numpy as np

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
        self.table.cellClicked.connect(self.cell_clicked)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.setWindowIcon(QIcon('icons/history.png'))

        self.setWindowTitle("Historique")
        self.setMinimumSize(1000, 800)

        self.apply_styles()

        palette = self.palette()
        palette.setColor(QPalette.Button, QColor(52, 152, 219))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        self.setPalette(palette)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def apply_styles(self):
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

    def load_history(self):
        logger.info(f"Loading history for host: {self.host_name}")
        host_id = self.db.get_host_id(self.host_name)
        if host_id is None:
            logger.warning(f"No host found with name: {self.host_name}")
            return

        latency_data = self.db.get_latency_history(host_id)
        bandwidth_data = self.db.get_bandwidth_history(host_id)

        combined_data = {}
        for date, latency, packets_lost in latency_data:
            combined_data[date] = [latency, packets_lost, None, None]
        for date, upload, download in bandwidth_data:
            if date in combined_data:
                combined_data[date][2:] = [upload, download]
            else:
                combined_data[date] = [None, None, upload, download]

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

    def cell_clicked(self, row, column):
        if column == 0:  # Date column
            return

        value = self.table.item(row, column).text()
        
        if value == "N/A":
            return

        column_names = ["Date", "Latence", "Paquets perdus", "Upload", "Download"]
        column_name = column_names[column]


        
        self.plot_curve(column)

    def plot_curve(self, column):
        dates = []
        values = []
        for row in range(self.table.rowCount()):
            date_item = self.table.item(row, 0)
            value_item = self.table.item(row, column)
            if date_item and value_item and value_item.text() != "N/A":
                dates.append(date_item.text())
                values.append(float(value_item.text()))

        dates.reverse()
        values.reverse()

        plot_window = PlotWindow(self, column, dates, values)
        plot_window.show()

class PlotWindow(QDialog):
    def __init__(self, parent, column, dates, values, scale_minutes=1):
        super().__init__(parent)
        self.setWindowTitle(f"Courbe - {parent.table.horizontalHeaderItem(column).text()}")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('k')  # fond noir
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(plot_widget)
        self.setLayout(layout)

        # Convert dates to timestamps for plotting
        timestamps = []
        for date in dates:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                try:
                    dt = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        dt = datetime.strptime(date, "%Y-%m-%d")
                    except ValueError:
                        print(f"Could not parse date: {date}")
                        continue
            timestamps.append(dt.timestamp())

        # Plot the data
        plot_widget.plot(x=timestamps, y=values, pen=pg.mkPen(color=(52, 152, 219), width=2))

        plot_widget.setLabel('left', parent.table.horizontalHeaderItem(column).text())
        plot_widget.setLabel('bottom', f'Date and Time ({scale_minutes}-minute intervals)')

        # Customize x-axis
        ax = plot_widget.getAxis('bottom')
        ax.setStyle(tickTextOffset=10)

        # Create a function to format dates based on the scale
        def timestamp_to_str(timestamp):
            dt = datetime.fromtimestamp(timestamp)
            if scale_minutes < 60:
                return dt.strftime("%Y-%m-%d %H:%M")
            elif scale_minutes < 1440:  # Less than a day
                return dt.strftime("%Y-%m-%d %H:00")
            else:
                return dt.strftime("%Y-%m-%d")

        # Select ticks and set labels
        ticks = self.select_ticks(timestamps, scale_minutes)
        ax.setTicks([[(ts, timestamp_to_str(ts)) for ts in ticks]])

        # Rotate x-axis labels for better readability
        ax.setTickFont(pg.QtGui.QFont('Arial', 8))
       

        # Set tick spacing based on the scale
        tick_spacing = scale_minutes * 60  # Convert minutes to seconds
        ax.setTickSpacing(major=tick_spacing, minor=tick_spacing/2)

        # Adjust the view range to show all data points
        plot_widget.setXRange(min(timestamps), max(timestamps))

    def select_ticks(self, timestamps, scale_minutes):
        """Select ticks at regular intervals based on the scale, ensuring start and end are included."""
        if len(timestamps) <= 20:
            return timestamps
        
        start = min(timestamps)
        end = max(timestamps)
        duration = end - start
        
        # Aim for about 20 ticks, but respect the minimum scale
        interval = max(duration / 19, scale_minutes * 60)
        
        ticks = [start]
        current = start + interval
        while current < end:
            ticks.append(current)
            current += interval
        ticks.append(end)
        
        return ticks