"""
ECG Monitor

Author: Charlie Brunt

"""
import sys, os, time, serial, serial.tools.list_ports, customtkinter
import tkinter as tk
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
import seaborn as sns
from numpy_ringbuffer import RingBuffer
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from BlitManager import BlitManager
from PIL import Image, ImageTk


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def connect_to_arduino(baud_rate, serial_number="95530343834351A0B091"):
    """
    Configure the serial port
    """
    for pinfo in serial.tools.list_ports.comports():
        if pinfo.serial_number == serial_number or "Arduino" in pinfo.description:
            return serial.Serial(pinfo.device, baud_rate)
    raise IOError("No Arduino found")


def animate():
    """
    Update plotted data on graphs
    """
    # Update data
    bits = port.read(CHUNK_SIZE//60) # ~ 30 fps
    decoded_bits = np.frombuffer(bits, dtype=np.uint8)
    r.extend(decoded_bits)
    data = np.array(r) # np.frombuffer(bit_data, dtype=np.uint8)
    data = (data - np.average(data))/128 # remove DC offset and normalise
    line1.set_ydata(np.pad(data, (0, CHUNK_SIZE - len(data)))) # Plot waveform

    # Hann window
    windowed_data = np.hanning(len(data)) * data

    global timer
    temp = time.time()
    fr_number.set_text("FPS: {:.1f}".format(1.0 / (temp - timer)))
    timer = temp

    # Update the canvas
    bm.update()

    # Schedule the next update
    root.after(1, animate)


def close_window():
    """
    Callback function to stop executing code when closing a window
    """
    # root.destroy()
    sys.exit()


if __name__== "__main__":
    # Set font family globally
    font_manager._load_fontmanager(try_read_cache=False)
    font_name = "Inter"

    # global variables
    timer = 0

    # Parameters
    CHUNK_SIZE = 32768
    SAMPLING_RATE = 20000
    BAUD_RATE = 1000000

    # Ring buffer object
    r = RingBuffer(capacity=CHUNK_SIZE, dtype=np.uint8)

    times = np.arange(CHUNK_SIZE)/SAMPLING_RATE

    # Create the Tkinter GUI window
    # root = tk.Tk()
    customtkinter.set_appearance_mode("Dark")
    root = customtkinter.CTk()
    root.title("Guitar Companion")
    root.geometry("1600x900")
    root.iconbitmap(resource_path("assets/icon.ico"))
    root.protocol("WM_DELETE_WINDOW", close_window)
    root.configure(background="white")

    # Graph frame
    graph_frame = customtkinter.CTkFrame(master=root, fg_color="#1a1a1a")
    graph_frame.pack(fill=tk.BOTH, side=tk.TOP, padx=8, pady=8, expand=True)

    graph_frame_title = tk.Label(
        master=graph_frame,
        text="Waveform and Power Spectral Density",
        font=(font_name, 10),
        bg="#1a1a1a",
        fg="#5f5f5f"
    )
    graph_frame_title.pack(side=tk.TOP, anchor=tk.NW, padx=10, pady=5)

    # Create a Figure object
    fig = plt.figure()
    fig.patch.set_facecolor('.1')

    # Seaborn styles
    sns.set_style("dark", {
        'axes.grid': True,
        'grid.linestyle': '-',
        'grid.color': '0.3',
        'text.color': 'white',
        'xtick.color': 'white',
        'ytick.color': 'white',
        'axes.labelcolor': 'white',
        }
    )

    plt.rcParams["font.family"] = font_name

    # Font dictionary
    font = {
        'family': font_name,
        'color':  'white',
        'weight': 'normal',
        'size': 8
    }

    # Time domain plot setup
    ax1 = fig.add_subplot(2, 1, 1)
    line1, = ax1.plot(times, np.zeros(CHUNK_SIZE), "red")
    ax1.patch.set_alpha(0)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Amplitude')
    ax1.set_xlim(0, 0.125*CHUNK_SIZE/SAMPLING_RATE)
    ax1.set_ylim(-1,1)
    ax1.grid(axis="x")
    fr_number = ax1.text(0.001, 0.938, '', va='top', ha='left', fontdict=font)

    animated_artists = [line1, fr_number]

    # Create a canvas widget to display the plot
    canvas = FigureCanvasTkAgg(fig, master=graph_frame)
    canvas.get_tk_widget().pack(side="top",fill='both', expand=True, padx=10, pady=10)

    # Create BlitManager object
    bm = BlitManager(canvas, animated_artists)

    # Open Arduino COM port
    # port = connect_to_arduino(BAUD_RATE)

    canvas.draw()

    # Schedule the first update
    root.after(1, animate)

    # Run the Tkinter event loop
    root.mainloop()
