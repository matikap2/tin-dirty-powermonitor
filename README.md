# tin-dirty-powermonitor

Tin-dirty-powermonitor is simple and dirty app made for current/power monitoring using Digilent Analog Discovery tool. It utilizes *first AnalogIn channel* of AD.

## Requirements

* OS: Windows / MacOS / Linux
* Python: version >= 3.7
* Libraries: from requirements.txt
* [WaveForms SDK](https://store.digilentinc.com/waveforms-download-only/)

## Installation

Install libraries from requirements.txt using [pip](https://pip.pypa.io/en/stable/).

```bash
pip install -r requirements.txt
```

WaveForms SDK is *mandatory* to install! Without it program won't work.

## Configuration

You should configure `DEBUG` option in main `powermonitor.py` script.
```python
DEBUG = True      # AnalogOut channel is enabled and you can connect it to AnalogIn channel to see test sinus -2V/+2V 1Hz waveform.
DEBUG = False     # AnalogOut is disabled.
```

## Authors
* Mateusz Kapala
* Mateusz Gawron
* Tomasz Cygan

Project made for TiN course on AGH UST.
