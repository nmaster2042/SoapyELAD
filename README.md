# SoapyELAD - ELAD FDM-S2 Driver for SoapySDR and OpenWebRX

This project provides a SoapySDR plugin for the ELAD FDM-S2 SDR receiver on Linux,
enabling its use with OpenWebRX and other SoapySDR-compatible software.

## Features
- Full support for ELAD FDM-S2 on Linux
- All sample rates: 192, 384, 768, 1536, 3072, 6144 kHz
- Automatic FPGA programming at startup
- Integration with OpenWebRX

## Requirements
- Debian/Ubuntu Linux (tested on Debian 13 Trixie)
- SoapySDR 0.8+
- libusb-1.0
- OpenWebRX 1.2+
- cmake, build-essential

## Hardware
- ELAD FDM-S2 connected via USB 2.0
- Maximum stable sample rate: 3072 kHz (4 bytes/sample)
- At 6144 kHz: 2 bytes/sample mode, ~4.9 MHz bandwidth

## Installation

### 1. Install dependencies
```bash
sudo apt install -y cmake build-essential libusb-1.0-0-dev libsoapysdr-dev
```

### 2. Download elad-firmware
Download `elad-firmware-2.0-intel` from https://www.eladit.com/it/download?path=sdr%2FLinux
and copy it to `/usr/local/bin/elad-firmware`, then make it executable:
```bash
sudo chmod +x /usr/local/bin/elad-firmware
```

### 3. Build and install SoapyELAD
```bash
cd src
mkdir build && cd build
cmake ..
make
sudo make install
```

### 4. Install OpenWebRX integration
```bash
sudo cp owrx/elad.py /usr/lib/python3/dist-packages/owrx/source/elad.py
```

Edit `/usr/lib/python3/dist-packages/owrx/feature.py` and add inside the `features` dictionary:
```python
"elad": ["soapy_connector", "soapy_elad"],
```
And add this method to the `FeatureDetector` class:
```python
def has_soapy_elad(self):
    return self._has_soapy_driver("elad")
```

### 5. Install udev rule
```bash
sudo cp udev/99-elad.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

### 6. Install systemd service
```bash
sudo cp systemd/elad-init.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/elad-init.sh
sudo cp systemd/elad-firmware.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable elad-firmware.service
sudo systemctl start elad-firmware.service
```

## OpenWebRX Configuration
Add devices in OpenWebRX settings. Example for all sample rates:

| Device Name | Sample Rate | Bandwidth |
|---|---|---|
| ELAD FDM-S2 192kHz | 192000 | 153 kHz |
| ELAD FDM-S2 384kHz | 384000 | 307 kHz |
| ELAD FDM-S2 768kHz | 768000 | 614 kHz |
| ELAD FDM-S2 1.5MHz | 1536000 | 1.2 MHz |
| ELAD FDM-S2 3MHz | 3072000 | 2.4 MHz |
| ELAD FDM-S2 6MHz | 6144000 | 4.9 MHz |

## Notes
- Each sample rate requires FPGA reprogramming (~6 seconds)
- Only one device can be active at a time
- After OpenWebRX update, re-run steps 4 (elad.py and feature.py)
- USB 2.0 limit: 6144 kHz may show artifacts on some systems

## Credits
- Protocol reverse-engineered from gr-elad-3.8 source code by ELAD Srl
- Driver developed for Linux/OpenWebRX community
- Tested on Lenovo ThinkCentre M910q, Debian 13 Trixie

## License
GPL v3
