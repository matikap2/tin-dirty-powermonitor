#!/usr/bin/python3
import sys
import glob
import serial


def get_serial_list():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


def open_serial_port(port, baudrate):
    print("Opening serial port")
    handler = serial.Serial(port, baudrate)
    return handler


def write_serial_port(handler, msg):
    print(f"Write serial port: {msg}")
    arr = bytearray(msg, 'utf-8')
    handler.write(arr)


def close_serial_port(handler):
    print("Closing serial port")
    handler.close()
