import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy import signal
import datetime

def movingaverage(x, n=5):
    x2 = np.pad(x, (int((n-1)/2), int((n-1)/2)))
    y = []
    for i, xi in enumerate(x):
        yi = np.sum(x2[i:i+n])/n
        y.append(yi)
    y2 = np.array(y)
    print(len(y2))
    return y2


def save_plot(y, ylims=(-6000,6000), xlims=(25,55)):
    x = np.arange(0, len(y)/250, 1/250)
    y = y - np.mean(y) # offset removal
    filtered_y0 = signal.filtfilt(*signal.bessel(6, 15, btype="low", fs=250), y)
    filtered_y = signal.filtfilt(*signal.iirnotch(50, 5, 250), filtered_y0)
    rectified_y = np.absolute(filtered_y-np.mean(filtered_y))
    smoothed_y = movingaverage(rectified_y, n=100)

    plt.plot(x, y , label="raw", linewidth=1)
    plt.plot(x, filtered_y + -3000, label="filtered", linewidth=1)
    # plt.plot(x, rectified_y - 1500, label="rectified", linewidth=1)
    # plt.plot(x, smoothed_y - 4500, label="smoothed", linewidth=1)
    filename = "signal processing " + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude (uV)")
    plt.xlim(xlims)
    # plt.ylim(ylims)
    plt.legend(loc="lower left", ncol=4)
    plt.title("Signal Processing")
    path = os.getcwd() + "/Software/Plots/"
    plt.savefig(path+filename+".png", bbox_inches='tight')
    plt.show()

def save_subplots(y, ylims=(-1500,1500), xlims=(25,55)):
    x = np.arange(0, len(y)/250, 1/250)
    y = y - np.mean(y) # offset removal
    filtered_y0 = signal.filtfilt(*signal.bessel(6, 15, btype="low", fs=250), y)
    filtered_y = signal.filtfilt(*signal.iirnotch(45, 5, 250), filtered_y0)
    rectified_y = np.absolute(filtered_y-np.mean(filtered_y))
    smoothed_y = movingaverage(rectified_y, n=100)

    fig, axs = plt.subplots(4, 1, sharex=True, sharey=True)
    axs[0].plot(x, y , label="raw", linewidth=1, color="blue")
    axs[1].plot(x, filtered_y, label="filtered", linewidth=1, color="green")
    axs[2].plot(x, rectified_y, label="rectified", linewidth=1, color="red")
    axs[3].plot(x, smoothed_y, label="smoothed", linewidth=1, color="purple")
    for ax in axs:
        ax.set_xlim(xlims)
        ax.set_ylim(ylims)
        ax.set_ylabel("uV")
    axs[3].set_xlabel("Time (s)")
    fig.suptitle("Signal Processing")
    fig.legend(loc="lower left", ncol=4)
    fig.tight_layout()

    filename = "signal processing " + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    path = os.getcwd() + "/Software/Plots/"
    # plt.savefig(path+filename+".png", bbox_inches='tight')
    plt.show()

def save_subplots_spectogram(y, ylims=(-1500,1500), xlims=(25,55)):
    x = np.arange(0, len(y)/250, 1/250)
    y = y - np.mean(y) # offset removal
    filtered_y0 = signal.filtfilt(*signal.bessel(6, 15, btype="low", fs=250), y)
    filtered_y = signal.filtfilt(*signal.iirnotch(50, 5, 250), filtered_y0)
    rectified_y = np.absolute(filtered_y-np.mean(filtered_y))
    smoothed_y = movingaverage(rectified_y, n=100)

    f, t, Sxx = signal.spectrogram(y, fs=250, window=("hamming"), nperseg=512, noverlap=512//16, nfft=512, scaling="density")
    logged_Sxx = 20*np.log10(Sxx)

    fig, axs = plt.subplots(2, 1, sharex=True)
    axs[0].plot(x, y , label="raw", linewidth=1, color="blue")
    axs[1].pcolormesh(t, f, logged_Sxx, shading='gouraud', cmap="viridis")

    axs[0].set_xlim(xlims)
    axs[0].set_ylim(ylims)
    axs[0].set_ylabel("uV")
    axs[1].set_xlabel("Time (s)")
    axs[1].set_ylabel("Frequency (Hz)")

    fig.suptitle("Signal and Spectogram")
    fig.legend(loc="lower left", ncol=4)
    fig.tight_layout()

    filename = "signal processing " + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    path = os.getcwd() + "/Software/Plots/"
    # plt.savefig(path+filename+".png", bbox_inches='tight')
    plt.show()


if __name__ == "__main__":
    sns.set_theme()
    plt.rcParams['figure.figsize'] = [15,5]
    plt.rcParams['figure.dpi'] = 200
    plt.rcParams["font.family"] = "Arial" 
    sns.set_style("white")

    path = os.getcwd() + "/Data/"
    files = os.listdir(path)

    filename = "emg 2.csv"
    df = pd.read_csv(path+filename)
    y = (df["Channel_1"] / 256) * 3.3 / 1100 * 1000000
    save_subplots_spectogram(y)
    # save_subplots(y)

    