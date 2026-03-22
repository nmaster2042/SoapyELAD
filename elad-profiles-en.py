#!/usr/bin/env python3
"""
ELAD FDM-S2 Profile Manager for OpenWebRX
"""

import json
import sys
import os
import subprocess

SETTINGS_FILE = "/var/lib/openwebrx/settings.json"

R  = "\033[0m"
B  = "\033[1m"
CY = "\033[96m"
GR = "\033[92m"
YE = "\033[93m"
RE = "\033[91m"
BL = "\033[94m"
MA = "\033[95m"

ELAD_DEVICES = {
    "elad_192kHz":  192000,
    "elad_384kHz":  384000,
    "elad_768kHz":  768000,
    "elad_1536kHz": 1536000,
    "elad_3072kHz": 3072000,
    "elad_6144kHz": 6144000,
}

def load_settings():
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)
    print(f"{GR}✅ Settings saved.{R}")

def restart_openwebrx():
    print(f"\n{YE}🔄 Restarting OpenWebRX...{R}")
    subprocess.run(["systemctl", "restart", "openwebrx"])
    print(f"{GR}✅ OpenWebRX restarted!{R}")

def select_devices(settings, prompt=None):
    available = [(i+1, dev_id) for i, dev_id in enumerate(ELAD_DEVICES) if dev_id in settings['sdrs']]
    print(f"\n{CY}Available devices:{R}")
    for num, dev_id in available:
        khz = ELAD_DEVICES[dev_id] // 1000
        print(f"  {YE}{num}{R}. {dev_id} ({khz} kHz)")
    print(f"  {YE}0{R}. ↩️  Cancel")
    if not prompt:
        prompt = "Select device (e.g. 1,3,5 or ENTER for all): "
    choice = input(prompt).strip()
    if choice == '0':
        return None
    if not choice:
        return [dev_id for _, dev_id in available]
    selected = []
    for part in choice.split(','):
        try:
            idx = int(part.strip()) - 1
            if 0 <= idx < len(available):
                selected.append(available[idx][1])
        except ValueError:
            pass
    if not selected:
        print(f"{RE}❌ No valid device selected.{R}")
        return None
    return selected

def get_profile_name(settings, dev_id, prof_id):
    try:
        return settings['sdrs'][dev_id]['profiles'][prof_id]['name']
    except:
        return prof_id

def select_profile(settings, target_devices, prompt=None):
    found = {}
    for dev_id in target_devices:
        for prof_id, prof in settings['sdrs'][dev_id].get('profiles', {}).items():
            if prof_id not in found:
                found[prof_id] = prof.get('name', prof_id)
    if not found:
        print(f"{RE}❌ No profiles found.{R}")
        return None
    print(f"\n{CY}Available profiles:{R}")
    found_list = sorted(found.items(), key=lambda x: x[1])
    for i, (prof_id, name) in enumerate(found_list, 1):
        print(f"  {YE}{i}{R}. {name}")
    print(f"  {YE}0{R}. ↩️  Cancel")
    if not prompt:
        prompt = "Select profile (number): "
    try:
        choice = int(input(prompt))
        if choice == 0:
            return None
        prof_id, name = found_list[choice - 1]
        return prof_id
    except (ValueError, IndexError):
        print(f"{RE}❌ Invalid choice.{R}")
        return None

def list_profiles(settings):
    print(f"\n{B}📋 CURRENT ELAD PROFILES{R}")
    print("=" * 60)
    found = {}
    for dev_id, samp_rate in ELAD_DEVICES.items():
        if dev_id not in settings['sdrs']:
            continue
        profiles = settings['sdrs'][dev_id].get('profiles', {})
        for prof_id, prof in profiles.items():
            if prof_id not in found:
                found[prof_id] = {}
            found[prof_id][dev_id] = prof
    if not found:
        print("No profiles found.")
        return
    for prof_id, devices in sorted(found.items(), key=lambda x: list(x[1].values())[0]['name']):
        bw_list = []
        for dev_id in devices:
            khz = ELAD_DEVICES[dev_id] // 1000
            bw_list.append(f"{khz}kHz")
        first = list(devices.values())[0]
        freq_mhz = first['center_freq'] / 1e6
        print(f"\n  🔹 {B}{first['name']}{R}")
        print(f"     Frequency: {freq_mhz:.3f} MHz  Mode: {first['start_mod']}")
        print(f"     Present in: {YE}{', '.join(bw_list)}{R}")

