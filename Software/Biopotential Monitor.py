import sys
import time
import platform
import serial
import csv
import os
import serial.tools.list_ports
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime
from numpy_ringbuffer import RingBuffer
import numpy as np
import pyqtgraph as pg
import pandas as pd
import qdarkstyle
import scipy.signal as signal


class SerialThread(QThread):
    """
    Thread for reading data from the serial port.
    """

    data_received = pyqtSignal(np.ndarray)

    def __init__(self, ser, buffers, channels, sampling_rate, parent=None):
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
        
        self.notch_applied = False
        self.b_notch = None
        self.a_notch = None

        self.lpf_applied = False
        self.b_lpf = None
        self.a_lpf = None

        self.hpf_applied = False
        self.b_hpf = None
        self.a_hpf = None

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
            if self.count == 1:  # how often to update plots upon receiving data (sets fps)
                self.count = 0
                try:
                    arrays = np.array([np.array(buffer) for buffer in self.buffers]) # convert ring buffers to numpy arrays
                    to_send = self.digital_filtering(arrays)
                    self.data_received.emit(to_send)
                except:
                    pass

    def digital_filtering(self, data):
        """Apply digital filters to the data."""
        if self.notch_applied:
            data = np.array([signal.lfilter(self.b_notch, self.a_notch, np.array(buffer)) for buffer in data])
        if self.lpf_applied:
            data = np.array([signal.lfilter(self.b_lpf, self.a_lpf, np.array(buffer)) for buffer in data])
        if self.hpf_applied:
            data = np.array([signal.lfilter(self.b_hpf, self.a_hpf, np.array(buffer)) for buffer in data])
        return data

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

    def __init__(self, channels: int, baudrate=1000000, demo_mode=False, sampling_rate=250):
        """
        Constructor for App class.

        Args:
            channels (int): Number of plots to display.
            parent: Parent widget.
            demo_mode (bool): Flag indicating whether the application is in demo mode.
        """
        super(App, self).__init__()

        # Test mode
        self.demo_mode = demo_mode

        # Initialise parameters for data acquisition
        self.sampling_rate = sampling_rate  # Hz
        self.buffer_size = 4 * self.sampling_rate  # 4 second window
        self.channels = channels
        self.baudrate = baudrate
        self.calls = 0  # fps counter variable

        # Create ring buffers for data storage
        self.buffers = [RingBuffer(capacity=self.buffer_size, dtype=np.uint8) for _ in range(self.channels)]

        # Set up dataframe for recording
        self.dataframe = pd.DataFrame(columns=['Timestamp'] + [f'Channel_{i+1}' for i in range(self.channels)])

        # Initialise the application window
        self.setWindowTitle("Biopotential Monitor")  # Set the window title
        self.setupUi()
        self.showMaximized()
        self.console.append(self.get_timestamp() + "Initialising...")

        # Connect to board
        if not demo_mode:
            self.console.append(self.get_timestamp() + "Searching for board...")
            QTimer.singleShot(1000, self.initialise_serial)
        else:
            self.console.append(self.get_timestamp() + "Demo mode")
            self.demo_update()

    def initialise_serial(self):
        """Delayed initialisation after the window is shown."""
        # Connect to the board
        self.ser = self.connect_to_board()

        # Create a serial thread for reading data from the board
        self.serial_thread = SerialThread(self.ser, self.buffers, self.channels, self.sampling_rate)

        # Connect the data received signal to the update plots method
        self.serial_thread.data_received.connect(self.update_plots)

        # self.ser.write(self.channels.to_bytes(1, byteorder='big'))  # Tell the board how many channels to expect

    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

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
        self.t = np.linspace(-self.buffer_size/self.sampling_rate, 0, num=self.buffer_size)
        self.counter = 0
        self.fps = 0.
        self.lastupdate = time.time()

        # Initialize flags
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
        self.controls_layout.setSpacing(5)  # Adjust the spacing here

        # Create a console widget
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.console.setFont(font)
        self.controls_layout.addWidget(self.console)

        # Create an hpf widget
        self.hpf_widget = QWidget()
        self.hpf_layout = QHBoxLayout(self.hpf_widget)
        self.controls_layout.addWidget(self.hpf_widget)
        self.hpf_layout.setAlignment(Qt.AlignTop)

        # Add a high pass filter button
        self.hpf_button = QPushButton("")
        self.hpf_button.setIcon(QIcon(self.resource_path("assets/hpf.png")))
        self.hpf_button.setMaximumWidth(60)
        self.hpf_button.setEnabled(False)
        self.hpf_button.setIconSize(QSize(50, 38))
        self.hpf_button.setCheckable(True)
        self.hpf_button.clicked.connect(self.apply_high_pass_filter)
        self.hpf_layout.addWidget(self.hpf_button)

        # Add high pass filter frequency input label
        self.hpf_freq_input_label = QLabel("Frequency (Hz):")
        self.hpf_layout.addWidget(self.hpf_freq_input_label)

        # Add high pass filter frequency input
        self.hpf_freq_input = QLineEdit()
        self.hpf_freq_input.setText("0.5")
        self.hpf_freq_input.setMaximumWidth(120)
        self.hpf_layout.addWidget(self.hpf_freq_input)

        # Create an lpf widget
        self.lpf_widget = QWidget()
        self.lpf_layout = QHBoxLayout(self.lpf_widget)
        self.controls_layout.addWidget(self.lpf_widget)
        self.lpf_layout.setAlignment(Qt.AlignTop)

        # Add a low pass filter button
        self.lpf_button = QPushButton("")
        self.lpf_button.setIcon(QIcon(self.resource_path("assets/lpf.png")))
        self.lpf_button.setMaximumWidth(60)
        self.lpf_button.setEnabled(False)
        self.lpf_button.setIconSize(QSize(50, 38))
        self.lpf_button.setCheckable(True)
        self.lpf_button.clicked.connect(self.apply_low_pass_filter)
        self.lpf_layout.addWidget(self.lpf_button)

        # Add low pass filter frequency input label
        self.lpf_freq_input_label = QLabel("Frequency (Hz):")
        self.lpf_layout.addWidget(self.lpf_freq_input_label)

        # Add low pass filter frequency input
        self.lpf_freq_input = QLineEdit()
        self.lpf_freq_input.setText("40.0")
        self.lpf_freq_input.setMaximumWidth(120)
        self.lpf_layout.addWidget(self.lpf_freq_input)

        # Add a notch filter widget
        self.notch_widget = QWidget()
        self.notch_layout = QHBoxLayout(self.notch_widget)
        self.controls_layout.addWidget(self.notch_widget)
        self.notch_layout.setAlignment(Qt.AlignTop)

        # Add a notch filter button
        self.notch_button = QPushButton("")
        self.notch_button.setIcon(QIcon(self.resource_path("assets/notch.png")))
        self.notch_button.setMaximumWidth(60)
        self.notch_button.setEnabled(False)
        self.notch_button.setIconSize(QSize(50, 38))
        self.notch_button.setCheckable(True)
        self.notch_button.clicked.connect(self.apply_notch_filter)
        self.notch_layout.addWidget(self.notch_button)

        # Add notch filter frequency input label
        self.notch_freq_input_label = QLabel("Frequency (Hz):")
        self.notch_layout.addWidget(self.notch_freq_input_label)

        # Add notch filter frequency input
        self.notch_freq_input = QLineEdit()
        self.notch_freq_input.setText("50.0")
        self.notch_freq_input.setMaximumWidth(120)
        self.notch_layout.addWidget(self.notch_freq_input)

        # Add notch filter quality factor input label
        self.notch_qf_input_label = QLabel("Q:")
        self.notch_layout.addWidget(self.notch_qf_input_label)

        # Add notch filter quality factor input
        self.notch_qf_input = QLineEdit()
        self.notch_qf_input.setText("3.0")
        self.notch_qf_input.setMaximumWidth(120)
        self.notch_layout.addWidget(self.notch_qf_input)

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
        """Creates a plot widget for each channel and adds it to the scroll area."""

        # Style the plots
        cmap = pg.ColorMap([0, self.channels-1], [pg.mkColor('#729ece'), pg.mkColor('#ff9e4a')])
        font = QFont()
        font.setPixelSize(10)

        # Create a plot for each channel
        self.plots = []
        for i in range(self.channels):
            color = cmap.map(i)
            plot = pg.PlotWidget()
            plot.setLabel("left", f"Channel {i+1}")
            plot.getAxis("bottom").setStyle(tickFont=font)
            plot.getAxis("left").setStyle(tickFont=font)
            plot.setMinimumHeight(120)
            plot.setYRange(0, 255)
            plot.setXRange(-self.buffer_size/self.sampling_rate + 1, 0)
            curve = plot.plot(pen=color)
            self.plots.append((curve, plot))  # Store both the plot and the curve handle
            self.canvas_layout.addWidget(plot)

    def update_plots(self, data):
        """ 
        Update plots with new data.

        Checks if the plot update flag is enabled and the plot is visible in the scroll area.
        If the plot is not visible, the data is not updated. This is done to reduce the computational 
        load when many plots are used. The data is still stored in the ring buffers and is consequently 
        available for saving to CSV. The render override flag renders all plots when the update flag is 
        disabled to allow saving of plots as a PNG. Recording data to CSV is possible even when the plot 
        update flag is disabled.
        """
        if self.update_enabled:
            for i, (curve, plot) in enumerate(self.plots):
                if self.is_plot_visible(plot):
                    curve.setData(self.t[:len(data[i])], data[i])
            self.fps_counter()
        elif self.render_override:
            for i, (curve, plot) in enumerate(self.plots):
                curve.setData(self.t[:len(data[i])], data[i])
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
            self.ydata = (np.sin(5*(self.t/3.+ self.counter/9.)) + 1) * 127.5
            for curve, plot in self.plots:
                if self.is_plot_visible(plot):
                    curve.setData(self.t, self.ydata)
            self.counter += 1
        self.fps_counter()
        QTimer.singleShot(10, self.demo_update)

    def is_plot_visible(self, plot):
        """
        Check if the plot is visible in the scroll area.

        Args:
            plot (pg.PlotWidget): Plot widget.

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
        if not self.started_monitoring: # check for first time monitoring
            if self.demo_mode:
                self.started_monitoring = True
                self.update_enabled = True
                new_label = "Pause"
                self.pause_button.setText(new_label)
                self.console.append(self.get_timestamp() + "Monitoring started")
            elif self.ser: # Check if the serial object was created successfully
                self.ser.flushInput() # Clear the input buffer
                self.started_monitoring = True # Start monitoring
                self.record_button.setEnabled(True)
                self.notch_button.setEnabled(True)
                self.lpf_button.setEnabled(True)
                self.hpf_button.setEnabled(True)
                self.update_enabled = True # Start updating the plots
                new_label = "Pause"
                self.pause_button.setText(new_label)
                self.console.append(self.get_timestamp() + "Monitoring started")
                self.serial_thread.start()
            else: # If the serial object was not created, try again
                self.console.append(self.get_timestamp() + "Attempting to connect to board...")
                QTimer.singleShot(1000, self.initialise_serial) # Try to connect to the board
        else: # If monitoring has already started, toggle update state: pause/resume
            self.update_enabled = not self.update_enabled
            new_label = "Resume" if not self.update_enabled else "Pause"
            self.pause_button.setText(new_label)
            self.console.append(self.get_timestamp() + ("Monitoring paused" if not self.update_enabled else "Monitoring resumed"))
            if self.update_enabled:
                self.save_button.setEnabled(False)
            else:
                self.render_override = True # renders all plots on next update regardless of visibility to allow png saving
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

        # Update the FPS counter every 50 frames
        if self.calls >= 50:
            self.calls = 0
            dt = (now - self.lastupdate)
            self.fps = 50 / dt
            self.lastupdate = now
        tx = 'Frame Rate: {fps:.0f} FPS'.format(fps=self.fps)

    def connect_to_board(self):
        """Connect to the board automatically on Windows/Mac."""
        board_ports = list(serial.tools.list_ports.comports())
        if platform.system() == "Darwin":
            for p in board_ports:
                if "XIAO" in p[1]: # and "1101" in p[0]:
                    board_port = p[0]
                    self.console.append(self.get_timestamp() + "Connected to board on port: " + board_port)
                    self.pause_button.setText("Start Monitoring")
                    ser = serial.Serial(board_port, self.baudrate, timeout=1)
                    return ser
            self.console.append(self.get_timestamp() + "Couldn't find board")
            self.pause_button.setText("Connect to Board")
        elif platform.system() == "Windows":
            for p in board_ports:
                if "2886" in p[2]:
                    board_port = p[0]
                    self.console.append(self.get_timestamp() + "Connected to board on port: " + board_port)
                    self.pause_button.setText("Start Monitoring")
                    ser = serial.Serial(board_port, self.baudrate, timeout=1)
                    return ser
            self.console.append(self.get_timestamp() + "Couldn't find board port")
            self.pause_button.setText("Connect to Board")
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

    def apply_notch_filter(self):
        """Apply a notch filter to the data."""
        if not self.serial_thread.notch_applied:
            self.console.append(self.get_timestamp() + "Applying notch filter")

            quality_factor = float(self.notch_qf_input.text())
            notch_freq = float(self.notch_freq_input.text())
            b, a = signal.iirnotch(notch_freq, quality_factor, float(self.sampling_rate))
            self.serial_thread.b_notch = b
            self.serial_thread.a_notch = a
            self.serial_thread.notch_applied = True
            self.notch_freq_input.setDisabled(True)
            self.notch_qf_input.setDisabled(True)
        else:
            self.console.append(self.get_timestamp() + "Notch filter removed")
            self.serial_thread.notch_applied = False
            self.notch_freq_input.setDisabled(False)
            self.notch_qf_input.setDisabled(False)

    def apply_low_pass_filter(self):
        """Apply a notch filter to the data."""
        if not self.serial_thread.lpf_applied:
            self.console.append(self.get_timestamp() + "Applying low-pass filter")
            cutoff_freq = float(self.lpf_freq_input.text())
            filter_order = 4
            b, a = signal.butter(filter_order, cutoff_freq, 'low', fs=float(self.sampling_rate))
            self.serial_thread.b_lpf = b
            self.serial_thread.a_lpf = a
            self.serial_thread.lpf_applied = True
            self.lpf_freq_input.setDisabled(True)
        else:
            self.console.append(self.get_timestamp() + "Low-pass filter removed")
            self.serial_thread.lpf_applied = False
            self.lpf_freq_input.setDisabled(False)

    def apply_high_pass_filter(self):
        """Apply a high pass filter to the data."""
        if not self.serial_thread.hpf_applied:
            self.console.append(self.get_timestamp() + "Applying high-pass filter")
            cutoff_freq = float(self.hpf_freq_input.text())
            filter_order = 4
            b, a = signal.butter(filter_order, cutoff_freq, 'high', fs=float(self.sampling_rate))
            self.serial_thread.b_hpf = b
            self.serial_thread.a_hpf = a
            self.serial_thread.hpf_applied = True
            self.hpf_freq_input.setDisabled(True)
        else:
            self.console.append(self.get_timestamp() + "High-pass filter removed")
            self.serial_thread.hpf_applied = False
            self.hpf_freq_input.setDisabled(False)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    ecgapp = App(channels=1, baudrate=1000000, demo_mode=False, sampling_rate=250)
    sys.exit(app.exec_())