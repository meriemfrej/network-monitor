import subprocess
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLineEdit, QGraphicsView, QGraphicsScene, QGraphicsObject, QGraphicsLineItem, QApplication, QTextEdit
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont, QPolygonF, QPalette
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRectF, QPointF, QPropertyAnimation, QObject, pyqtProperty, QLineF
import re

class TracerouteThread(QThread):
    update_signal = pyqtSignal(int, str, float)
    log_signal = pyqtSignal(str)

    def __init__(self, target):
        super().__init__()
        self.target = target

    def run(self):
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
            
                # Calculate average response time
                valid_times = [int(t[:-2]) for t in times if t != '*' and t != '<1 ms']
                avg_time = sum(valid_times) / len(valid_times) if valid_times else 0
            
                self.update_signal.emit(hop_number, ip, avg_time)
        process.wait()

class Node(QGraphicsObject):
    def __init__(self, ip, x, y):
        super().__init__()
        self.ip = ip
        self.rect = QRectF(0, 0, 150, 40)
        self.setPos(x, y)

    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(QColor(200, 200, 255)))
        painter.drawRoundedRect(self.rect, 5, 5)
        painter.setFont(QFont("Arial", 8))
        painter.drawText(self.rect, Qt.AlignCenter, f"{self.ip}")

class Arrow(QGraphicsLineItem):
    def __init__(self, start_point, end_point):
        super().__init__(start_point.x(), start_point.y(), end_point.x(), end_point.y())
        self.arrow_head = QPolygonF()

        # Create arrow head
        vector = end_point - start_point
        vector = vector / (vector.x()**2 + vector.y()**2)**0.5 * 20
        normal = QPointF(-vector.y(), vector.x())
        p1 = end_point - vector + normal * 0.5
        p2 = end_point - vector - normal * 0.5
        self.arrow_head.append(end_point)
        self.arrow_head.append(p1)
        self.arrow_head.append(p2)

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        painter.setBrush(Qt.black)
        painter.drawPolygon(self.arrow_head)

class AnimatedArrow(QGraphicsObject):
    def __init__(self, start_point, end_point, avg_time, parent=None):
        super().__init__(parent)
        self.start_point = start_point
        self.end_point = end_point
        self.avg_time = avg_time
        self._progress = 0.0
        self.setZValue(-1)  # Ensure arrows are drawn behind nodes

        self.animation = QPropertyAnimation(self, b"progress")
        self.animation.setDuration(1000)  # 1 second duration
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
            # Draw arrowhead
            vector = self.end_point - self.start_point
            vector = vector / (vector.x()**2 + vector.y()**2)**0.5 * 10
            normal = QPointF(-vector.y(), vector.x()) * 0.3
            p1 = self.end_point - vector + normal 
            p2 = self.end_point - vector - normal
            painter.setBrush(Qt.black)
            painter.drawPolygon(QPolygonF([self.end_point, p1, p2]))

            # # Draw average time label
            # mid_point = (self.start_point + self.end_point) / 2
            # mid_point += QPointF(10, 15)
    
            # painter.setFont(QFont("Arial", 8))
            # painter.drawText(mid_point, f"{self.avg_time:.2f} ms")

    @pyqtProperty(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = value
        self.update()

    def start_animation(self):
        self.animation.start()


class TracerouteVisualization(QWidget):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.arrows = []
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()


        self.setWindowTitle("Traceroute")
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

        self.tracert_input = QLineEdit()
        self.tracert_input.setPlaceholderText("Insérer IP ou bien Domain")
        layout.addWidget(self.tracert_input)
        

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        self.log_area.setReadOnly(True)

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
            if hop_number % 3 == 1:  # Start of a new level
                x = prev_node.pos().x()
                y = prev_node.pos().y() + v_spacing
            else:
                x = prev_node.pos().x() + h_spacing
                y = prev_node.pos().y()

        node = Node(f"{hop_number}: {ip}\n{avg_time:.2f} ms", x, y)
        self.scene.addItem(node)
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
            self.scene.addItem(arrow)
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

    def on_traceroute_finished(self):
        self.start_button.setEnabled(True)

