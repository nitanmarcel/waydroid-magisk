# Waydroid Magisk Installer
Install Magisk Delta in waydroid. 

- [Waydroid Magisk Installer](#waydroid-magisk-installer)
- [Installing Magisk on Waydroid](#installing-magisk-on-waydroid)
  - [Requirements](#requirements)
  - [Installation Steps](#installation-steps)
- [FAQ](#faq)
  - [What does work?](#what-does-work)
  - [Waydroid won't start](#waydroid-wont-start)
  - [No internet connection](#no-internet-connection)
  - [Magisk was installed but I have no root](#magisk-was-installed-but-i-have-no-root)
  - [Magisk modules not working or not showing as installed](#magisk-modules-not-working-or-not-showing-as-installed)
  - [Updating](#updating)
  - [Does this survive Waydroid updates?](#does-this-survive-waydroid-updates)
  - [Does Zygisk work?](#does-zygisk-work)
  - [I've enabled Zygisk in Magisk Delta Stable, updated waydroid images!!](#ive-enabled-zygisk-in-magisk-delta-stable-updated-waydroid-images)
  - [How is this different from other scripts?](#how-is-this-different-from-other-scripts)
  - [What is Magisk Delta?](#what-is-magisk-delta)

# Installing Magisk on Waydroid

## Requirements
* Waydroid 
* curl 
* zip
* gzip

## Installation Steps
1. Stop Waydroid using either systemd or init (depending on your system).
2. Download `install.sh`.
3. Make the script executable with `chmod +x ./install.sh`.*
  * Ubuntu Touch requires manually resize of waydroid system.img.
    * `sudo fsck.ext4 -f /var/lib/waydroid/images/system.img`
    * `sudo resize2fs /var/lib/waydroid/images/system.img 2G`
4. Run the script with `sudo ./install.sh`.*
  * Ubuntu Touch requires setting an working directory in `/home/phablet`
    * `sudo install.sh /home/phablet/magisk_waydroid`
5. Restart Waydroid using either systemd or init (depending on your system).
6. Install [Magisk Delta Canary](https://huskydg.github.io/magisk-files/) inside Waydroid. The Stable channel is not fully compatible with waydroid yet.
7. Complete the first-time setup in Magisk Delta. The app will try to reboot Waydroid, but it will fail. Restart Waydroid using either systemd or init (depending on your system).
8. After the first setup is complete, open magisk again, and re-install Magisk from Magisk Delta Manager.
9. **To avoid any issues it's important to read [FAQ](#faq) before using Magisk Delta on waydroid.**

# FAQ

## What does work?
* root
* zygisk
* modules
* updates
* ~~ota updates survival~~ (requires [#580](https://github.com/waydroid/waydroid/pull/580). Implemented in [waydroid-1-4](https://github.com/nitanmarcel/waydroid-magisk-installer/tree/waydroid-1-4) branch)

## Waydroid won't start
Note that Waydroid may take longer to boot due to Magisk being set up.

## No internet connection
Try restarting Waydroid using either systemd or init (depending on your system).

## Magisk was installed but I have no root
Something was gone wrong, or you have conflicting magisk files in the system. Re-try with a clean installation of waydroid and system.img.

## Magisk modules not working or not showing as installed
Currently, modules only work with Magisk Delta Canary. Download and install the apk in Waydroid, and update by following the instructions in the "Updating" section below.

## Updating
Use Magisk Delta to install Magisk directly into the system partition. Always update through the Magisk app, not the `install.sh` script.

## Does this survive Waydroid updates?
If the Android system is updated, Magisk will be removed and you'll need to run `install.sh` again to reinstall it.

## Does Zygisk work?
Zygisk only works with Magisk Delta Canary which gets installed by default with `install.sh`. Enabling it with Magisk Delta Stable will result in waydroid not booting.Debug and updating waydroid as it will require running `install.sh` which reverts to stable magisk and will stop waydroid from booting. -->

## I've enabled Zygisk in Magisk Delta Stable, updated waydroid images!!
Delete `/data/adb/magisk.db` inside `waydroid shell`. Will clear Magisk's database and disable zygdisk.

## How is this different from other scripts?
* This script installs Magisk Delta, a fork of Magisk with some reimplemented features such as Magisk Hide and better support for Android emulators.
* It follows the same installation workflow as Magisk, allowing users to update through the Magisk Delta Manager instead of relying on the `install.sh` script from this repository.

## What is Magisk Delta?
Magisk Delta is a fork of the official Magisk Manager with the old Magisk Hide feature re-added and other new features. You can find a list of differences between Magisk Delta and official Magisk [here](https://github.com/HuskyDG/magisk-files/blob/main/note_stable.md#diffs-to-official-magisk).

## Arch Linux
linux-zen breaks Magisk Delta, compile your own kernel as per Arch wiki or switch to another kernel. `linux-xanmod` and `linux-xanmod-anbox` had been reported to work too.
