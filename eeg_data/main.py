import eeg_data.face.face as face
from scipy import signal
from scipy.interpolate import interp1d
from scipy.signal import butter, filtfilt, iirdesign, zpk2tf, freqz
from scipy.fftpack import fft
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import numpy as np
import time
import pickle
import os


# [gyro_x, gyro_y, electrodes, sample_numbers, time_ms, time_s]
#     0      1          2             3            4       5

def getdatasets_eeg():
    eeg_input, output = face.get_blink_twice_ds()
    return eeg_input[2], output


def getdatasets_eyes_open():
    eeg_input = face.get_eyes_open_ds()
    return eeg_input[2]


def getdatasets_eyes_closed():
    eeg_input = face.get_eyes_closed_ds()
    return eeg_input[2]


def getdatasets_test_eye_states():
    eeg_input = face.get_eye_states_test_ds()
    return eeg_input


def pickle_freq_data(fft_raw, spectro_raw, csd_raw, timestamp):
    path_to_save = "C:/testeeg/testeeg/eeg_data/freqs/"
    fft_string = timestamp + "-fft.p"
    spectro_string = timestamp + "-spectro.p"
    csd_string = timestamp + "-csd.p"

    try:
        pickle.dump(fft_raw, open(path_to_save + fft_string, "wb"))
        pickle.dump(spectro_raw, open(path_to_save + spectro_string, "wb"))
        pickle.dump(csd_raw, open(path_to_save + csd_string, "wb"))
        return 1
    except:
        return -1


def load_pickled_freq_data():
    path_to_load = "C:/testeeg/testeeg/eeg_data/freqs/"
    freq_files = os.listdir(path_to_load)

    try:
        latest_frequencies = freq_files[0:2]
        for file in latest_frequencies:
            freq_types = file.split("-")

            if freq_types[1] == "fft.p":
                fft_raw = pickle.load(open(path_to_load + file))
            elif freq_types[1] == "spectro.p":
                spectro_raw = pickle.load(open(path_to_load + file))
            elif freq_types[1] == "csd.p":
                csd_raw = pickle.load(open(path_to_load + file))
        return fft_raw, spectro_raw, csd_raw
    except:
        return -1


def streamfft(yf, eeg_data, batch_size):
    plt.grid()
    plt.xlabel("Frequency")
    plt.ylabel("Magnitude (db)")
    #plt.savefig("C:/testeeg/testeeg/mozart/logs/fft.png")


    #plt.ion()
    fft_size = np.shape(yf)
    T = 1 / 128.0
    end_x = (fft_size[1] + batch_size) / 128.0
    xeeg = np.linspace(0.0, end_x, num=(fft_size[1] + batch_size))

    for channel_num in range(0, fft_size[0]):
        print("Streaming channel %d" % (channel_num + 1))
        for batch_num in range(0, fft_size[1]):
            current_batch_fft = np.asarray(yf[channel_num][batch_num])
            current_batch_eeg = np.asarray(eeg_data[channel_num][batch_num])
            xf = np.linspace(0.0, 1.0 / (2.0 * T), batch_size / 2)
            xeeg_batch = xeeg[batch_num: batch_num + 256]
            index_time = xeeg[254 + batch_num]
            #print("plotting @%f seconds" % index_time)
            try:
                plt.ion()
                plt.figure(1)
                plt.clf()
                #plt.title("Plotting channel %d" % channel_num+1)

                plt.subplot(211)
                plt.grid()
                plt.xlabel("Frequency")
                plt.ylabel("Magnitude (db)")
                plt.title("Plotting channel %d at %f seconds" % (channel_num + 1, index_time))
                # plt.savefig("C:/testeeg/testeeg/mozart/logs/fft.png")
                plt.semilogy(xf[0: batch_size / 2], T / batch_size * np.abs(current_batch_fft[0:batch_size / 2]) ** 2)
                plt.ylim([0.00001, 10000])

                plt.subplot(212)
                plt.grid()
                plt.xlabel("Time (s)")
                plt.ylabel("Magnitude (V)")
                plt.title("Plotting channel %d at %f seconds" % (channel_num + 1, index_time))
                plt.ylim([4050, 4500])
                #print(xeeg.__len__(), current_batch_eeg.__len__())

                plt.plot(xeeg_batch, current_batch_eeg)
                plt.pause(0.01)

                plt.show()

            except:
                print("Error streaming graphs")
                continue


def gettimeseriesdata(raw_data_all, batchsize, channel_bottom=5, channel_top=13, load=False):
    timestamp = str(time.time())
    rs_shape = np.shape(raw_data_all)
    if rs_shape[1] < 30:
        raw_data = raw_data_all
    else:
        raw_data = raw_data_all[:, channel_bottom:channel_top]

    raw_data = np.asarray(raw_data)
    raw_data_shape = np.shape(raw_data)

    eeg_ch_data = []

    for channel_num in range(0, raw_data_shape[1]):
        channel_data = raw_data[:, channel_num]
        eeg_data = []
        x_f = 0
        while x_f + batchsize < raw_data_shape[0]:
            # print("\tIndex: %d" % x_f)
            y = channel_data[x_f:x_f + batchsize]
            eeg_data.append(y)  # Append data from all batches in the current channel
            x_f += 1
        eeg_ch_data.append(eeg_data)

    np_eeg = np.asarray(eeg_ch_data)
    return np_eeg