def get_profile_data():
    print(f"  {YE}(type 0 in any field to cancel){R}")
    name = input("Profile name (e.g. NDB 927kHz): ").strip()
    if name == '0' or not name:
        print("↩️  Operation cancelled.")
        return None, None
    prof_id = name.lower().replace(" ", "_").replace("/", "_")
    freq_str = input("Center frequency (MHz, e.g. 0.927 or 7.1): ").strip()
    if freq_str == '0' or not freq_str:
        print("↩️  Operation cancelled.")
        return None, None
    try:
        freq_mhz = float(freq_str)
        if freq_mhz <= 0:
            print(f"{RE}❌ Invalid frequency.{R}")
            return None, None
        center_freq = int(freq_mhz * 1e6)
    except ValueError:
        print(f"{RE}❌ Invalid frequency.{R}")
        return None, None
    print("Available modes: am, usb, lsb, cw, wfm, nfm, dab")
    start_mod = input("Reception mode (0=cancel, default: am): ").strip()
    if start_mod == '0':
        print("↩️  Operation cancelled.")
        return None, None
    if not start_mod:
        start_mod = "am"
    return prof_id, {"name": name, "center_freq": center_freq, "start_mod": start_mod, "start_freq": center_freq}

def add_profile(settings, to_all=True):
    if to_all:
        print(f"\n{B}➕ ADD PROFILE TO ALL ELAD DEVICES{R}")
        target_devices = [d for d in ELAD_DEVICES if d in settings['sdrs']]
    else:
        print(f"\n{B}➕ ADD PROFILE TO SELECTED DEVICES{R}")
        target_devices = select_devices(settings)
        if not target_devices:
            return
    print("=" * 60)
    prof_id, prof_data = get_profile_data()
    if not prof_id:
        return
    count = 0
    for dev_id in target_devices:
        samp_rate = ELAD_DEVICES[dev_id]
        profile = prof_data.copy()
        profile['samp_rate'] = samp_rate
        settings['sdrs'][dev_id]['profiles'][prof_id] = profile
        count += 1
        khz = samp_rate // 1000
        print(f"  {GR}✅ Added to {dev_id} ({khz} kHz){R}")
    save_settings(settings)
    print(f"\n{GR}✅ Profile '{prof_data['name']}' added to {count} ELAD devices!{R}")

def delete_profile(settings, from_all=True):
    if from_all:
        print(f"\n{B}🗑️  DELETE PROFILE FROM ALL ELAD DEVICES{R}")
        target_devices = [d for d in ELAD_DEVICES if d in settings['sdrs']]
    else:
        print(f"\n{B}🗑️  DELETE PROFILE FROM SELECTED DEVICES{R}")
        target_devices = select_devices(settings)
        if not target_devices:
            return
    print("=" * 60)
    prof_id = select_profile(settings, target_devices)
    if not prof_id:
        return
    prof_name = get_profile_name(settings, target_devices[0], prof_id)
    dev_names = ", ".join([d.replace("elad_", "") for d in target_devices])
    confirm = input(f"\nDelete '{prof_name}' from [{dev_names}]? (y/N): ").strip().lower()
    if confirm != 'y':
        print("↩️  Operation cancelled.")
        return
    count = 0
    for dev_id in target_devices:
        if prof_id in settings['sdrs'][dev_id].get('profiles', {}):
            del settings['sdrs'][dev_id]['profiles'][prof_id]
            count += 1
            print(f"  {RE}🗑️  Removed from {dev_id}{R}")
    save_settings(settings)
    print(f"\n{GR}✅ Profile '{prof_name}' deleted from {count} ELAD devices!{R}")

