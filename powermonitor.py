#!/usr/bin/python3
import threading
import time
import PySimpleGUI as sg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import ad_wrappers as adw
import serial_wrapper as sw
import statistics as stat
import os
from shutil import copyfile

DEBUG = False

TEMP_FILENAME = 'temp.csv'
CURRENT_HEADER = 'current'
TIMESTAMP_HEADER = 'time'
black = '#0F110D'
grey = '#3B3D3A'
yellow = '#FFFF21'


def draw_figure(canvas, figure):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg


def remove_and_init_temp_file():
    if os.path.exists(TEMP_FILENAME):
        os.remove(TEMP_FILENAME)
    with open(TEMP_FILENAME, 'a') as file:
        file.write("{},{}\n".format(TIMESTAMP_HEADER, CURRENT_HEADER))


def save_to_file_and_refresh_plot(window, ax, ay, last_n_samples):
    if len(ax) > last_n_samples:
        with open(TEMP_FILENAME, 'a') as file:
            temp_ax = ax[0:-last_n_samples]
            print(f"Saving {len(temp_ax)} samples.")
            for i, x in enumerate(temp_ax):
                file.write("{},{}\n".format(x, ay[i]))
            del ax[:-last_n_samples]
            del ay[:-last_n_samples]
            print(f"Current length - ax:{len(ax)} / ay:{len(ay)}.")
    window.write_event_value('-PLOT-', 1)


def save_last_samples(ax, ay):
    with open(TEMP_FILENAME, 'a') as file:
        temp_ax = ax[:-1]
        print(f"Saving {len(temp_ax)} samples.")
        for i, x in enumerate(temp_ax):
            file.write("{},{}\n".format(x, ay[i]))
        print(f"Current length - ax:{len(ax)} / ay:{len(ay)}.")


def ad_record_thread(frequency, seconds, display_samples, scaling_resistance, window, dwf_out, dwf_in, ax, ay):
    print('Thread started - will work for {} seconds'.format(seconds))

    if DEBUG:
        print("Generating sine wave...")
        adw.ad_generate_test_signal(dwf_out)

    print("Setting up acquisition...")
    adw.ad_configure_acquisition(dwf_in, frequency, seconds)

    # Wait at least 2 seconds for the offset to stabilize
    time.sleep(2)

    print("Begin acquisition...")
    adw.ad_start_data_acquisition(dwf_in)

    adw.ad_process_record_data(dwf_in, frequency, int(seconds * frequency), scaling_resistance, ay, ax,
                               lambda: save_to_file_and_refresh_plot(window, ax, ay, display_samples))

    save_last_samples(ax, ay)

    window.write_event_value('-THREAD-', '*** The thread says.... "I am finished" ***')


