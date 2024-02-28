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
import qdarkstyle


class SerialThread(QThread):
    """
    Thread for reading data from the serial port.
    """

    data_received = pyqtSignal(np.ndarray)

    def __init__(self, ser, buffers, channels, parent=None):
        """
        Constructor for SerialThread class.

        Args:
            ser (serial.Serial): Serial object for communication with the board.
            buffers (list): List of ring buffers for data storage.
            channels (int): Number of channels.
            parent: Parent widget.
        """
        super(SerialThread, self).__init__(parent)
        self.ser = ser
        self.buffers = buffers
        self.running = True
        self.count = 0

    def run(self):
        """Run method for the thread."""
        while self.running:
            self.count += 1
            data = self.receive_data()
            for i in range(len(self.buffers)):
                try:
                    self.buffers[i].extend([data[i]])
                except:
                    pass
            if self.count == 1:  # set fps
                self.count = 0
                to_send = np.array([np.array(buffer) for buffer in self.buffers])
                self.data_received.emit(to_send)

    def receive_data(self):
        """
        Read data from the serial port.

        Returns:
            np.ndarray: Data read from the serial port.
        """
        try:
            if self.ser.isOpen():
                bytes = self.ser.readline().strip()
                decoded_data = np.frombuffer(bytes, dtype=np.int8)
                return decoded_data
            else:
                print("Could not open serial port.")
                return None
        except serial.SerialException as e:
            print(f"Serial port error: {e}")
            sys.exit(1)

    def stop(self):
        """Stop the thread."""
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
            demo_mode (bool): Flag indicating whether the application is in demo mode.
        """
        super(App, self).__init__(parent)

        # Test mode
        self.demo_mode = demo_mode

        # Initialise parameters for data acquisition
        self.sampling_rate = 200  # Hz
        self.buffer_size = 2 * self.sampling_rate  # 2 second window
        self.channels = channels
        self.baudrate = 115200
        self.calls = 0  # fps counter variable

        # Create ring buffers for data storage
        self.buffers = [RingBuffer(capacity=self.buffer_size, dtype=np.uint8) for _ in range(self.channels)]

        # Set up dataframe for recording
        self.dataframe = pd.DataFrame(columns=['Timestamp'] + [f'Channel_{i+1}' for i in range(self.channels)])

        # Initialise the application window
        self.setWindowTitle("BSPM Monitor")  # Set the window title
        self.setupUi()
        self.showMaximized()
        self.console.append(self.get_timestamp() + "Initialising...")

        # Connect to board
        if not demo_mode:
            self.console.append(self.get_timestamp() + "Searching for board...")
            QTimer.singleShot(1000, self.delayed_init)
        else:
            self.console.append(self.get_timestamp() + "Demo mode")
            self.demo_update()

    def delayed_init(self):
        """Delayed initialisation after the window is shown."""
        self.ser = self.connect_to_board()
        self.serial_thread = SerialThread(self.ser, self.buffers, self.channels)
        self.serial_thread.data_received.connect(self.update_plots)

    def setupUi(self):
        """Set up user interface."""
        # Create the main layout
        self.mainbox = QWidget()
        self.setCentralWidget(self.mainbox)
        self.layout = QHBoxLayout(self.mainbox)
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
        self.x = np.linspace(0, self.buffer_size/self.sampling_rate, num=self.buffer_size)
        self.counter = 0
        self.fps = 0.
        self.lastupdate = time.time()
        self.started_monitoring = False
        self.update_enabled = False
        self.recording_active = False
        self.render_override = False

        # Create plots, schedule first update
        self.create_plots()

        # Create a widget for controls
        self.controls_widget = QWidget()
        self.controls_layout = QVBoxLayout(self.controls_widget)
        self.layout.addWidget(self.controls_widget)
        self.controls_widget.setMaximumWidth(400)
        self.controls_layout.setAlignment(Qt.AlignTop)

        # Create a console widget
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        font = QtGui.QFont("Courier New", 10)
        self.console.setFont(font)
        self.controls_layout.addWidget(self.console)

        # Create button widgets
        self.buttons_widget = QWidget()
        self.buttons_layout = QHBoxLayout(self.buttons_widget)
        self.controls_layout.addWidget(self.buttons_widget)
        self.buttons_layout.setAlignment(Qt.AlignTop)

        # Add pause button
        self.pause_button = QPushButton("Start Monitoring")
        self.pause_button.setMaximumWidth(120)
        self.pause_button.clicked.connect(self.toggle_update)
        self.buttons_layout.addWidget(self.pause_button)

        # Add a save as png button
        self.save_button = QPushButton("Save as PNG")
        self.save_button.setMaximumWidth(120)
        self.save_button.clicked.connect(self.save_as_png)
        self.buttons_layout.addWidget(self.save_button)
        self.save_button.setEnabled(False)

        # Add record to CSV button
        self.record_button = QPushButton("Record to CSV")
        self.record_button.setMaximumWidth(120)
        self.record_button.clicked.connect(self.toggle_record)
        self.buttons_layout.addWidget(self.record_button)
        self.record_button.setEnabled(False)

        # Info Box
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignBottom | Qt.AlignCenter)
        self.controls_layout.addWidget(self.info_label)
        self.update_info_box()

    def create_plots(self):
        """Create plot widgets."""
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
            plot.setXRange(0, self.buffer_size/self.sampling_rate)
            curve = plot.plot(pen=color)
            self.plots.append((curve, plot))  # Store both the plot and the curve handle
            self.canvas_layout.addWidget(plot)

    def update_plots(self, data):
        """Update plots with new data."""
        if self.update_enabled:
            for i, (curve, plot) in enumerate(self.plots):
                if self.is_plot_visible(plot):
                    curve.setData(self.x[:len(data[i])], data[i])
            self.fps_counter()
        elif self.render_override:
            for i, (curve, plot) in enumerate(self.plots):
                curve.setData(self.x[:len(data[i])], data[i])
            self.render_override = False
        if self.recording_active:
            timestamp = self.get_csv_timestamp()
            data_with_timestamp = [timestamp] + [channel_data[-1] for channel_data in data]
            new_row = pd.Series(data_with_timestamp, index=self.dataframe.columns)
            self.dataframe = self.dataframe._append(new_row, ignore_index=True)
        self.update_info_box()

    def demo_update(self):
        """Update plots and FPS counter in demo mode."""
        if self.update_enabled:
            self.ydata = (np.sin(self.x/3.+ self.counter/9.) + 1) * 127.5
            for curve, plot in self.plots:
                if self.is_plot_visible(plot):
                    curve.setData(self.x, self.ydata)
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
        if not self.update_enabled:
            return True
        scroll_pos = self.scroll.verticalScrollBar().value()
        plot_pos = plot.pos().y()
        return scroll_pos - plot.height() < plot_pos < scroll_pos + self.scroll.viewport().height()

    def toggle_update(self):
        """Toggle update of plots."""
        if not self.started_monitoring:
            if self.demo_mode:
                self.started_monitoring = True
                self.update_enabled = True
                new_label = "Pause"
                self.pause_button.setText(new_label)
                self.console.append(self.get_timestamp() + "Monitoring started")
            elif self.ser:
                self.started_monitoring = True
                self.record_button.setEnabled(True)
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
                self.render_override = True
                self.save_button.setEnabled(True)

    def toggle_record(self):
        """Toggle recording to CSV file."""
        self.recording_active = not self.recording_active
        new_label = "Save recording" if self.recording_active else "Record to CSV"
        self.record_button.setText(new_label)
        self.console.append(self.get_timestamp() + ("Recording started" if self.recording_active else "Recording stopped"))
        if not self.recording_active:
            self.save_to_csv(self.dataframe)
            self.dataframe = pd.DataFrame(columns=['Timestamp'] + [f'Channel_{i+1}' for i in range(self.channels)])

    def save_to_csv(self, dataframe):
        """Save data to a CSV file."""
        current_datetime = datetime.now()
        datetime_string = current_datetime.strftime("%Y-%m-%d-%H-%M-%S")
        filename = datetime_string + ".csv"
        if filename:
            dataframe.to_csv("Data/"+filename, index=False)
            self.console.append(self.get_timestamp() + f"Data saved as {filename}")

    def save_as_png(self):
        """Save the plot as a PNG file."""
        current_datetime = datetime.now()
        datetime_string = current_datetime.strftime("%Y-%m-%d-%H-%M-%S")
        filename = datetime_string + ".png"
        if filename:
            self.canvas.grab().save("Pictures/"+filename)
            self.console.append(self.get_timestamp() + f"Plot saved as {filename}")

    def fps_counter(self):
        """Calculate and update FPS counter label."""
        self.calls += 1
        now = time.time()
        if self.calls >= 50:
            self.calls = 0
            dt = (now - self.lastupdate)
            self.fps = 50 / dt
            self.lastupdate = now
        tx = 'Frame Rate: {fps:.0f} FPS'.format(fps=self.fps)

    def connect_to_board(self):
        """Connect to the board."""
        board_ports = list(serial.tools.list_ports.comports())
        if platform.system() == "Darwin":
            for p in board_ports:
                if "XIAO" in p[1]:
                    board_port = p[0]
                    self.console.append(self.get_timestamp() + "Connected to board on port: " + board_port)
                    ser = serial.Serial(board_port, self.baudrate, timeout=1)
                    return ser
            self.console.append(self.get_timestamp() + "Couldn't find board")
        elif platform.system() == "Windows":
            for p in board_ports:
                if "2886" in p[2]:
                    board_port = p[0]
                    self.console.append(self.get_timestamp() + "Connected to board on port: " + board_port)
                    ser = serial.Serial(board_port, self.baudrate, timeout=1)
                    return ser
            self.console.append(self.get_timestamp() + "Couldn't find board port")
        else:
            self.console.append(self.get_timestamp() + "Unsupported platform")

    def update_info_box(self):
        """Update information box."""
        current_time = datetime.now().strftime("%H:%M:%S")
        fps_info = f"FPS: {self.fps:.0f}"
        channels_info = f"Channels: {self.channels}"
        sampling_rate_info = f"Sampling Rate: {self.sampling_rate} Hz"
        info_text = f"{current_time} | {fps_info} | {channels_info} | {sampling_rate_info}"
        self.info_label.setText(info_text)

    def get_timestamp(self):
        """Get the current date and time as a string."""
        return datetime.now().strftime("%H:%M:%S") + " "

    def get_csv_timestamp(self):
        """Get the current date and time as a string for use in CSV files."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    channels = 5
    ecgapp = App(channels, demo_mode=False)
    sys.exit(app.exec_())
