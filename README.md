# Waydroid Magisk
Kitsune Mask manager for Waydroid.

- [Waydroid Magisk](#waydroid-magisk)
- [Installing Magisk on Waydroid](#installing-magisk-on-waydroid)
  - [Requirements](#requirements)
  - [Installation](#installation)
    - [From PPA](#from-ppa)
    - [From GitHub](#from-github)
- [Usage](#usage)
- [FAQ](#faq)
  - [What does work?](#what-does-work)
  - [Waydroid won't start](#waydroid-wont-start)
  - [No internet connection](#no-internet-connection)
  - [Magisk modules not working or not showing as installed](#magisk-modules-not-working-or-not-showing-as-installed)
  - [Kitsune Mask fails to patch SELinux policy.](#magisk-delta-fails-to-patch-selinux-policy)
  - [Updating](#updating)
  - [Does Zygisk work?](#does-zygisk-work)
  - [I've enabled Zygisk in Kitsune Mask Stable!!](#ive-enabled-zygisk-in-magisk-delta-stable)
  - [How is this different from other scripts?](#how-is-this-different-from-other-scripts)
  - [What is Kitsune Mask?](#what-is-magisk-delta)
  - [Arch Linux](#arch-linux)
  - [Ubuntu Touch](#ubuntu-touch)
- [Credits](#credits)

# Installing Magisk on Waydroid

## Requirements
* waydroid
* make
* git

## Installation
### From PPA
1. `curl -s --compressed "https://nitanmarcel.github.io/waydroid-magisk/waydroid_magisk.gpg" | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/waydroid_magisk.gpg > /dev/null`
2. `sudo curl -s --compressed -o /etc/apt/sources.list.d/waydroid_magisk.list https://nitanmarcel.github.io/waydroid-magisk/waydroid_magisk.list`
3. `sudo apt update`
4. `sudo apt install waydroid-magisk` 
5. run `sudo waydroid_magisk install` to install Magisk
  * `waydroid-magisk` can also be used as a manager. If you want to use Kitsune Mask Manager instead use the install command with `--manager` argument.
6. start waydroid and run `sudo waydroid_magisk setup` to trigger first time setup.
7. **To avoid any issues it's important to read [FAQ](#faq) before using Kitsune Mask on waydroid.**

### From GitHub
1. git clone `https://github.com/nitanmarcel/waydroid-magisk-installer/`
2. run `sudo make install USE_SYSTEMD=1`
  * If using upstart (e.g Ubuntu Touch 16.04)
  * run `sudo make install USE_UPSTART=1`
3. run `sudo waydroid_magisk install` to install Magisk
  * `waydroid-magisk` can also be used as a manager. If you want to use Kitsune Mask Manager instead use the install command with `--manager` argument.
  * Ubuntu Touch requires setting an working directory in `/home/phablet`
  * `sudo waydroid_magisk install --tmpdir /home/phablet/magisk_waydroid`

4. start waydroid and run `sudo waydroid_magisk setup` to trigger first time setup.
5. enable ota survival service
  * For systemd `sudo systemctl enable --now waydroid_magisk_ota.service`
  * For upstart `sudo systemctl start waydroid_magisk_ota.service`
6. **To avoid any issues it's important to read [FAQ](#faq) before using Kitsune Mask on waydroid.**

# Usage
* a detailed list of all the available commands can be found in [API.md](https://github.com/nitanmarcel/waydroid-magisk/blob/main/API.md)

# FAQ

## What does work?
* root
* zygisk
* modules
* updates
* ~~ota updates survival~~ (Starting with waydroid 1.4.0)

## Waydroid won't start
Note that Waydroid may take longer to boot due to Magisk being set up.

## No internet connection
Try restarting Waydroid using either systemd or init (depending on your system).

## Magisk modules not working or not showing as installed
Currently, modules only work with Kitsune Mask Canary. Download and install the apk in Waydroid, and update by following the instructions in the "Updating" section below.

## Kitsune Mask fails to patch SELinux policy.
  * Use `waydroid_magisk` to update and setup Magisk.

## Updating
* Using Kitsune Mask to install Magisk directly into the system partition.
* Using `waydroid_magisk install --update`.

## Does Zygisk work?
Zygisk only works with Kitsune Mask Canary which gets installed by default.

## I've enabled Zygisk in Kitsune Mask Stable!!
* Run `waydroid_magisk zygisk disable` - to disable zygisk.

## How is this different from other scripts?
magisk_waydroid is a Kitsune Mask manager, bringing all the features from Kitsune Mask manager in your command line. 

## What is Kitsune Mask?
Kitsune Mask is a fork of the official Magisk Manager with the old Magisk Hide feature re-added and other new features. You can find a list of differences between Kitsune Mask and official Magisk [here](https://github.com/HuskyDG/magisk-files/blob/main/note.md#diffs-to-official-magisk).

## Arch Linux
On arch based distributions, `linux-xanmod-anbox` with `linux-xanmod-anbox-headers` (needs `psi=1` in cmdline) from chaotic AUR is recommended, otherwise Kitsune Mask might not work properly.

## Ubuntu Touch
__`waydroid-magisk` is developed to be compatible with almost every Linux OS, including Ubuntu Touch. But a few issues can still occur such as (workarounds included).__
* Readonly filesystem/No space left
  * `sudo waydroid_magisk install --tmpdir /home/phablet/magisk`
* Failed to re-execute lxc-attach via memory file descriptor
  * Use waydroid_magisk via adb
  * or enable ssh `android-gadget-service enable ssh` and ssh to `localhost` (`ssh localhost`)
* CANNOT LINK EXECUTABLE "service": "/system/lib/libcutils.so" is 32-bit instead of 64-bit
  * `sudo env LD_LIBRARY_PATH=/android/system/lib64/ waydroid_magisk {command failing here}`

# Credits
* [Waydroid Team](github.com/waydroid/waydroid)
* Kitsune Mask Maintainer - [HuskyDG](https://github.com/HuskyDG)
* [Others](https://huskydg.github.io/magisk-files/#credits)
