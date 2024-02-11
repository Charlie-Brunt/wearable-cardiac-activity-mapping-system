import sys
import time
from pyqtgraph.Qt import Qtcore, QtGui
import numpy as np
import pyqtgraph as pg

class App(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(App, self).__init__(parent)
        