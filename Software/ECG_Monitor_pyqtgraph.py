import sys
import time
import platform
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QScrollArea, QApplication,
    QHBoxLayout, QVBoxLayout, QMainWindow, QTextEdit
)
from PyQt5.QtCore import QTimer
from PyQt5 import QtGui
import numpy as np
import pyqtgraph as pg

class App(QMainWindow):
    """
    Main application class for BSPM Monitor.
    """

    def __init__(self, channels: int, parent=None):
        """
        Constructor for App class.

        Args:
            channels (int): Number of plots to display.
            parent: Parent widget.
        """
        super(App, self).__init__(parent)

        # Initialise critical parameters and variables
        self.sampling_frequency = 200 # Hz
        self.buffer_size = 2 * self.sampling_frequency # 2 second window
        self.buffer = bytearray(self.buffer_size)
        self.channels = channels

        # Initialise the application window
        self.setWindowTitle("BSPM Monitor")  # Set the window title
        self.setupUi()
        self.show()
        self.console.append("Initialising...")

        # Connect to board
        QTimer.singleShot(1000, self.delayed_init)
    
    def delayed_init(self):
        """
        Delayed initialisation after the window is shown.
        """
        self.console.append("Searching for board...")
        self.ser = self.connect_to_board(115200)

    def setupUi(self):
        """
        Setup user interface.

        """
        # Create the main layout
        self.mainbox = QWidget()
        self.setCentralWidget(self.mainbox)
        self.layout = QVBoxLayout(self.mainbox)
        self.layout.setSpacing(0)

        # Create a scroll area widget for plots
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.layout.addWidget(self.scroll)

        # Create a widget for plots
        self.canvas = QWidget()
        self.scroll.setWidget(self.canvas)
        self.canvas_layout = QVBoxLayout(self.canvas)
        self.canvas_layout.setSpacing(0)
        
        # Initialize data variables
        self.x = np.linspace(0, 50., num=self.buffer_size)
        self.counter = 0
        self.fps = 0.
        self.lastupdate = time.time()
        self.started_monitoring = False
        self.update_enabled = False
        self.recording_active = False

        # Create plots
        self.create_plots()
        self._update()
        self.showMaximized()

        # Create a widget for controls
        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)
        self.layout.addWidget(self.controls_widget)
        self.controls_widget.setMaximumHeight(70)

        # Create a console widget
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        font = QtGui.QFont("Courier", 10)
        self.console.setFont(font)
        self.controls_layout.addWidget(self.console)
        self.console.setMaximumWidth(500)

        # Add record to CSV button
        self.record_button = QPushButton("Record to CSV")
        self.record_button.setMaximumWidth(120)
        self.record_button.clicked.connect(self.toggle_record)
        self.controls_layout.addWidget(self.record_button)

        # Add a save as png button
        self.save_button = QPushButton("Save as PNG")
        self.save_button.setMaximumWidth(120)
        self.save_button.clicked.connect(self.save_as_png)
        self.controls_layout.addWidget(self.save_button)
        self.save_button.setEnabled(False)


        # Add pause button
        self.pause_button = QPushButton("Start Monitoring")
        self.pause_button.setMaximumWidth(120)
        self.pause_button.clicked.connect(self.toggle_update)
        self.controls_layout.addWidget(self.pause_button)

        # Add FPS counter label
        self.label = QLabel()
        self.controls_layout.addWidget(self.label)

    def create_plots(self):
        """
        Create plot widgets.

        Args:
            channels (int): Number of plots to create.
        """
        self.plots = []
        cmap = pg.ColorMap([0, self.channels-1], [pg.mkColor('#729ece'), pg.mkColor('#ff9e4a')])
        font = QtGui.QFont()
        font.setPixelSize(10)
        for i in range(self.channels):
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
        """
        Update plots and FPS counter.
        """
        if self.update_enabled:
            self.ydata = np.sin(self.x/3.+ self.counter/9.)
            for curve, plot in self.plots:
                if self.is_plot_visible(plot):
                    curve.setData(self.ydata)
            self.fps_counter()
        QTimer.singleShot(10, self._update)
        self.counter += 1

    def is_plot_visible(self, plot):
        """
        Check if the plot is visible in the scroll area.

        Args:
            plot: Plot widget to check.

        Returns:
            bool: True if the plot is visible, False otherwise.
        """
        scroll_pos = self.scroll.verticalScrollBar().value()
        plot_pos = plot.pos().y()
        return scroll_pos - plot.height() < plot_pos < scroll_pos + self.scroll.viewport().height()

    def toggle_update(self):
        """
        Toggle update of plots.
        """
        if not self.ser: # Remove not later
            if not self.started_monitoring:
                self.update_enabled = True
                self.started_monitoring = True
                new_label = "Pause"
                self.pause_button.setText(new_label)
                self.console.append("Monitoring started.")
            else:
                self.update_enabled = not self.update_enabled
                new_label = "Resume" if not self.update_enabled else "Pause"
                self.pause_button.setText(new_label)
                self.console.append("Monitoring paused." if not self.update_enabled else "Monitoring resumed.")
                if self.update_enabled:
                    self.save_button.setEnabled(False)
                else:
                    self.save_button.setEnabled(True)
        else:
            self.console.append("Not connected to board.")

    def toggle_record(self):
        """
        Toggle recording to CSV file.
        """
        self.recording_active = not self.recording_active
        new_label = "Save recording" if self.recording_active else "Record to CSV"
        self.record_button.setText(new_label)

    def save_as_png(self):
        """
        Save the plot as a PNG file.
        """
        filename = str(time.time()) + ".png"
        if filename:
            self.canvas.grab().save(filename)
            self.console.append(f"Plot saved as {filename}.")

    def fps_counter(self):
        """
        Calculate and update FPS counter label.
        """
        now = time.time()
        dt = (now - self.lastupdate)
        if dt <= 0:
            dt = 0.000000000001
        fps2 = 1.0 / dt
        self.lastupdate = now
        self.fps = self.fps * 0.9 + fps2 * 0.1
        tx = '{fps:.1f} FPS'.format(fps=self.fps)
        self.label.setText(tx)

    def read_from_com_port(self, baudrate=115200):
        """
        Read data from a COM port.

        Args:
            port (str): COM port name.
            baudrate (int): Baudrate of the COM port.
            timeout: Timeout value.

        Returns:
            str: Data read from the COM port.
        """
        try:
            ser = self.connect_to_board(baudrate)
            if ser.isOpen():
                buffer_size = 128
                data = ser.read(self.buffer_size)
                return data
            else:
                print("Could not open serial port.")
                return None
        except serial.SerialException as e:
            print(f"Serial port error: {e}")
            return None

    def connect_to_board(self, baudrate):
        """
        Connect to the board.

        Args:
            baudrate (int): Baudrate for serial communication.

        Returns:
            serial.Serial: Serial object for communication with the board.
        """
        board_ports = list(serial.tools.list_ports.comports())
        if platform.system() == "Darwin":
            for p in board_ports:
                print(p[1])
                if "XIAO" in p[1]:
                    board_port = p[0]
                    self.console.append("Connecting to board on port:", board_port)
                    ser = serial.Serial(board_port, baudrate, timeout=1)
                    return ser
            self.console.append("Couldn't find board.")
            # sys.exit(1)
        elif platform.system() == "Windows":
            for p in board_ports:
                print(p[2])
                if "2886" in p[2]:
                    board_port = p[0]
                    self.console.append("Connecting to board on port:", board_port)
                    ser = serial.Serial(board_port, baudrate, timeout=1)
                    return ser
            self.console.append("Couldn't find board port.")
            # sys.exit(1)
        else:
            self.console.append("Unsupported platform")
            # sys.exit(1)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    channels = 5
    ecgapp = App(channels)
    sys.exit(app.exec_())
