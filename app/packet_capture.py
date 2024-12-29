from scapy.all import sniff, IP, TCP, UDP, ICMP, ARP
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QWidget, QListWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHBoxLayout, QAbstractItemView, QHeaderView, QListWidget, QListWidgetItem
from PyQt5.QtGui import QPalette, QColor

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
        packet_info = {
            "source": packet[IP].src if IP in packet else packet.src,
            "destination": packet[IP].dst if IP in packet else packet.dst,
            "protocol": "Unknown",
            "sport": None,
            "dport": None,
            "tcp_flags": None
        }

        if IP in packet:
            if TCP in packet:
                packet_info["protocol"] = "TCP"
                packet_info["sport"] = packet[TCP].sport
                packet_info["dport"] = packet[TCP].dport
                packet_info["tcp_flags"] = packet[TCP].flags
            elif UDP in packet:
                packet_info["protocol"] = "UDP"
                packet_info["sport"] = packet[UDP].sport
                packet_info["dport"] = packet[UDP].dport
            elif ICMP in packet:
                packet_info["protocol"] = "ICMP"
        elif ARP in packet:
            packet_info["protocol"] = "ARP"
        
        if packet_info["protocol"] in ["TCP", "UDP"]:
            if packet_info["sport"] == 110 or packet_info["dport"] == 110:
                packet_info["protocol"] = "POP"
            elif packet_info["sport"] == 25 or packet_info["dport"] == 25:
                packet_info["protocol"] = "SMTP"

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
        self.packet_table.setColumnCount(6)
        self.packet_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.packet_table.setHorizontalHeaderLabels(["Source IP", "Source Port", "Destination IP", "Destination Port", "Protocol", "TCP Flags"])
        header = self.packet_table.horizontalHeader()       
        for i in range(6):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        # Create protocol filter list
        self.protocol_list = QListWidget()
        self.protocol_list.setSelectionMode(QAbstractItemView.MultiSelection)
        protocols = ["UDP", "TCP", "ICMP", "ARP", "POP", "SMTP"]
        for protocol in protocols:
            item = QListWidgetItem(protocol)
            self.protocol_list.addItem(item)
        self.protocol_list.itemSelectionChanged.connect(self.filter_packets)

        # Create layouts
        filter_layout = QVBoxLayout()
        filter_layout.addWidget(self.protocol_list)

        table_layout = QVBoxLayout()
        table_layout.addWidget(self.packet_table)

        main_layout = QHBoxLayout()
        main_layout.addLayout(filter_layout, 1)
        main_layout.addLayout(table_layout, 3)

        self.setLayout(main_layout)

        self.setWindowTitle("Packet Capture")
        self.setMinimumSize(1200, 800)
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
        self.packet_table.setItem(row, 5, QTableWidgetItem(str(packet_info["tcp_flags"])))
        self.filter_packets()

    def filter_packets(self):
        selected_protocols = [item.text() for item in self.protocol_list.selectedItems()]
        for row in range(self.packet_table.rowCount()):
            protocol = self.packet_table.item(row, 4).text()
            self.packet_table.setRowHidden(row, len(selected_protocols) > 0 and protocol not in selected_protocols)