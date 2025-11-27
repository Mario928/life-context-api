import librosa
import librosa.display
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


# ======================================================
# 1. Load Audio
# ======================================================

def load_audio(path, target_sr=None):
    y, sr = librosa.load(path, sr=target_sr)
    return y, sr


# ======================================================
# 2. Signal smoothing
# ======================================================

def smooth_signal(y, kernel_size=1024):
    kernel = np.ones(kernel_size) / kernel_size
    y_smooth = np.convolve(y, kernel, mode='same')
    return y_smooth


# ======================================================
# 3. Silence detection via RMS threshold
# ======================================================

def detect_silence(y, sr, threshold_db=-40, frame_length=2048, hop_length=512):
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)

    silent_frames = np.where(rms_db < threshold_db)[0]
    timestamps = librosa.frames_to_time(silent_frames, sr=sr, hop_length=hop_length)

    silent_ranges = []
    if len(timestamps) > 0:
        start = timestamps[0]
        for i in range(1, len(timestamps)):
            if timestamps[i] - timestamps[i - 1] > (hop_length / sr):
                silent_ranges.append((start, timestamps[i - 1]))
                start = timestamps[i]
        silent_ranges.append((start, timestamps[-1]))

    return silent_ranges


# ======================================================
# 4. Loudness analytics
# ======================================================

def loudness_analytics(y, sr, frame_length=2048, hop_length=512):
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)

    return {
        "min_db": float(np.min(rms_db)),
        "max_db": float(np.max(rms_db)),
        "mean_db": float(np.mean(rms_db)),
        "median_db": float(np.median(rms_db)),
        "rms_series_db": rms_db.tolist(),         # <-- store RMS/dB time series
        "rms_series_time": librosa.frames_to_time(np.arange(len(rms_db)), sr=sr).tolist()
    }


# ======================================================
# 5. Spectral analysis
# ======================================================

def spectral_analysis(y, sr):
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    times = librosa.times_like(centroid, sr=sr)

    return {
        "centroid_mean": float(np.mean(centroid)),
        "centroid_std": float(np.std(centroid)),
        "centroid_series": centroid.tolist(),     # <-- spectral centroid series
        "centroid_times": times.tolist()
    }


# ======================================================
# 6. Mel-spectrogram (compressed)
# ======================================================

def mel_spectrogram_compressed(y, sr, n_mels=64, hop_length=512):
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels, hop_length=hop_length)
    mel_db = librosa.power_to_db(mel, ref=np.max)

    # compress → float16 = 50% smaller
    mel_compressed = mel_db.astype(np.float16)

    return {
        "mel_spectrogram_shape": mel_compressed.shape,
        "mel_spectrogram_compressed": mel_compressed.tolist()  # or save as numpy + serialize
    }


# ======================================================
# 7. Plotting dashboard
# ======================================================

def plot_dashboard(y, y_smooth, sr):
    plt.figure(figsize=(15, 12))

    plt.subplot(3, 1, 1)
    librosa.display.waveshow(y, sr=sr, alpha=0.5)
    librosa.display.waveshow(y_smooth, sr=sr, color="orange")
    plt.title("Waveform (Original + Smoothed)")

    plt.subplot(3, 1, 2)
    S = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)
    librosa.display.specshow(S, sr=sr, x_axis='time', y_axis='log')
    plt.title("Log Spectrogram")

    plt.subplot(3, 1, 3)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    times = librosa.times_like(centroid)
    plt.plot(times, centroid, color="green")
    plt.title("Spectral Centroid")

    plt.tight_layout()
    plt.show()


# ======================================================
# 8. FFT computation
# ======================================================

def compute_fft(y, sr):
    N = len(y)
    fft = np.fft.fft(y)
    mag = np.abs(fft)[:N // 2]
    freqs = np.linspace(0, sr / 2, N // 2)
    return freqs, mag


def plot_fft(freqs, mag):
    plt.figure(figsize=(12, 5))
    plt.plot(freqs, mag)
    plt.title("FFT Magnitude Spectrum")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.xlim([0, 8000])
    plt.show()


# ======================================================
# 9. Full Pipeline
# ======================================================

def analyze_audio(path):
    y, sr = load_audio(path)
    y_smooth = smooth_signal(y)

    silence = detect_silence(y, sr)
    loud = loudness_analytics(y, sr)
    spectral = spectral_analysis(y, sr)
    mel = mel_spectrogram_compressed(y, sr)

    # Plots
    plot_dashboard(y, y_smooth, sr)
    freqs, mag = compute_fft(y, sr)
    plot_fft(freqs, mag)

    return {
        "sr": sr,
        "silence_ranges": silence,
        "loudness": loud,
        "spectral": spectral,
        "mel_spectrogram": mel,
    }


# ======================================================
# RUN
# ======================================================

audio_file = "/content/audio.wav"  # <-- CHANGE THIS
results = analyze_audio(audio_file)

print(results.keys())
