import nmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
from PyQt5.QtCore import pyqtSignal, QThread, pyqtSlot, QRegExp
from PyQt5.QtGui import  QRegExpValidator, QPalette, QColor
from models import Database
class NetworkScanner(QWidget):
    scan_complete = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.nm = nmap.PortScanner()

    def scan_network(self, ip_range):
        print(f"Scanning network: {ip_range}")
        self.nm.scan(hosts=ip_range, arguments='-sn')
        hosts = []
        for host in self.nm.all_hosts():
            if self.nm[host].state() == 'up':
                hosts.append({
                    'ip': host,
                    'hostname': self.nm[host].hostname(),
                    'status': 'Up',
                    'adresse_mac': self.nm[host]['addresses'].get('mac', 'N/A')
                })
        self.scan_complete.emit(hosts)

    def scan_ports(self, ip, port_range):
        self.nm.scan(ip, arguments=f'-p {port_range}')
        open_ports = []
        for port in self.nm[ip]['tcp']:
            if self.nm[ip]['tcp'][port]['state'] == 'open':
                open_ports.append({
                    'port': port,
                    'service': self.nm[ip]['tcp'][port]['name'],
                    'version': self.nm[ip]['tcp'][port]['version']
                })
        return open_ports
    
    def scan_ports_anomaly(self, ip, port_range):
        self.nm.scan(ip, arguments=f'-p {port_range}')
        port_status = []
        start_port, end_port = map(int, port_range.split('-'))
        for port in range(start_port, end_port+1):
            if port in self.nm[ip]['tcp']:
                status = self.nm[ip]['tcp'][port]['state']
                service = self.nm[ip]['tcp'][port]['name']
                version = self.nm[ip]['tcp'][port]['version']
            else:
                status = 'closed'
                service = ''
                version = ''
            port_status.append({
                'port': port,
                'status': status,
                'service': service,
                'version': version
            })
        return port_status

    def detect_os(self, ip):
        
        self.nm.scan(ip, arguments='-O')
        if 'osmatch' in self.nm[ip]:
            return self.nm[ip]['osmatch'][0]['name']
        return 'Unknown'


class NetworkScannerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.network_scanner = NetworkScanner()
        self.input_field = QLineEdit()
        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.start_scan)
        self.table = QTableWidget()
        
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["IP", "Hostname", "Status", "Adresse MAC", "Actions"])
        header = self.table.horizontalHeader()       
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        layout = QVBoxLayout()
        layout.addWidget(self.input_field)
        layout.addWidget(self.scan_button)
        layout.addWidget(self.table)
        self.table.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)
        self.network_scanner.scan_complete.connect(self.display_scan_results)
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

        ip_regex = QRegExp(r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[12]?[0-9])$")
        ip_validator = QRegExpValidator(ip_regex)
        self.input_field.setValidator(ip_validator)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.scan_thread = None
    

    def start_scan(self):
        self.scan_button.setEnabled(False)
        self.input_field.setEnabled(False)
        ip_range = self.input_field.text()
        self.scan_thread = ScanThread(self.network_scanner, ip_range)
        self.scan_thread.finished.connect(self.scan_finished)
        self.scan_thread.start()

    def scan_finished(self):
        self.scan_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.scan_thread = None

    def display_scan_results(self, hosts):
        self.table.setRowCount(len(hosts))
        print(f"hosts number: {len(hosts)}")
        for i, host in enumerate(hosts):
            ip = host['ip']
            hostname = host['hostname']
            status = host['status']
            adresse_mac = host['adresse_mac']
            self.table.setItem(i, 0, QTableWidgetItem(ip))
            self.table.setItem(i, 1, QTableWidgetItem(hostname))
            self.table.setItem(i, 2, QTableWidgetItem(status))
            self.table.setItem(i, 3, QTableWidgetItem(adresse_mac))
            db = Database("network_monitor.db")
            existing_host = db.host_exists(ip)
            if existing_host is False:
                # Create a button to add the host
                add_button = QPushButton("Ajouter hôte")
                add_button.clicked.connect(lambda ip=ip, hostname=hostname: db.add_host(name=hostname, ip=ip))
                self.table.setCellWidget(i, 4, add_button)
                add_button.setEnabled(True)
            else:
                # If host already exists, don't show the add button
                self.table.setItem(i, 4, QTableWidgetItem(""))

    def closeEvent(self, event):
        if self.scan_thread is not None:
            self.scan_thread.quit()
            self.scan_thread.wait()
        event.accept()

class ScanThread(QThread):
    def __init__(self, network_scanner, ip_range):
        super().__init__()
        self.network_scanner = network_scanner
        self.ip_range = ip_range

    @pyqtSlot()
    def run(self):
        self.network_scanner.scan_network(self.ip_range)