def copy_profile(settings):
    print(f"\n{B}📋 COPY PROFILE FROM ONE DEVICE TO OTHERS{R}")
    print("=" * 60)
    print("Source device:")
    dev_list = [d for d in ELAD_DEVICES if d in settings['sdrs']]
    for i, dev_id in enumerate(dev_list, 1):
        khz = ELAD_DEVICES[dev_id] // 1000
        print(f"  {YE}{i}{R}. {dev_id} ({khz} kHz)")
    print(f"  {YE}0{R}. ↩️  Cancel")
    try:
        choice = int(input("Select source device (number): "))
        if choice == 0:
            return
        src_dev = dev_list[choice - 1]
    except (ValueError, IndexError):
        print(f"{RE}❌ Invalid choice.{R}")
        return
    prof_id = select_profile(settings, [src_dev], "Select profile to copy (number): ")
    if not prof_id:
        return
    src_profile = settings['sdrs'][src_dev]['profiles'][prof_id]
    prof_name = src_profile['name']
    print(f"\nDestination for '{prof_name}':")
    target_devices = select_devices(settings, "Select destination devices (e.g. 1,3,5 or ENTER for all): ")
    if not target_devices:
        return
    target_devices = [d for d in target_devices if d != src_dev]
    if not target_devices:
        print(f"{RE}❌ No valid destination device.{R}")
        return
    count = 0
    for dev_id in target_devices:
        samp_rate = ELAD_DEVICES[dev_id]
        new_profile = src_profile.copy()
        new_profile['samp_rate'] = samp_rate
        settings['sdrs'][dev_id]['profiles'][prof_id] = new_profile
        count += 1
        print(f"  {GR}✅ Copied to {dev_id}{R}")
    save_settings(settings)
    print(f"\n{GR}✅ Profile '{prof_name}' copied to {count} ELAD devices!{R}")

def print_menu(modified):
    print("\n" + "=" * 60)
    print(f"  {B}{CY}🎛️  ELAD FDM-S2 PROFILE MANAGER{R}")
    print("=" * 60)
    print(f"  {YE}1{R}. {CY}📋{R}  List all profiles")
    print(f"  {YE}2{R}. {GR}➕{R}  Add profile to ALL devices")
    print(f"  {YE}3{R}. {GR}➕{R}  Add profile to SELECTED devices")
    print(f"  {YE}4{R}. {RE}🗑️{R}  Delete profile from ALL devices")
    print(f"  {YE}5{R}. {RE}🗑️{R}  Delete profile from SELECTED devices")
    print(f"  {YE}6{R}. {MA}📋{R}  Copy profile from one device to others")
    if modified:
        print(f"  {YE}0{R}. {YE}🚪  Exit and restart OpenWebRX{R}")
    else:
        print(f"  {YE}0{R}. {YE}🚪  Exit{R}")
    print(f"  {YE}9{R}. 🚪  Exit without restarting OpenWebRX")
    print("=" * 60)

def main():
    if not os.path.exists(SETTINGS_FILE):
        print(f"{RE}❌ File not found: {SETTINGS_FILE}{R}")
        sys.exit(1)

    modified = False

    while True:
        print_menu(modified)
        choice = input("Choice: ").strip()
        settings = load_settings()

        if choice == '1':
            list_profiles(settings)
        elif choice == '2':
            add_profile(settings, to_all=True)
            modified = True
        elif choice == '3':
            add_profile(settings, to_all=False)
            modified = True
        elif choice == '4':
            delete_profile(settings, from_all=True)
            modified = True
        elif choice == '5':
            delete_profile(settings, from_all=False)
            modified = True
        elif choice == '6':
            copy_profile(settings)
            modified = True
        elif choice == '0':
            if modified:
                restart_openwebrx()
            print(f"{GR}👋 Goodbye!{R}")
            break
        elif choice == '9':
            print("👋 Goodbye! (OpenWebRX not restarted)")
            break
        else:
            print(f"{RE}❌ Invalid choice.{R}")

if __name__ == "__main__":
    main()
