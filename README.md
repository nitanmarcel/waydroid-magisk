# Waydroid Magisk Installer
Install Magisk Delta in waydroid.

- [Waydroid Magisk Installer](#waydroid-magisk-installer)
- [Installing Magisk on Waydroid](#installing-magisk-on-waydroid)
  - [Requirements](#requirements)
  - [Installation Steps](#installation-steps)
- [FAQ](#faq)
  - [Waydroid won't start](#waydroid-wont-start)
  - [No internet connection](#no-internet-connection)
  - [Magisk modules not working or not showing as installed](#magisk-modules-not-working-or-not-showing-as-installed)
  - [Updating](#updating)
  - [Does this survive Waydroid updates?](#does-this-survive-waydroid-updates)
  - [Does Zygisk work?](#does-zygisk-work)
  - [I've enabled Zygisk in Magisk Delta Stable/Canary, updated waydroid images!!](#ive-enabled-zygisk-in-magisk-delta-stablecanary-updated-waydroid-images)
  - [How is this different from other scripts?](#how-is-this-different-from-other-scripts)
  - [What is Magisk Delta?](#what-is-magisk-delta)

# Installing Magisk on Waydroid

## Requirements
* Waydroid 
* curl 
* zip

## Installation Steps
1. Stop Waydroid using either systemd or init (depending on your system).
2. Download `install.sh`.
3. Make the script executable with `chmod +x ./install.sh`.
4. Run the script with `sudo ./install.sh`.
5. Restart Waydroid using either systemd or init (depending on your system).
6. Install [Magisk Delta](https://huskydg.github.io/magisk-files/) inside Waydroid.
7. Complete the first-time setup in Magisk Delta. The app will try to reboot Waydroid, but it will fail. Restart Waydroid using either systemd or init (depending on your system).
8. **To avoid any issues it's important to read [FAQ](#faq) before using Magisk Delta on waydroid.**

# FAQ

## Waydroid won't start
Note that Waydroid may take longer to boot due to Magisk being set up.

## No internet connection
Try restarting Waydroid using either systemd or init (depending on your system).

## Magisk modules not working or not showing as installed
Currently, modules only work with Magisk Delta Canary. Download and install the apk in Waydroid, and update by following the instructions in the "Updating" section below.

## Updating
Use Magisk Delta to install Magisk directly into the system partition. Always update through the Magisk app, not the `install.sh` script.

## Does this survive Waydroid updates?
If the Android system is updated, Magisk will be removed and you'll need to run `install.sh` again to reinstall it.

## Does Zygisk work?
Zygisk only works on devices with SELinux enabled or by using Magisk Debug (Not recommended). Attempting to enable it without SELinux enabled or with any other version will crash Waydroid (a fix is in the works).

Careful when installing Magisk Debug and updating waydroid as it will require running `install.sh` which reverts to stable magisk and will stop waydroid from booting.

## I've enabled Zygisk in Magisk Delta Stable/Canary, updated waydroid images!!
Delete `/data/adb/magisk.db` inside `waydroid shell`. Will clear Magisk's database and disable zygdisk.

## How is this different from other scripts?
* This script installs Magisk Delta, a fork of Magisk with some reimplemented features such as Magisk Hide and better support for Android emulators.
* It follows the same installation workflow as Magisk, allowing users to update through the Magisk Delta Manager instead of relying on the `install.sh` script from this repository.

## What is Magisk Delta?
Magisk Delta is a fork of the official Magisk Manager with the old Magisk Hide feature re-added and other new features. You can find a list of differences between Magisk Delta and official Magisk [here](https://github.com/HuskyDG/magisk-files/blob/main/note_stable.md#diffs-to-official-magisk).
