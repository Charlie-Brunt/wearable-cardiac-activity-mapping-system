import numpy as np
import matplotlib.pyplot as plt

def generate_ecg_signal(duration, sampling_rate, num_cycles):
    """
    Generate a more realistic approximation of a periodic ECG signal.

    Args:
        duration (float): Duration of each cycle of the signal in seconds.
        sampling_rate (int): Sampling rate of the signal in samples per second.
        num_cycles (int): Number of cycles to generate.

    Returns:
        np.ndarray: Generated periodic ECG signal.
    """
    t_cycle = np.linspace(0, duration, int(duration * sampling_rate), endpoint=False)

    # Define parameters for the ECG signal components
    p_wave_duration = 0.08  # Duration of the P wave in seconds
    qrs_complex_duration = 0.1  # Duration of the QRS complex in seconds
    t_wave_duration = 0.2  # Duration of the T wave in seconds
    baseline_amplitude = 0.2  # Baseline amplitude of the signal
    p_wave_amplitude = 0.1  # Amplitude of the P wave
    qrs_complex_amplitude = 1.0  # Amplitude of the QRS complex
    t_wave_amplitude = 0.3  # Amplitude of the T wave

    # Generate the ECG signal components for one cycle
    p_wave = p_wave_amplitude * np.exp(-((t_cycle - 0.4 * duration) / (p_wave_duration / 2))**2)
    qrs_complex = qrs_complex_amplitude * np.exp(-((t_cycle - 0.5 * duration) / (qrs_complex_duration / 2))**2)
    t_wave = t_wave_amplitude * np.exp(-((t_cycle - 0.7 * duration) / (t_wave_duration / 2))**2)

    # Combine the components to generate the ECG signal for one cycle
    ecg_signal_cycle = baseline_amplitude + p_wave + qrs_complex + t_wave

    # Repeat the cycle to generate the periodic signal
    ecg_signal = np.tile(ecg_signal_cycle, num_cycles)

    # Generate time array for the periodic signal
    t = np.linspace(0, duration * num_cycles, len(ecg_signal), endpoint=False)

    return t, ecg_signal

# Parameters
duration = 10  # Duration of each cycle of the signal in seconds
sampling_rate = 1000  # Sampling rate of the signal in samples per second
num_cycles = 3  # Number of cycles to generate

# Generate periodic ECG signal
t, ecg_signal = generate_ecg_signal(duration, sampling_rate, num_cycles)

# Plot the periodic ECG signal
plt.figure(figsize=(10, 6))
plt.plot(t, ecg_signal, label='ECG Signal')
plt.title('Periodic ECG Signal')
plt.xlabel('Time (s)')
plt.ylabel('Amplitude')
plt.grid(True)
plt.legend()
plt.show()
