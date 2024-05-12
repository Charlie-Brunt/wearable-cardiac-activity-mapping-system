from scipy import signal
import numpy as np
import matplotlib.pyplot as plt


t = np.linspace(0, 1, 100)  # 1 second
f = 3 # 3 Hz
array = np.sin(2*f*np.pi*t) + np.sin(2*50*f*np.pi*t)

# Filter the data
b, a = signal.iirnotch(50.0, 20, 100.0)

filtered_data = signal.filtfilt(b, a, array)

# Plot the data
# plt.plot(array)
plt.plot(filtered_data)
plt.show()

