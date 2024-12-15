from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget
class AnomalyDetection(QWidget):
    anomaly_detected = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.rules = []

    def add_rule(self, rule_type, value, description):
        self.rules.append({"type": rule_type, "value": value, "description": description})

    def check_packet(self, packet_info):
        for rule in self.rules:
            if rule["type"] == "port" and packet_info.get("dport") == rule["value"]:
                self.anomaly_detected.emit({"type": "Port", "description": rule["description"]})
            elif rule["type"] == "ip" and packet_info.get("destination") == rule["value"]:
                self.anomaly_detected.emit({"type": "IP", "description": rule["description"]})

