# SoapyELAD - ELAD FDM-S2 and FDM-S1 Driver for SoapySDR and OpenWebRX

This project provides a SoapySDR plugin for ELAD receivers on Linux, supporting various sample rates, FPGA programming, and OpenWebRX integration. For detailed requirements, hardware support, and dependencies, please refer to the documentation on {Link: GitHub https://github.com}

## Features
- Full support for ELAD FDM-S2 and FDM-S1 on Linux
- All sample rates: 192, 384, 768, 1536, 3072, 6144 kHz (ELAD S2 only)
- Automatic FPGA programming at startup
- Integration with OpenWebRX

## Requirements
- Debian/Ubuntu Linux (tested on Debian 13 Trixie)
- SoapySDR 0.8+
- libusb-1.0
- OpenWebRX 1.2+
- cmake, build-essential

## Hardware
- ELAD FDM-S2 or FDM-S1 connected via USB 2.0
- Maximum stable sample rate: 3072 kHz (4 bytes/sample)
- At 6144 kHz: 2 bytes/sample mode, ~4.9 MHz bandwidth (ELAD S2)

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
| ELAD FDM-S1 192kHz | 192000 | 153 kHz |
| ELAD FDM-S1 384kHz | 384000 | 307 kHz |
| ELAD FDM-S1 768kHz | 768000 | 614 kHz |
| ELAD FDM-S1 1.5MHz | 1536000 | 1.2 MHz |
| ELAD FDM-S1 3MHz | 3072000 | 2.4 MHz |
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

## Compatible Software

Since this is a SoapySDR plugin, it works with any SoapySDR-compatible software:

| Software | Status | Notes |
|----------|--------|-------|
| OpenWebRX | ✅ Tested | Full integration included |
| SDR++ | ✅ Compatible | Select SoapySDR source, driver=elad |
| GQRX | ✅ Compatible | Select SoapySDR source, driver=elad |
| GNU Radio | ✅ Compatible | Via gr-soapy block |
| CubicSDR | ✅ Compatible | Select SoapySDR source |
| SDRangel | ✅ Compatible | Select SoapySDR source |

## Running your SDR Software

When launching your favorite SDR software (such as SDR++, GQRX, or CubicSDR), you must now specify the hardware model argument to let SoapySDR initialize the correct master clock and FPGA routing:

- For **ELAD FDM-S1**: Use device arguments `driver=elad,product=FDM-S1`
- For **ELAD FDM-S2**: Use device arguments `driver=elad,product=FDM-S2`

### Usage with non-OpenWebRX software

Before launching any software, program the FPGA with the desired sample rate:
```bash
sudo /usr/local/bin/elad-firmware + 6   # 6144 kHz
sudo /usr/local/bin/elad-firmware + 5   # 3072 kHz
sudo /usr/local/bin/elad-firmware + 4   # 1536 kHz
sudo /usr/local/bin/elad-firmware + 3   # 768 kHz
sudo /usr/local/bin/elad-firmware + 2   # 384 kHz
sudo /usr/local/bin/elad-firmware + 1   # 192 kHz
```

## Profile Manager

A command-line tool to manage OpenWebRX profiles across all ELAD FDM-S2 devices.

### Features
- List all profiles across all devices
- Add a profile to ALL devices at once
- Add a profile to SELECTED devices
- Delete a profile from ALL or SELECTED devices
- Copy a profile from one device to others
- Automatic OpenWebRX restart after changes

### Usage

**English version:**
\`\`\`bash
profile-rx-en
\`\`\`

**Italian version:**
\`\`\`bash
profile-rx
\`\`\`

### Profile fields
- **Name**: Profile display name (e.g. "NDB 927kHz")
- **Frequency**: Center frequency in MHz (e.g. 0.927 for 927 kHz)
- **Mode**: am, usb, lsb, cw, wfm, nfm, dab

### Files
| File | Description |
|------|-------------|
| elad-profiles-en.py | Profile manager (English) |
| elad-profiles.py | Profile manager (Italian) |
| profile-rx-en | English launcher |
| profile-rx | Italian launcher |
