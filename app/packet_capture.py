from scapy.all import sniff, IP, TCP, UDP
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QWidget, QListWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QVBoxLayout, QAbstractItemView, QHeaderView
from PyQt5.QtGui import  QPalette, QColor

class PacketCapture(QObject):
    packet_captured = pyqtSignal(dict)

    def __init__(self, target_ip):
        super().__init__()
        self.is_capturing = False
        self.packet_list = QListWidget()
        self.max_packets = 1000  # Maximum number of packets to capture
        self.target_ip = target_ip

    def start_capture(self):
        self.is_capturing = True
        self.sniff_thread = SniffThread(self)
        self.sniff_thread.start()

    def stop_capture(self):
        self.is_capturing = False
        self.sniff_thread.quit()
        self.sniff_thread.wait()

    def process_packet(self, packet):
        if IP in packet:
            packet_info = {
                "source": packet[IP].src,
                "destination": packet[IP].dst,
            }
            if packet[IP].proto == 6:
                packet_info["protocol"] = "TCP"
            elif packet[IP].proto == 17:
                packet_info["protocol"] = "UDP"
            else:
                packet_info["protocol"] = "Other"
            if TCP in packet:
             
                packet_info["sport"] = packet[TCP].sport
                packet_info["dport"] = packet[TCP].dport
            elif UDP in packet:
              
                packet_info["sport"] = packet[UDP].sport
                packet_info["dport"] = packet[UDP].dport
            else:
                packet_info["sport"] = None
                packet_info["dport"] = None
            
            self.packet_captured.emit(packet_info)
            self.packet_list.addItem(str(packet_info))

    def get_packet_list(self):
        return self.packet_list

class SniffThread(QThread):
    def __init__(self, packet_capture):
        super().__init__()
        self.packet_capture = packet_capture
        self.packet_count = 0

    def run(self):
        sniff(prn=self.capture_packet, store=False, count=self.packet_capture.max_packets, filter=f"host {self.packet_capture.target_ip}")

    def capture_packet(self, packet):
        self.packet_capture.process_packet(packet)
        self.packet_count += 1
        if self.packet_count >= self.packet_capture.max_packets:
            self.quit()


class PacketCaptureWidget(QWidget):
    def __init__(self, target_ip):
        super().__init__()
        self.packet_capture = PacketCapture(target_ip)
        self.packet_table = QTableWidget()
        self.packet_table.setColumnCount(5)
        self.packet_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.packet_table.setHorizontalHeaderLabels(["Source IP", "Source Port", "Destination IP", "Destination Port", "Protocol"])
        header = self.packet_table.horizontalHeader()       
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        layout = QVBoxLayout()
        layout.addWidget(self.packet_table)
        self.setLayout(layout)
        self.setWindowTitle("Captures Des Packets")
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

    def start_capture(self):
        self.packet_capture.start_capture()
        self.packet_capture.packet_captured.connect(self.add_packet_to_table)

    def stop_capture(self):
        self.packet_capture.stop_capture()

    def add_packet_to_table(self, packet_info):
   
        row = self.packet_table.rowCount()
        self.packet_table.insertRow(row)
        self.packet_table.setItem(row, 0, QTableWidgetItem(str(packet_info["source"])))
        self.packet_table.setItem(row, 1, QTableWidgetItem(str(packet_info["sport"])))
        self.packet_table.setItem(row, 2, QTableWidgetItem(str(packet_info["destination"])))
        self.packet_table.setItem(row, 3, QTableWidgetItem(str(packet_info["dport"])))
        self.packet_table.setItem(row, 4, QTableWidgetItem(str(packet_info["protocol"])))