def getfft(raw_data_all, batchsize, print_frequency_graph, channel_bottom=5, channel_top=13, load=False):
    if load is True:
        try:
            fft_raw, spectro_raw, csd_raw = load_pickled_freq_data()
            return fft_raw, spectro_raw, csd_raw
        except:
            pass

    timestamp = str(time.time())

    # Define the channels to get from the 14 channel raw data
    rs_shape = np.shape(raw_data_all)
    if rs_shape[1] < 30:
        raw_data = raw_data_all
    else:
        raw_data = raw_data_all[:, channel_bottom:channel_top]

    raw_data = np.asarray(raw_data)

    # Sampling frequency
    fs = 128.0

    # Time sampling interval in s
    T = 1 / fs

    # Number of samples
    n = rs_shape[0]

    # Get x values
    xf = np.linspace(0.0, 1.0 / (2.0 * T), batchsize / 2)

    fft_channels = []

    plt.grid()
    plt.xlabel("Frequency")
    plt.ylabel("Magnitude (db)")

    plt.savefig("C:/testeeg/testeeg/mozart/logs/fft.png")
    plt.ion()

    # Get fft of each EEG channel by batch size
    for i in range(0, rs_shape[1]):
        fft_data = []
        x_f = 0
        channel_data = raw_data[:, i]

        print("Channel %d starting" % i)
        while x_f + batchsize < n:
            # print("\tIndex: %d" % x_f)
            y = channel_data[x_f:x_f + batchsize]
            yf = fft(y)
            try:
                pass
                # plt.clf()
                # plt.semilogy(xf[0: batchsize / 2], 2.0 / batchsize * np.abs(yf[0:batchsize / 2]))
                # plt.ylim([0.0001, 10000])
                # plt.show()
                # plt.pause(0.01)
            except:
                continue

            fft_data.append(yf)  # Append data from all batches in the current channel
            x_f += 1
            # x_f += (batchsize / 8)

        fft_channels.append(fft_data)  # Append data from all channels together

    np_fft = np.asarray(fft_channels)
    print(np_fft.shape)
    # streamfft(np_fft, T)

    # plt.grid()
    # plt.xlabel("Frequency")
    # plt.ylabel("Magnitude (db)")
    # plt.savefig("C:/testeeg/testeeg/mozart/logs/fft.png")

    if print_frequency_graph:
        plt.show()

    status = pickle_freq_data(fft_channels, 1, 1, timestamp)
    print(status)
    return xf, np_fft, 0, 0


#        spectro_data = plot_spectrogram(raw_data, n, fs, channel_bottom + 1, print_frequency_graph)
#        csd_data = plot_csd(raw_data, n, fs, channel_bottom + 1, print_frequency_graph)



# return xf, fft_data, spectro_data, csd_data


def plot_spectrogram(raw_data, nfft, fs, channel_bottom, print_frequency_graph):
    data_shape = raw_data.shape

    print("Generating spectrogram...")
    plt_num = 1
    plt.clf()
    plt.figure(1)

    channel_data = []
    for i in range(0, data_shape[1]):
        plt.subplot(8, 2, plt_num)

        f, t, Sxx = signal.spectrogram(x=raw_data[:, i], nfft=nfft, fs=fs, noverlap=127, nperseg=128,
                                       scaling='density')  # returns PSD power per Hz
        plt.pcolormesh(t, f, Sxx)

        plt.xlabel('Time (sec)')
        plt.ylabel('Frequency (Hz)')
        plt.title('Channel %s' % (i + channel_bottom))
        plt_num += 1
        channel_data.append([f, t, Sxx])
        print("\tChannel %d spectrogram generated" % i)
    if print_frequency_graph:
        plt.show()
    return channel_data


def plot_csd(raw_data, nfft, fs, channel_bottom, print_frequency_graph):
    data_shape = raw_data.shape
    channel_data = []

    print("Generating cross spectral density graph...")
    plt_num = 1
    plt.clf()
    plt.figure(1)
    for i in range(0, data_shape[1] - 1):
        plt.subplot(8, 2, plt_num)
        x = raw_data[:, i]
        y = raw_data[:, i + 1]
        f, Pxy = signal.csd(x, y, nfft=nfft, fs=fs)  # returns PSD power per Hz
        plt.semilogy(f, np.abs(Pxy))
        plt.xlabel('frequency [Hz]')
        plt.ylabel('CSD [V**2/Hz]')
        plt.title('Channel %s' % (i + channel_bottom))
        plt_num += 1
        channel_data.append([f, Pxy])

    if print_frequency_graph:
        plt.show()
    return channel_data


def getdatasets_blinkonce():
    eeg_input, output = face.get_blink_once_ds()
    return eeg_input[2], output


def getdatasets_blink_ten():
    eeg_input, output = face.get_blink_ten_ds()
    return eeg_input[2], output


def getdatasets_gyroxy():
    eeg_input, output = face.get_blink_twice_ds()
    return eeg_input[0:1], output


def getdatasets_samplenums():
    eeg_input, output = face.get_blink_twice_ds()
    return eeg_input[3], output


def getdatasets_timems():
    eeg_input, output = face.get_blink_twice_ds()
    return eeg_input[4], output


def getdatasets_times():
    eeg_input, output = face.get_blink_twice_ds()
    return eeg_input[5], output
