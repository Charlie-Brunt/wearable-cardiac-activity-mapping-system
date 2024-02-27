import sys
import time
import platform
import serial
import csv
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QScrollArea, QApplication,
    QHBoxLayout, QVBoxLayout, QMainWindow, QTextEdit, QSizePolicy
)
from PyQt5.QtCore import QTimer, QTime, Qt, QThread, pyqtSignal
from PyQt5 import QtGui
from datetime import datetime
from numpy_ringbuffer import RingBuffer
import numpy as np
import pyqtgraph as pg
import pandas as pd

class SerialThread(QThread):
    """
    Thread for reading data from the serial port.
    """
    data_received = pyqtSignal(np.ndarray)

    def __init__(self, ser, buffers, update_size, channels, parent=None):
        super(SerialThread, self).__init__(parent)
        self.ser = ser
        self.buffers = buffers
        self.update_size = update_size
        self.running = True

    def run(self):
        while self.running:
            data = self.receive_data()
            if data is not None:

                for i in range(len(self.buffers)):
                    try:
                        self.buffers[i].extend([data[i]])
                        
                    except:
                        pass
            to_send = np.array([np.array(buffer) for buffer in self.buffers])
            self.data_received.emit(to_send)
            # time.sleep(0.01)

    def receive_data(self):
        """
        Read data from a COM port.

        Returns:
            np.ndarray: Data read from the COM port.
        """
        try:
            if self.ser.isOpen():
                bytes = self.ser.readline().strip()
                # print(bytes)
                decoded_data = np.frombuffer(bytes, dtype=np.int8)
                # print(decoded_data)
                return decoded_data
            else:
                print("Could not open serial port.")
                return None
        except serial.SerialException as e:
            print(f"Serial port error: {e}")
            sys.exit(1)

    def stop(self):
        self.running = False