def main():
    """
    Starts and executes the GUI
    Reads data from a global variable and displays
    Returns when the user exits / closes the window
    """
    currents = []
    timestamps = []
    dwf_ao, dwf_ai = None, None
    device_ready = False
    sample_freq = int(adw.HZ_ACQ)
    display_samples = 2
    scaling_resistance = 1
    comports = sw.get_serial_list()

    sg.theme('DarkBlue')

    layout = [
        [
            sg.Text('Power Monitor', size=(50, 1), justification='center', font='Helvetica 20')
        ],
        [
            sg.Canvas(size=(640, 480), key='-CANVAS-')
        ],
        [
            sg.Button('Open AD', bind_return_key=True),
            sg.Button('Close AD', bind_return_key=True),
            sg.Text('Sampling frequency [Hz]:'),
            sg.Input(key='-SAMPLEFREQ-', focus=True, size=(10, 1), default_text=str(sample_freq)),
            sg.Text('Measurement length [s]:'),
            sg.Input(key='-SECONDS-', focus=True, size=(5, 1), default_text='0'),
            sg.Button('Start', bind_return_key=True)
        ],
        [
            sg.Text('Measuring resistor [Ohm]:'),
            sg.Input(key='-RESISTANCE-', focus=True, size=(10, 1), default_text=str(scaling_resistance)),
            sg.Text('Source voltage [V]:'),
            sg.Input(key='-VOLTAGE-', focus=True, size=(10, 1), default_text=5),
            sg.Text('Power [W]:'),
            sg.MLine(key='-POWER-', size=(10, 1), reroute_stdout=False, write_only=True, auto_refresh=True)
        ],
        [
            sg.Text('Display last N seconds:'),
            sg.Input(key='-DISPLAYSECS-', focus=True, size=(5, 1), default_text='2'),
            sg.Text('Min Y [A]:'),
            sg.Input(key='-YLIM_MIN-', focus=True, size=(5, 1)),
            sg.Text('Max Y [A]:'),
            sg.Input(key='-YLIM_MAX-', focus=True, size=(5, 1))
        ],
        [
            sg.Checkbox('Alarms on/off', key='-ALARMSWITCH-'),
            sg.Text('Low alarm [A]:'),
            sg.Input(key='-LOW_ALARM-', focus=True, size=(5, 1), default_text=str(0)),
            sg.Text('High alarm [A]:'),
            sg.Input(key='-HIGH_ALARM-', focus=True, size=(5, 1), default_text=str(0)),
            sg.Text('Alarms:'),
            sg.MLine(key='-ALARM-', size=(20, 1), reroute_stdout=False, write_only=True, autoscroll=True,
                     auto_refresh=True)
        ],
        [
            sg.Text('Serial port:'),
            sg.Combo(values=comports, key='-COMPORT-', size=(20, 1)),
            sg.Button('Update list', bind_return_key=True),
            sg.Text('Baudrate:'),
            sg.Combo(values=[9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600], key='-BAUDRATE-',
                     size=(10, 1)),
            sg.Text('Command:'),
            sg.Input(key='-CMD-', focus=True, size=(10, 1)),
            sg.Button('Send CMD', bind_return_key=True)
        ],
        [
            sg.Text('Save file:'),
            sg.Input(key='-FILENAME-', focus=True, size=(40, 1)),
            sg.FileSaveAs('Browse', file_types=(("CSV", "*.csv"),)),
            sg.Button('Save', bind_return_key=True)
        ],
        [
            sg.MLine(size=(100, 12), k='-ML-', reroute_stdout=True, write_only=True,
                     autoscroll=True, auto_refresh=True)
        ]
    ]

    window = sg.Window('Power Monitor', layout, finalize=True)

    timeout = thread = None

    canvas_elem = window['-CANVAS-']
    canvas = canvas_elem.TKCanvas

    # draw the initial plot in the window
    fig = Figure()
    ax = fig.add_subplot(111)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Current [A]")
    ax.set_facecolor(grey)
    ax.grid(color=black)
    fig_agg = draw_figure(canvas, fig)

    # --------------------- EVENT LOOP ---------------------
    while True:
        event, values = window.read(timeout=100)
        # print(event, values)
        if event in (sg.WIN_CLOSED, 'Exit'):
            break

        elif event == 'Start' and not thread:
            if not device_ready:
                print("Device is not ready!")
            elif float(values['-SECONDS-']) == 0.0:
                print("Measurement length can't be 0.0s")
            else:
                print('Thread Starting! Long work....sending value of {} seconds'.format(float(values['-SECONDS-'])))
                sample_freq = int(values['-SAMPLEFREQ-'])
                display_samples = int(sample_freq * int(values['-DISPLAYSECS-']))
                scaling_resistance = float(values['-RESISTANCE-'])
                remove_and_init_temp_file()
                thread = threading.Thread(
                    target=ad_record_thread,
                    args=(sample_freq, float(values['-SECONDS-']), display_samples, scaling_resistance, window,
                          dwf_ao, dwf_ai, timestamps, currents),
                    daemon=True)
                thread.start()

        elif event == 'Open AD' and not device_ready:
            adw.ad_get_dwf_version()
            if DEBUG:
                dwf_ao, dwf_ai = adw.ad_open_device_out_in()
                device_ready = True
            else:
                dwf_ai = adw.ad_open_device_in()
                device_ready = True

        elif event == 'Close AD' and device_ready and not thread:
            if DEBUG:
                adw.ad_close_device(dwf_ai)
                adw.ad_close_device(dwf_ao)
                dwf_ao, dwf_ai = None, None
                device_ready = False
            else:
                adw.ad_close_device(dwf_ai)
                dwf_ai = None
                device_ready = False

        elif event == '-THREAD-':  # Thread has completed
            thread.join(timeout=0)
            print('Thread finished')
            thread, message, progress, timeout = None, '', 0, None  # reset variables for next run

        elif event == '-PLOT-':
            ax.cla()  # clear the subplot

            print(f"Display samples: {display_samples} / Buffer len: {len(timestamps)}")

            ax.set_xlabel("Time [s]")
            ax.set_ylabel("Current [A]")

            ax.set_xlim((0 if len(timestamps) < display_samples else timestamps[-display_samples]), timestamps[-1])

            try:
                ax.set_ylim(int(values['-YLIM_MIN-']), int(values['-YLIM_MAX-']))
            except:
                pass

            ax.set_facecolor(grey)
            ax.grid(color=black)
            ax.plot(timestamps, currents, color=yellow)
            fig_agg.draw()

            # Avg power
            window['-POWER-'].Update(
                stat.mean(currents[int(0 if len(timestamps) < display_samples else -display_samples):-1]) * float(
                    values['-VOLTAGE-']))

            # Alarm check
            if bool(values['-ALARMSWITCH-']):
                if any(curr <= float(values['-LOW_ALARM-']) for curr in currents):
                    window['-ALARM-'].print("Alarm LOW!")
                if any(curr >= float(values['-HIGH_ALARM-']) for curr in currents):
                    window['-ALARM-'].print("Alarm HIGH!")

        elif event == 'Save':
            try:
                copyfile(TEMP_FILENAME, str(values['-FILENAME-']))
                print("Saved")
            except:
                print("Can't save")

        elif event == 'Update list':
            comports = sw.get_serial_list()
            window['-COMPORT-'].Update(values=list(comports))
        elif event == 'Send CMD':
            uart = sw.open_serial_port(str(values['-COMPORT-']), int(values['-BAUDRATE-']))
            sw.write_serial_port(uart, str(values['-CMD-']))
            sw.close_serial_port(uart)

    window.close()


if __name__ == '__main__':
    main()
    print('Exiting Program')
