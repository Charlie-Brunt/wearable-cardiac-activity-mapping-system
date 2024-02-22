import sys
import time
import platform
import serial
from PyQt5.QtWidgets import (
    QWidget, QSlider, QLineEdit, QLabel, QPushButton, QScrollArea, QApplication,
    QHBoxLayout, QVBoxLayout, QMainWindow, QSizePolicy, QToolBar
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5 import QtGui
import numpy as np
import pyqtgraph as pg
from numpy_ringbuffer import RingBuffer

class App(QMainWindow):
    def __init__(self, num_plots, parent=None):
        super(App, self).__init__(parent)

        # Initialize the application window
        self.setWindowTitle("BSPM Monitor")  # Set the window title
        self.setupUi(num_plots)

    def setupUi(self, num_plots):
        # Create the main layout
        self.mainbox = QWidget()
        self.setCentralWidget(self.mainbox)
        self.layout = QVBoxLayout(self.mainbox)

        # Create a scroll area widget for plots
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.layout.addWidget(self.scroll)

        # Create a widget for plots
        self.canvas = QWidget()
        self.scroll.setWidget(self.canvas)
        self.canvas_layout = QVBoxLayout(self.canvas)
        self.canvas_layout.setSpacing(0)

        # Create a widget for controls
        self.controls_widget = QWidget()
        self.controls_widget.setLayout(QHBoxLayout())
        self.layout.addWidget(self.controls_widget)
        self.controls_widget.setMaximumHeight(50)

        # Add FPS counter label
        self.label = QLabel()
        self.controls_widget.layout().addWidget(self.label)

        # Add pause button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setMaximumWidth(80)
        self.pause_button.clicked.connect(self.toggle_update)
        self.controls_widget.layout().addWidget(self.pause_button)

        # Initialize data variables
        self.x = np.linspace(0, 50., num=128)
        self.counter = 0
        self.fps = 0.
        self.lastupdate = time.time()
        self.update_enabled = True

        # Create plots
        self.create_plots(num_plots)
        self._update()
        self.showMaximized()

    def create_plots(self, num_plots):
        self.plots = []
        cmap = pg.ColorMap([0, num_plots-1], [pg.mkColor('#729ece'), pg.mkColor('#ff9e4a')])
        font = QtGui.QFont()
        font.setPixelSize(10)
        for i in range(num_plots):
            color = cmap.map(i)
            plot = pg.PlotWidget()
            plot.setLabel("left", f"Plot {i+1}")
            plot.getAxis("bottom").setStyle(tickFont=font)
            plot.getAxis("left").setStyle(tickFont=font)
            plot.setMinimumHeight(120)
            curve = plot.plot(pen=color)
            self.plots.append((curve, plot))  # Store both the plot and the curve handle
            self.canvas_layout.addWidget(plot)

    def _update(self):
        if self.update_enabled:
            self.ydata = np.sin(self.x/3.+ self.counter/9.)
            for curve, plot in self.plots:
                if self.is_plot_visible(plot):
                    curve.setData(self.ydata)
            self.fps_counter()
        QTimer.singleShot(10, self._update)
        self.counter += 1

    def is_plot_visible(self, plot):
        """Check if the plot is visible in the scroll area."""
        scroll_pos = self.scroll.verticalScrollBar().value()
        plot_pos = plot.pos().y()
        return scroll_pos - plot.height() < plot_pos < scroll_pos + self.scroll.viewport().height()

    def toggle_update(self):
        new_label = "Resume" if self.update_enabled else "Pause"
        self.update_enabled = not self.update_enabled
        self.pause_button.setText(new_label)

    def fps_counter(self):
        now = time.time()
        dt = (now - self.lastupdate)
        if dt <= 0:
            dt = 0.000000000001
        fps2 = 1.0 / dt
        self.lastupdate = now
        self.fps = self.fps * 0.9 + fps2 * 0.1
        tx = 'Frame Rate:  {fps:.1f} FPS'.format(fps=self.fps)
        self.label.setText(tx)

    def read_from_com_port(self, port, baudrate=115200, timeout=None):
            try:
                ser = connect_to_board(baudrate)
                if ser.isOpen():
                    data = ser.read_all().decode('utf-8')
                    return data
                else:
                    print("Could not open serial port.")
                    return None
            except serial.SerialException as e:
                print(f"Serial port error: {e}")
                return None

    def connect_to_board(baudrate):
        board_ports = list(serial.tools.list_ports.comports())
        if platform.system() == "Darwin":
            for p in board_ports:
                print(p[1])
                if "XIAO" in p[1]:
                    board_port = p[0]
                    print("Connecting to board on port:", board_port)
                    ser = serial.Serial(board_port, baudrate, timeout=1)
                    return ser
            print("Couldn't find board port.")
            sys.exit(1)
        elif platform.system() == "Windows":
            for p in board_ports:
                print(p[2])
                if "2886" in p[2]:
                    board_port = p[0]
                    print("Connecting to board on port:", board_port)
                    ser = serial.Serial(board_port, baudrate, timeout=1)
                    return ser
            print("Couldn't find board port.")
            sys.exit(1)
        else:
            print("Unsupported platform")
            sys.exit(1)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    num_plots = 16
    ecg_app = App(num_plots)
    ecg_app.show()
    sys.exit(app.exec_())