class App(QMainWindow):
    """
    Main application class for BSPM Monitor.
    """

    def __init__(self, channels: int, parent=None, demo_mode=False):
        """
        Constructor for App class.

        Args:
            channels (int): Number of plots to display.
            parent: Parent widget.
        """
        super(App, self).__init__(parent)

        # Test mode
        self.demo_mode = demo_mode

        # Initialise parameters for data acquisition
        self.sampling_rate = 200 # Hz
        self.buffer_size = 2 * self.sampling_rate # 2 second window
        self.update_size = self.buffer_size//100 # sets fps
        self.channels = channels
        self.baudrate = 115200

        # Create a ring buffers for data storag
        self.buffers = [RingBuffer(capacity=self.buffer_size, dtype=np.uint8) for _ in range(self.channels)]

        # Initialise the application window
        self.setWindowTitle("BSPM Monitor")  # Set the window title
        self.setupUi()
        self.show()
        self.console.append(self.get_timestamp() + "Initialising...")

        # Connect to board
        if not demo_mode:
            self.console.append(self.get_timestamp() + "Searching for board...")
            QTimer.singleShot(1000, self.delayed_init)
        else:
            self.console.append(self.get_timestamp() + "Demo mode")
            self.demo_update()
            
    
    def delayed_init(self):
        """
        Delayed initialisation after the window is shown.
        """
        self.ser = self.connect_to_board()
        self.serial_thread = SerialThread(self.ser, self.buffers, self.update_size, self.channels)
        self.serial_thread.data_received.connect(self.update_plots)

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

        # Create plots, schedule first update
        self.create_plots()
        self.showMaximized()

        # Create a widget for controls
        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)
        self.layout.addWidget(self.controls_widget)
        self.controls_widget.setMaximumHeight(100)

        # Create a console widget
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        font = QtGui.QFont("Courier New", 10)
        self.console.setFont(font)
        self.controls_layout.addWidget(self.console)
        self.console.setMaximumWidth(400)

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

        # Create a widget for the clock
        self.clock = QLabel()
        self.controls_layout.addWidget(self.clock)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)  # Update every second
        self.update_clock()
        self.clock.setAlignment(Qt.AlignCenter)

        # Add FPS counter label
        self.fps_label = QLabel()
        self.fps_label.setText("Frame Rate: 0 FPS")
        self.controls_layout.addWidget(self.fps_label)
        self.fps_label.setAlignment(Qt.AlignCenter)

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
            plot.setLabel("left", f"Channel {i+1}")
            plot.getAxis("bottom").setStyle(tickFont=font)
            plot.getAxis("left").setStyle(tickFont=font)
            plot.setMinimumHeight(120)
            plot.setYRange(0, 255)
            plot.setXRange(0, self.buffer_size)
            curve = plot.plot(pen=color)
            self.plots.append((curve, plot))  # Store both the plot and the curve handle
            self.canvas_layout.addWidget(plot)

    def update_plots(self, data):
        if self.update_enabled:
            for i, (curve, plot) in enumerate(self.plots):
                if self.is_plot_visible(plot):
                    # data = data - np.average(data)
                    curve.setData(data[i])
            if self.recording_active:
                pass
            self.fps_counter()
                # self.save_to_csv()

    def demo_update(self):
        """
        Update plots and FPS counter.
        """
        if self.update_enabled:
            self.ydata = (np.sin(self.x/3.+ self.counter/9.) + 1) * 127.5
            for curve, plot in self.plots:
                if self.is_plot_visible(plot):
                    curve.setData(self.ydata)
            self.counter += 1
        self.fps_counter()
        QTimer.singleShot(10, self.demo_update)

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
        if not self.started_monitoring:
            if self.demo_mode:
                self.started_monitoring = True
                self.update_enabled = True
                new_label = "Pause"
                self.pause_button.setText(new_label)
                self.console.append(self.get_timestamp() + "Monitoring started")
            elif self.ser:
                self.started_monitoring = True
                self.update_enabled = True
                new_label = "Pause"
                self.pause_button.setText(new_label)
                self.console.append(self.get_timestamp() + "Monitoring started")
                self.serial_thread.start()
            else:
                self.console.append(self.get_timestamp() + "Attempting to connect to board...")
                QTimer.singleShot(1000, self.delayed_init)
        else:
            self.update_enabled = not self.update_enabled
            new_label = "Resume" if not self.update_enabled else "Pause"
            self.pause_button.setText(new_label)
            self.console.append(self.get_timestamp() + ("Monitoring paused" if not self.update_enabled else "Monitoring resumed"))
            if self.update_enabled:
                self.save_button.setEnabled(False)
            else:
                self.save_button.setEnabled(True)

    def toggle_record(self):
        """
        Toggle recording to CSV file.
        """
        self.recording_active = not self.recording_active
        new_label = "Save recording" if self.recording_active else "Record to CSV"
        self.record_button.setText(new_label)
        self.console.append(self.get_timestamp() + ("Recording started" if self.recording_active else "Recording stopped"))
        if self.recording_active:
            

    def save_as_png(self):
        """
        Save the plot as a PNG file.
        """
        # Get the current date and time
        current_datetime = datetime.now()
        
        # Format the date and time as a string
        datetime_string = current_datetime.strftime("%Y-%m-%d-%H-%M-%S")

        filename = datetime_string + ".png"
        if filename:
            self.canvas.grab().save("Pictures/"+filename)
            self.console.append(self.get_timestamp() + f"Plot saved as {filename}")

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
        tx = 'Frame Rate: {fps:.1f} FPS'.format(fps=self.fps)
        self.fps_label.setText(tx)

    def connect_to_board(self):
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
                # print(p[1])
                if "XIAO" in p[1]:
                    board_port = p[0]
                    self.console.append(self.get_timestamp() + "Connected to board on port: " + board_port)
                    ser = serial.Serial(board_port, self.baudrate, timeout=1)
                    return ser
            self.console.append(self.get_timestamp() + "Couldn't find board")
            # sys.exit(1)
        elif platform.system() == "Windows":
            for p in board_ports:
                # print(p[2])
                if "2886" in p[2]:
                    board_port = p[0]
                    self.console.append(self.get_timestamp() + "Connected to board on port: " + board_port)
                    ser = serial.Serial(board_port, self.baudrate, timeout=1)
                    return ser
            self.console.append(self.get_timestamp() + "Couldn't find board port")
            # sys.exit(1)
        else:
            self.console.append(self.get_timestamp() + "Unsupported platform")
            # sys.exit(1)

    def get_timestamp(self):
        """
        Get the current date and time as a string.

        Returns:
            str: The current date and time formatted as a string.
        """
        return datetime.now().strftime("%H:%M:%S") + " "

    def update_clock(self):
        """
        Update the clock with the current time.
        """
        # Get the current time
        current_time = QTime.currentTime()

        # Format the time as a string
        time_string = current_time.toString("hh:mm:ss")

        # Display the time on the clock LCD
        self.clock.setText(time_string)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    channels = 32
    ecgapp = App(channels, demo_mode=False)
    sys.exit(app.exec_())
