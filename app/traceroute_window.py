import subprocess
import re
import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLineEdit, QGraphicsView, 
    QGraphicsScene, QApplication, QTextEdit, QMessageBox, QGraphicsObject
)
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont, QPolygonF, QPalette
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QRectF, QPointF, QPropertyAnimation, 
    QObject, pyqtProperty
)

class TracerouteThread(QThread):
    update_signal = pyqtSignal(int, str, float)
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, target):
        super().__init__()
        self.target = target

    def run(self):
        try:
            process = subprocess.Popen(["tracert", "-4", self.target], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            for line in process.stdout:
                self.log_signal.emit(line.strip())
                match = re.search(r'^\s*(\d+)(?:\s+(<?\d+\s*ms|\*)\s+(<?\d+\s*ms|\*)\s+(<?\d+\s*ms|\*))+\s+(.+)$', line)
                if match:
                    hop_number = int(match.group(1))
                    times = [t.strip() for t in match.group(2, 3, 4)]
                    ip_or_hostname = match.group(5).strip()
                    if '[' in ip_or_hostname:
                        ip = re.search(r'\[(.*?)\]', ip_or_hostname).group(1)
                    else:
                        ip = ip_or_hostname
                
                    valid_times = [int(t[:-2]) for t in times if t != '*' and t != '<1 ms']
                    avg_time = sum(valid_times) / len(valid_times) if valid_times else 0
                
                    self.update_signal.emit(hop_number, ip, avg_time)
            process.wait()
            if process.returncode != 0:
                self.error_signal.emit(f"Traceroute failed with error code: {process.returncode}")
        except FileNotFoundError:
            self.error_signal.emit("Traceroute command not found. Please ensure it's installed and in your system's PATH.")
        except Exception as e:
            self.error_signal.emit(f"An unexpected error occurred: {e}")

class Node(QObject):
    def __init__(self, ip, x, y, hop_number, avg_time):
        super().__init__()
        self.ip = ip
        self.hop_number = hop_number
        self.avg_time = avg_time
        self.rect = QRectF(0, 0, 150, 40)
        self.x = x
        self.y = y

    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(QColor(200, 200, 255)))
        painter.drawRoundedRect(self.rect, 5, 5)
        painter.setFont(QFont("Arial", 8))
        painter.drawText(self.rect, Qt.AlignCenter, f"{self.hop_number}: {self.ip}\n{self.avg_time:.2f} ms")

    def pos(self):
        return QPointF(self.x, self.y)

class AnimatedArrow(QObject):
    def __init__(self, start_point, end_point, avg_time, parent=None):
        super().__init__(parent)
        self.start_point = start_point
        self.end_point = end_point
        self.avg_time = avg_time
        self._progress = 0.0

        self.animation = QPropertyAnimation(self, b"progress")
        self.animation.setDuration(1000)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)

    def boundingRect(self):
        return QRectF(self.start_point, self.end_point).normalized()

    def paint(self, painter, option, widget):
        painter.setPen(QPen(Qt.black, 2))
        current_end = QPointF(
            self.start_point.x() + (self.end_point.x() - self.start_point.x()) * self._progress,
            self.start_point.y() + (self.end_point.y() - self.start_point.y()) * self._progress
        )
        painter.drawLine(self.start_point, current_end)

        if self._progress == 1.0:
            vector = self.end_point - self.start_point
            vector = vector / (vector.x()**2 + vector.y()**2)**0.5 * 10
            normal = QPointF(-vector.y(), vector.x()) * 0.3
            p1 = self.end_point - vector + normal 
            p2 = self.end_point - vector - normal
            painter.setBrush(Qt.black)
            painter.drawPolygon(QPolygonF([self.end_point, p1, p2]))

    @pyqtProperty(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = value

    def start_animation(self):
        self.animation.start()

class NodeGraphicsItem(QGraphicsObject):
    def __init__(self, node, parent=None):
        super().__init__(parent)
        self.node = node
        self.setPos(node.pos())
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        return self.node.boundingRect()

    def paint(self, painter, option, widget):
        self.node.paint(painter, option, widget)

    def mousePressEvent(self, event):
        scene = self.scene()
        if scene and scene.views():
            view = scene.views()[0]
            if view and isinstance(view.parent(), TracerouteVisualization):
                view.parent().show_node_details(self.node)

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.PointingHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)

