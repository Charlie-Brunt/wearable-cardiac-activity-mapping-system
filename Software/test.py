import sys
import time
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QMainWindow, QScrollArea, QApplication,
                             QLabel)


class Worker(QThread):
    dataUpdated = pyqtSignal(np.ndarray)

    def __init__(self, parent=None):
        super(Worker, self).__init__(parent)
        self.running = False

    def run(self):
        self.running = True
        x = np.linspace(0, 50, num=100)
        counter = 0
        lastupdate = time.time()
        while self.running:
            ydata = np.sin(x / 3. + counter / 9.)
            self.dataUpdated.emit(ydata)
            time.sleep(0.014)  # Adjust the sleep time as needed for your desired update rate
            counter += 1


class App(QMainWindow):
    def __init__(self, num_plots, parent=None):
        super(App, self).__init__(parent)

        self.setWindowTitle("BSPM Monitor")  # Set the window title

        # Create GUI elements
        self.mainbox = QWidget()
        self.setCentralWidget(self.mainbox)
        self.layout = QVBoxLayout(self.mainbox)

        # Scroll area widget
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.layout.addWidget(self.scroll)

        # Canvas widget for plots
        self.canvas = QWidget()
        self.scroll.setWidget(self.canvas)
        self.canvas_layout = QVBoxLayout(self.canvas)

        # Create a widget for FPS counter and Pause button
        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)
        self.layout.addWidget(self.controls_widget)
        self.controls_widget.setMaximumHeight(50)

        # FPS counter label widget
        self.label = QLabel()
        self.controls_layout.addWidget(self.label)

        # Add pause button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setMaximumWidth(80)  # Adjust button width
        self.pause_button.clicked.connect(self.toggle_update)
        self.controls_layout.addWidget(self.pause_button)

        # Initialize data
        self.num_plots = num_plots
        self.worker = Worker()
        self.worker.dataUpdated.connect(self.update_plots)
        self.worker.start()
        self.paused = False
        self.counter = 0
        self.fps = 0
        self.lastupdate = time.time()

        # Create plots
        self.create_plots(num_plots)
        self.showMaximized()  # Maximize the main window

    def create_plots(self, num_plots):
        # Line plots
        self.plots = []
        cmap = pg.ColorMap([0, num_plots - 1], [pg.mkColor('#729ece'), pg.mkColor('#ff9e4a')])
        for i in range(num_plots):
            color = cmap.map(i)
            plot = pg.PlotWidget()
            plot.setLabel("left", f"Plot {i + 1}")
            plot.setMinimumHeight(150)
            h = plot.plot(pen=color)
            self.plots.append(h)
            self.canvas_layout.addWidget(plot)

    def update_plots(self, ydata):
        if not self.paused:
            for plot in self.plots:
                plot.setData(ydata)
            self.fps_counter()

    def toggle_update(self):
        self.paused = not self.paused
        new_label = "Resume" if self.paused else "Pause"
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    num_plots = 16
    ecg_app = App(num_plots)
    ecg_app.show()
    sys.exit(app.exec_())
