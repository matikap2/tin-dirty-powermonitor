#!/usr/bin/python3
import sys
import dwf
import time
import matplotlib.pyplot as plt

# Constants
HZ_ACQ = 2e3
ACQ_TIME = 5
N_SAMPLES = int(ACQ_TIME * HZ_ACQ)


def ad_open_device_out_in():
    dwf_ao_handler, dwf_ai_handler = None, None

    if ad_print_devices_info():
        print("Configuring device")
        dwf_ao_handler = dwf.DwfAnalogOut()
        dwf_ai_handler = dwf.DwfAnalogIn(dwf_ao_handler)

    return dwf_ao_handler, dwf_ai_handler


def ad_open_device_in():
    dwf_ai_handler = None

    if ad_print_devices_info():
        print("Configuring device")
        dwf_ai_handler = dwf.DwfAnalogIn()

    return dwf_ai_handler


def ad_close_device(dwf_handler):
    print("Closing device")
    dwf_handler.close()


def ad_get_dwf_version():
    """
    Get version of dwf library.

    :return: string: version
    """
    ver = dwf.FDwfGetVersion()
    print("DWF Version: " + ver)
    return ver


def ad_print_devices_info():
    """
    Print device info and get number of connected devices.

    :return: int: number of devices
    """
    devices = dwf.DwfEnumeration()
    print("Number of Devices: " + str(len(devices)))

    for i, device in enumerate(devices):
        print("------------------------------")
        print("Device " + str(i) + " : ")
        print("\t" + device.deviceName())
        print("\t" + device.SN())

    return len(devices)


def ad_generate_test_signal(dwf_ao_handler):
    """
    Generate test sinusoidal signal.

    :param dwf_ao_handler: AD device handler
    :return: -
    """
    dwf_ao_handler.nodeEnableSet(0, dwf_ao_handler.NODE.CARRIER, True)
    dwf_ao_handler.nodeFunctionSet(0, dwf_ao_handler.NODE.CARRIER, dwf_ao_handler.FUNC.SINE)
    dwf_ao_handler.nodeFrequencySet(0, dwf_ao_handler.NODE.CARRIER, 1.0)
    dwf_ao_handler.nodeAmplitudeSet(0, dwf_ao_handler.NODE.CARRIER, 2.0)
    dwf_ao_handler.configure(0, True)


def ad_configure_acquisition(dwf_ai_handler, sample_freq, record_time):
    """
    Configure analog channel of AD for data acquisition in record mode.
    Set mode - record.

    :param dwf_ai_handler: AD device handler
    :param sample_freq: Sample frequency
    :param record_time: Time of acquisition in seconds
    :return: -
    """
    dwf_ai_handler.channelEnableSet(0, True)
    dwf_ai_handler.channelRangeSet(0, 5.0)
    dwf_ai_handler.acquisitionModeSet(dwf_ai_handler.ACQMODE.RECORD)
    dwf_ai_handler.frequencySet(sample_freq)
    dwf_ai_handler.recordLengthSet(record_time)


def ad_start_data_acquisition(dwf_ai_handler):
    """
    Start data acquisition from AD.

    :param dwf_ai_handler: AD device handler
    :return: -
    """
    dwf_ai_handler.configure(False, True)


def ad_process_record_data(dwf_ai_handler, sample_freq, max_sample_n, scaling_resistance,
                           samples_buffer, timestamp_buffer, function_loop):
    """
    Process acquired data from AD.

    :param scaling_resistance: for voltage->current conversion
    :param sample_freq: sampling frequency
    :param dwf_ai_handler: AD device handler
    :param max_sample_n: Max number of samples to acquire
    :param samples_buffer: Output sample buffer
    :param timestamp_buffer: Output timestamp buffer
    :param function_loop: Additional function to do
    :return: Samples count, lost samples flag, corrupted samples flag
    """
    samples_buffer.clear()
    timestamp_buffer.clear()

    samples_cnt = 0
    lost_flag = False
    corrupted_flag = False

    while samples_cnt < max_sample_n:
        sts = dwf_ai_handler.status(True)
        if samples_cnt == 0 and sts in (dwf_ai_handler.STATE.CONFIG,
                                        dwf_ai_handler.STATE.PREFILL,
                                        dwf_ai_handler.STATE.ARMED):
            # Acquisition not yet started.
            continue

        available_cnt, lost_cnt, corrupted_cnt = dwf_ai_handler.statusRecord()
        samples_cnt += lost_cnt

        if lost_cnt > 0:
            lost_flag = True
        if corrupted_cnt > 0:
            corrupted_flag = True
        if available_cnt == 0:
            continue
        if samples_cnt + available_cnt > max_sample_n:
            available_cnt = max_sample_n - samples_cnt

        # get samples
        temp_samples = dwf_ai_handler.statusData(0, available_cnt)
        samples_buffer.extend([s / scaling_resistance for s in temp_samples])
        timestamp_buffer.extend([i * (1 / sample_freq) for i in list(range(samples_cnt, samples_cnt + available_cnt))])
        samples_cnt += available_cnt

        # time.sleep(.1)
        function_loop()

    print("Recording finished")
    if lost_flag:
        print("Samples were lost! Reduce frequency")
    if corrupted_flag:
        print("Samples could be corrupted! Reduce frequency")

    return samples_cnt, lost_flag, corrupted_flag


if __name__ == '__main__':
    voltages = []
    timestamps = []

    ad_get_dwf_version()
    if not ad_print_devices_info():
        sys.exit()

    print("Configuring device")
    dwf_ao, dwf_ai = ad_open_device_out_in()

    print("Generating sine wave...")
    ad_generate_test_signal(dwf_ao)

    print("Setting up acquisition...")
    ad_configure_acquisition(dwf_ai, HZ_ACQ, ACQ_TIME)

    # Wait at least 2 seconds for the offset to stabilize
    time.sleep(2)

    print("Begin acquisition...")
    ad_start_data_acquisition(dwf_ai)

    ad_process_record_data(dwf_ai, HZ_ACQ, N_SAMPLES, voltages, timestamps, print)

    with open("record.csv", "w") as f:
        for v in voltages:
            f.write("%s\n" % v)

    plt.cla()
    plt.plot(timestamps, voltages)
    plt.show()

    ad_close_device(dwf_ai)
    ad_close_device(dwf_ao)

    sys.exit(1)