class ArrowGraphicsItem(QGraphicsObject):
    def __init__(self, arrow, parent=None):
        super().__init__(parent)
        self.arrow = arrow
        self.setZValue(-1)

    def boundingRect(self):
        return self.arrow.boundingRect()

    def paint(self, painter, option, widget):
        self.arrow.paint(painter, option, widget)

class TracerouteVisualization(QWidget):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.arrows = []
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.setWindowTitle("Traceroute Visualization")
        self.setMinimumSize(1000, 800)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                color: #2c3e50;
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
            QLineEdit, QTextEdit {
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
        """)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.WindowText, QColor(44, 62, 80))
        self.setPalette(palette)

        font = QFont("Segoe UI", 10)
        QApplication.setFont(font)

        self.tracert_input = QLineEdit()
        self.tracert_input.setPlaceholderText("Insérer IP ou bien Domain")
        layout.addWidget(self.tracert_input)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        self.start_button = QPushButton("Visualiser Traceroute")
        self.start_button.clicked.connect(self.start_visualization)
        layout.addWidget(self.start_button)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self.view)

        self.setLayout(layout)

    def start_visualization(self):
        self.start_button.setEnabled(False)
        self.log_area.clear()
        self.clear_visualization()
        target = self.tracert_input.text()
        if target:
            self.thread = TracerouteThread(target)
            self.thread.update_signal.connect(self.update_visualization)
            self.thread.log_signal.connect(self.log_output)
            self.thread.error_signal.connect(self.display_error)
            self.thread.finished.connect(self.on_traceroute_finished)
            self.thread.start()

    def update_visualization(self, hop_number, ip, avg_time):
        node_width = 150
        node_height = 40
        h_spacing = 200
        v_spacing = 80

        if hop_number == 1:
            x = 0
            y = 0
        else:
            prev_node = self.nodes[-1]
            if hop_number % 3 == 1:
                x = prev_node.pos().x()
                y = prev_node.pos().y() + v_spacing
            else:
                x = prev_node.pos().x() + h_spacing
                y = prev_node.pos().y()

        node = Node(ip, x, y, hop_number, avg_time)
        node_item = NodeGraphicsItem(node)
        self.scene.addItem(node_item)
        self.nodes.append(node)

        if len(self.nodes) > 1:
            prev_node = self.nodes[-2]
            if prev_node.pos().y() == node.pos().y():
                start_point = QPointF(prev_node.pos().x() + node_width, prev_node.pos().y() + node_height / 2)
                end_point = QPointF(node.pos().x(), node.pos().y() + node_height / 2)
            else:
                start_point = QPointF(prev_node.pos().x() + node_width / 2, prev_node.pos().y() + node_height)
                end_point = QPointF(node.pos().x() + node_width / 2, node.pos().y())
    
            arrow = AnimatedArrow(start_point, end_point, avg_time)
            arrow_item = ArrowGraphicsItem(arrow)
            self.scene.addItem(arrow_item)
            self.arrows.append(arrow)
            arrow.start_animation()

        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.view.centerOn(0, 0)

    def clear_visualization(self):
        self.scene.clear()
        self.nodes = []
        self.arrows = []

    def log_output(self, line):
        self.log_area.append(line)

    def display_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)
        self.start_button.setEnabled(True)

    def on_traceroute_finished(self):
        self.start_button.setEnabled(True)

    def show_node_details(self, node):
        try:
            details = f"Détails du saut {node.hop_number}\n\n"
            details += f"IP: {node.ip}\n"
            details += f"Temps moyen: {node.avg_time:.2f} ms\n\n"

            response = requests.get(f"https://ipapi.co/{node.ip}/json/")
            if response.status_code == 200:
                data = response.json()
                details += "Informations de géolocalisation:\n"
                details += f"Pays: {data.get('country_name', 'N/A')}\n"
                details += f"Région: {data.get('region', 'N/A')}\n"
                details += f"Ville: {data.get('city', 'N/A')}\n"
                details += f"Code postal: {data.get('postal', 'N/A')}\n"
                details += f"Latitude: {data.get('latitude', 'N/A')}\n"
                details += f"Longitude: {data.get('longitude', 'N/A')}\n"
                details += f"Fuseau horaire: {data.get('timezone', 'N/A')}\n"
                details += f"ISP: {data.get('org', 'N/A')}\n"
            else:
                details += "Impossible de récupérer les informations de géolocalisation.\n"
        
            QMessageBox.information(self, f"Détails du saut {node.hop_number}", details)
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible de récupérer les détails: {str(e)}")

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    ex = TracerouteVisualization()
    ex.show()
    sys.exit(app.exec_())

