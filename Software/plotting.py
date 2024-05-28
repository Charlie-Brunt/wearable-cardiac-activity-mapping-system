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


def save_plot(y, ylims=(-1500,1500), xlims=(0)):
    x = np.arange(0, len(y)/250, 1/250)

    plt.plot(x, y , label="raw", linewidth=1)
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

def save_subplots(y, ylims=(-1500,1500), xlims=(0)):
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

def save_subplots_spectogram(y, ylims=(-500,-250), xlims=(0)):
    x = np.arange(0, len(y)/250, 1/250)
    y = y - np.mean(y) # offset removal
    y = y/256 * 3.3 / 1100 * 1000000
    y = signal.filtfilt(*signal.bessel(6, (0.5, 100), btype="bandpass", fs=250), y)

    f, t, Sxx = signal.spectrogram(y, fs=250, nperseg=1024, noverlap=1024/16, nfft=2048, scaling="density")
    logged_Sxx = 20*np.log10(Sxx)

    fig, axs = plt.subplots(2, 1, sharex=True)
    axs[0].plot(x, y , label="raw", linewidth=1, color="#708fff")
    axs[1].pcolormesh(t, f, logged_Sxx, shading='gouraud')

    axs[0].set_xlim(xlims)
    axs[0].set_ylim(ylims)
    axs[0].set_ylabel("uV")
    axs[1].set_xlabel("Time (s)")
    axs[1].set_ylabel("Frequency (Hz)")

    fig.suptitle("Signal and Spectogram")
    fig.legend()
    fig.tight_layout()

    filename = "signal processing " + str(datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"))
    path = os.getcwd() + "/Software/Plots/"
    plt.savefig(path+filename+".png", bbox_inches='tight')
    # plt.show()

def save_plot_channels(df, title, ylims=(-1000,1000), xlims=(0)):
    x = np.arange(0, len(df)/250, 1/250)
    channels = []
    for i in range(1, len(df.columns)):

        y = (df["Channel_"+str(i)] / 256) * 3.3 / 1100 * 1000000
        y = y - np.mean(y) # offset removal
        filtered_y0 = signal.filtfilt(*signal.bessel(6, (0.5, 40), btype="bandpass", fs=250), y)
        channels.append(filtered_y0)

    colors = ["#ff5e5e", "#ff5790", "#e964c1", "#bb7ae8", "#708fff"]
    fig, axs = plt.subplots(len(df.columns) - 1, 1, sharex=True, sharey=True)
    if len(df.columns) == 2:
        axs = [axs]
    for i, y in enumerate(channels):
        axs[i].plot(x, y , label="Channel "+str(df.columns[i][-1]), linewidth=1, color=colors[i])
        axs[i].set_xlim(xlims)
        axs[i].set_ylim(ylims)

    axs[-1].set_xlabel("Time (s)")
    axs[2].set_ylabel("Amplitude uV")
    fig.suptitle(title)
    fig.legend(loc="lower right", ncol=5, fontsize="8")
    fig.tight_layout()
    # plt.subplots_adjust(hspace=0.3)

    filename = title + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    path = os.getcwd() + "/Software/Plots/"
    plt.savefig(path+filename+".png", bbox_inches='tight')
    # plt.show()

def save_plot_channels2(df, title, ylims=(-1000,1000), xlims=(0), channels=[1,2,3,4,5]):
    x = np.arange(0, len(df)/250, 1/250)
    channel_data = []
    for i in channels:
        y = (df["Channel_"+str(i)] / 256) * 3.3 / 1100 * 1000000
        y = y - np.mean(y) # offset removal
        filtered_y0 = signal.filtfilt(*signal.butter(6, (1.5, 40), btype="bandpass", fs=250), y)
        channel_data.append(filtered_y0)

    colors = ["#ff5e5e", "#ff5790", "#e964c1", "#bb7ae8", "#708fff"]
    fig, axs = plt.subplots(len(channels), 1, sharex=True, sharey=True)
    if len(channels) == 1:
        axs = [axs]
    for i, y in enumerate(channel_data):
        axs[i].plot(x, y , label="Channel "+ str(channels[i]), linewidth=1, color=colors[i])
        axs[i].set_xlim(xlims)
        axs[i].set_ylim(ylims)
        axs[i].set_ylabel("Amplitude uV")


    axs[-1].set_xlabel("Time (s)")
    fig.suptitle(title)
    fig.legend(loc="lower right", ncol=5, fontsize="8")
    fig.tight_layout()
    # plt.subplots_adjust(hspace=0.3)

    filename = title + str(datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"))
    path = os.getcwd() + "/Software/Plots/"
    plt.savefig(path+filename+".png", bbox_inches='tight')
    # plt.show()

def pan_tompkins(data, fs):
    # Pan-Tompkins Algorithm
    # Step 1: Bandpass filter
    # Step 2: Derivative
    diff_y = np.diff(data)
    # Step 3: Squaring
    squared_y = diff_y**2
    # Step 4: Moving Window Integration
    mw_y = movingaverage(squared_y, n=int(0.150*fs))
    # Step 5: Find R-peaks
    peaks, _ = signal.find_peaks(mw_y, height=0.1*np.max(mw_y))
    return peaks

def SNR(data, analysis_interval, threshold=250):
    data = data / 256 * 3.3 / 1100 * 1000000
    # data = data - np.mean(data)
    filtered_data = signal.filtfilt(*signal.butter(6, (0.5, 40), btype="bandpass", fs=250), data)

    t = np.arange(0, len(data)/250, 1/250)
    indices = np.where((t >= analysis_interval[0]) & (t <= analysis_interval[1]))
    y = filtered_data[indices]

    fig, axs = plt.subplots(2, 1)

    peaks = signal.find_peaks(y, height=threshold)[0]
    noise = y.copy()
    for peak in peaks:
        noise[peak - 12 : peak + 12] = 0
    noise = signal.filtfilt(*signal.butter(6, (10, 100), btype="bandpass", fs=250), noise)

    y = y - noise
    signal_power = np.mean(y**2)
    noise_power = np.mean(noise**2)

    axs[0].plot(t[indices], y, label="Signal", linewidth=1, color="#708fff")
    axs[0].plot(t[indices], noise, label="Noise", linewidth=1, color="#ff5e5e")
    axs[0].scatter(t[indices][peaks], y[peaks], color="red", label="R-peaks", s=10)
    axs[0].set_ylabel("Amplitude (uV)")
    axs[0].set_title("Signal and R-peaks")
    axs[0].legend()
    axs[1].hist(noise, bins=100, color="blue", alpha=0.5)
    axs[1].set_xlabel("Amplitude (uV)")
    axs[1].set_ylabel("Frequency")
    axs[1].set_title("Noise Distribution")
    axs[0].set_xlim(analysis_interval)
    fig.tight_layout()
    filename = "SNR" + str(datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"))
    path = os.getcwd() + "/Software/Plots/"
    plt.savefig(path+filename+".png", bbox_inches='tight')

    SNR = 10*np.log10(signal_power/noise_power)
    return SNR


def SNR_emg(data, analysis_interval):
    data = data / 256 * 3.3 / 1100 * 1000000
    # data = data - np.mean(data)
    filtered_data = signal.filtfilt(*signal.butter(6, (0.5, 40), btype="bandpass", fs=250), data)

    t = np.arange(0, len(data)/250, 1/250)
    indices = np.where((t >= analysis_interval[0]) & (t <= analysis_interval[1]))
    y = filtered_data[indices]

    fig, axs = plt.subplots(2, 1)

    # peaks = signal.find_peaks(y, height=threshold)[0]
    noise = y.copy()
    # for peak in peaks:
    #     noise[peak - 12 : peak + 12] = 0
    noise = signal.filtfilt(*signal.butter(6, (10, 100), btype="bandpass", fs=250), noise)
    y = y - noise
    signal_power = np.mean(y**2)
    noise_power = np.mean(noise**2)

    axs[0].plot(t[indices], y, label="Signal", linewidth=1, color="#708fff")
    axs[0].plot(t[indices], noise, label="Noise", linewidth=1, color="#ff5e5e")
    # axs[0].scatter(t[indices][peaks], y[peaks], color="red", label="R-peaks", s=10)
    axs[0].set_ylabel("Amplitude (uV)")
    axs[0].set_title("Signal and R-peaks")
    axs[0].legend()
    axs[1].hist(noise, bins=100, color="blue", alpha=0.5)
    axs[1].set_xlabel("Amplitude (uV)")
    axs[1].set_ylabel("Frequency")
    axs[1].set_title("Noise Distribution")
    axs[0].set_xlim(analysis_interval)
    fig.tight_layout()
    filename = "SNR" + str(datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"))
    path = os.getcwd() + "/Software/Plots/"
    plt.savefig(path+filename+".png", bbox_inches='tight')

    SNR = 10*np.log10(signal_power/noise_power)
    return SNR


if __name__ == "__main__":
    sns.set_theme()
    plt.rcParams['figure.figsize'] = [15, 8]
    plt.rcParams['figure.dpi'] = 200
    sns.set_style("whitegrid")
    plt.rc('xtick', labelsize=7) 
    plt.rc('ytick', labelsize=7) 

    path = os.getcwd() + "/Data/"
    files = os.listdir(path)

    filename = "ecg agcl.csv"
    df = pd.read_csv(path+filename)
    # save_plot_channels2(df, title="Two-Channel EMG (Wrist Flexion) - Eutectogel", xlims=(15, 20), ylims=(-1000, 1000), channels=[2,4])
    # save_plot_channels2(df, title="Ag-AgCl Benchmark", xlims=(0, 5), ylims=(-250, 500), channels=[1])
    save_subplots_spectogram(df["Channel_1"], xlims=(2, 60), ylims=(-250, 500))

    # snr = SNR(df["Channel_2"], (0, 7), threshold=400)
    # snr = SNR_emg(df["Channel_2"], (50, 54))
    # snr = SNR_emg(df["Channel_2"], (15, 20))

    # print(snr)
    