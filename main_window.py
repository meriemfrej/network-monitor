import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, QGroupBox,
                            QListWidget, QMessageBox, QInputDialog)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from models import Host, Latence, BandePassante, Database
from datetime import datetime
import logging
from history_window import HistoryWindow

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MetricsWorker(QThread):
    update_metrics = pyqtSignal(float, float, float, float)

    def __init__(self, host):
        super().__init__()
        self.host = host

    def run(self):
        logger.info(f"Starting metrics calculation for host: {self.host.name} ({self.host.ip})")
        latency_metric = Latence(self.host)
        bandwidth_metric = BandePassante(self.host)
        
        logger.info("Calculating latency")
        latency, packets_lost = latency_metric.calculer()
        logger.info("Calculating bandwidth")
        upload, download = bandwidth_metric.calculer()
        
        logger.info(f"Metrics calculation complete. Latency: {latency:.2f}ms, Packets lost: {packets_lost:.1f}%, Upload: {upload:.2f} Mbps, Download: {download:.2f} Mbps")
        self.update_metrics.emit(latency, packets_lost, upload, download)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Surveillance Réseau")
        self.setMinimumSize(800, 600)
        
        logger.info("Initializing MainWindow")
        self.db = Database()
        self.history_window = None # Added instance variable
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Section Configuration
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        
        # Host management
        host_layout = QHBoxLayout()
        self.host_name_input = QLineEdit()
        self.host_name_input.setPlaceholderText("Nom de l'hôte")
        self.host_ip_input = QLineEdit()
        self.host_ip_input.setPlaceholderText("Adresse IP")
        add_host_button = QPushButton("Ajouter l'hôte")
        add_host_button.clicked.connect(self.add_host)
        host_layout.addWidget(self.host_name_input)
        host_layout.addWidget(self.host_ip_input)
        host_layout.addWidget(add_host_button)
        config_layout.addLayout(host_layout)
        
        # Host selection
        self.host_list = QListWidget()
        self.host_list.itemSelectionChanged.connect(self.on_host_selected)
        config_layout.addWidget(self.host_list)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Section Métriques
        metrics_group = QGroupBox("Métriques Réseau")
        metrics_layout = QVBoxLayout()
        self.selected_host_label = QLabel("Hôte sélectionné: Aucun")
        metrics_layout.addWidget(self.selected_host_label)
        
        # Latence
        self.latency_label = QLabel("Latence: -- ms")
        self.packets_lost_label = QLabel("Paquets perdus: --%")
        metrics_layout.addWidget(self.latency_label)
        metrics_layout.addWidget(self.packets_lost_label)
        
        # Bande passante
        self.download_label = QLabel("Download: -- Mbps")
        self.upload_label = QLabel("Upload: -- Mbps")
        metrics_layout.addWidget(self.download_label)
        metrics_layout.addWidget(self.upload_label)
        
        # New buttons
        self.button_layout = QHBoxLayout()
        self.admin_button_layout = QHBoxLayout()
        self.start_test_button = QPushButton("Start New Test")
        self.start_test_button.clicked.connect(self.start_new_test)
        self.show_history_button = QPushButton("Show History")
        self.show_history_button.clicked.connect(self.show_history)
        self.edit_host_button = QPushButton("Edit Host")
        self.edit_host_button.clicked.connect(self.update_host)
        self.delete_host_button = QPushButton("Delete Host")
        self.delete_host_button.clicked.connect(self.delete_host)
        self.admin_button_layout.addWidget(self.edit_host_button)
        self.admin_button_layout.addWidget(self.delete_host_button)
        self.button_layout.addWidget(self.start_test_button)
        self.button_layout.addWidget(self.show_history_button)
        metrics_layout.addLayout(self.admin_button_layout)
        metrics_layout.addLayout(self.button_layout)
        
        # Initially hide the buttons
        self.start_test_button.hide()
        self.show_history_button.hide()
        self.delete_host_button.hide()
        self.edit_host_button.hide()
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)
        
        # Timer pour les mises à jour automatiques
        self.timer = QTimer()
        self.timer.timeout.connect(self.automatic_update)
        self.timer.start(60000)  # Mise à jour toutes les 60 secondes
        logger.info("Automatic update timer started (60 second interval)")
        
        self.load_hosts()
        
        self.worker = None
        self.selected_host = None
        logger.info("MainWindow initialization complete")
    
    def load_hosts(self):
        logger.info("Loading hosts from database")
        hosts = self.db.get_hosts()
        self.host_list.clear()
        for host in hosts:
            self.host_list.addItem(f"{host.name} ({host.ip})")
        logger.info(f"Loaded {len(hosts)} hosts")
    
    def add_host(self):
        logger.info("Adding new host")
        name = self.host_name_input.text()
        ip = self.host_ip_input.text()
        if name and ip:
            logger.info(f"Adding host: {name} ({ip})")
            self.db.add_host(name, ip)
            self.load_hosts()
            self.host_name_input.clear()
            self.host_ip_input.clear()
            logger.info("Host added successfully")
        else:
            logger.warning("Attempted to add host with missing name or IP")
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un nom et une adresse IP pour l'hôte.")
    
    def update_host(self):
        if self.selected_host:
            host_name, host_ip = self.selected_host.split(' (')
            host_ip = host_ip.rstrip(')')

            new_name, ok1 = QInputDialog.getText(self, "Update Host", "Enter new name:", text=host_name)
            if ok1 and new_name:
                new_ip, ok2 = QInputDialog.getText(self, "Update Host", "Enter new IP:", text=host_ip)
                if ok2 and new_ip:
                    self.db.update_host(host_name, new_name, new_ip)
                    self.load_hosts()
                    self.selected_host = f"{new_name} ({new_ip})"
                    self.selected_host_label.setText(f"Hôte sélectionné: {self.selected_host}")
                    logger.info(f"Host updated: {host_name} -> {new_name}, {host_ip} -> {new_ip}")

    def delete_host(self):
        if self.selected_host:
            host_name = self.selected_host.split(' (')[0]
            reply = QMessageBox.question(self, "Delete Host", 
                                         f"Are you sure you want to delete {host_name}?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.db.delete_host(host_name)
                self.load_hosts()
                self.selected_host = None
                self.selected_host_label.setText("Hôte sélectionné: Aucun")
                self.reinitialize_metrics()
                self.start_test_button.hide()
                self.show_history_button.hide()
                self.edit_host_button.hide()
                self.delete_host_button.hide()
                logger.info(f"Host deleted: {host_name}")

    
    def on_host_selected(self):
        logger.info("Host selection changed")
        selected_items = self.host_list.selectedItems()
        if selected_items:
            selected_host = selected_items[0].text()
            self.selected_host_label.setText(f"Hôte sélectionné: {selected_host}")
            self.selected_host = selected_host
            self.start_test_button.show()
            self.show_history_button.show()
            self.edit_host_button.show()
            self.delete_host_button.show()
            self.reinitialize_metrics()
        else:
            self.selected_host_label.setText("Hôte sélectionné: Aucun")
            self.selected_host = None
            self.start_test_button.hide()
            self.show_history_button.hide()
            self.reinitialize_metrics()
    
    def reinitialize_metrics(self):
        logger.info("Reinitializing metrics")
        self.latency_label.setText("Latence: -- ms")
        self.packets_lost_label.setText("Paquets perdus: --%")
        self.download_label.setText("Download: -- Mbps")
        self.upload_label.setText("Upload: -- Mbps")
    
    def automatic_update(self):
        logger.info("Automatic update triggered")
        if self.selected_host:
            self.start_metrics_calculation()
    
    def start_new_test(self):
        logger.info("Manual test started")
        if self.selected_host:
            self.start_metrics_calculation()
    
    def show_history(self):
        logger.info("Showing history")
        if self.selected_host:
            host_name = self.selected_host.split(' (')[0]
            self.history_window = HistoryWindow(self.db, host_name) # Updated show_history method
            self.history_window.show()
    
    def start_metrics_calculation(self):
        if not self.selected_host:
            logger.info("No host selected, skipping metrics calculation")
            return
        
        host_ip = self.selected_host.split('(')[1].strip(')')
        host = Host(0, self.selected_host.split(' (')[0], host_ip)
        logger.info(f"Starting metrics calculation for host: {host.name} ({host.ip})")
        
        if self.worker is not None and self.worker.isRunning():
            logger.info("Terminating previous worker thread")
            self.worker.terminate()
            self.worker.wait()
        
        self.worker = MetricsWorker(host)
        self.worker.update_metrics.connect(self.on_metrics_updated)
        self.worker.start()
        logger.info("Metrics calculation worker thread started")
        
        # Disable the buttons while calculating
        self.start_test_button.setEnabled(False)
        self.show_history_button.setEnabled(False)
        self.edit_host_button.setEnabled(False)
        self.delete_host_button.setEnabled(False)
        self.host_list.setEnabled(False)
        logger.info("Buttons disabled during calculation")
    
    def on_metrics_updated(self, latency, packets_lost, upload, download):
        logger.info("Metrics calculation complete, updating UI")
        self.latency_label.setText(f"Latence: {latency:.2f} ms")
        self.packets_lost_label.setText(f"Paquets perdus: {packets_lost:.1f}%")
        self.upload_label.setText(f"Upload: {upload:.2f} Mbps")
        self.download_label.setText(f"Download: {download:.2f} Mbps")
        
        # Enregistrement des métriques dans la base de données
        now = datetime.now()
        if self.selected_host:
            host_id = self.db.get_host_id(self.selected_host.split(' (')[0])
            logger.info(f"Saving metrics to database for host_id: {host_id}")
            self.db.add_latence(host_id, now, latency, int(packets_lost))
            self.db.add_bande_passante(host_id, now, upload, download)
    
        # Re-enable the buttons after calculation
        self.start_test_button.setEnabled(True)
        self.show_history_button.setEnabled(True)
        self.edit_host_button.setEnabled(True)
        self.delete_host_button.setEnabled(True)
        self.host_list.setEnabled(True)
        logger.info("Buttons re-enabled after calculation")
        
    def closeEvent(self, event):
        logger.info("Application closing")
        if self.worker is not None and self.worker.isRunning():
            logger.info("Terminating worker thread")
            self.worker.terminate()
            self.worker.wait()
        self.db.close()
        logger.info("Database connection closed")
        super().closeEvent(event)

