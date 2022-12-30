# Magisk installer on Waydroid

## Requirements
* Waydroid (duh)
* curl
* zip

## How to install
* Make sure you've stoped Waydroid either by using systemd or init (depending on your system).
* Download install.sh``
* `chmod +x ./install.sh`
* `sudo ./install.sh`
* Restart Waydroid either by using systemd or init (depending on your system).
* Install [Magisk Delta](https://huskydg.github.io/magisk-files/) inside Waydroid
* Open it and complete the first-time setup. It will try to reboot waydroid but will fail. You can restart Waydroid either by using systemd or init (depending on your system).

## Waydroid doesn't start anymore
* Waydroid will take longer to boot due to Magisk being set up.

## I have no internet connection
* In that case try to restart Waydroid again either by using systemd or init (depending on your system).

## Magisk modules don't work/doesn't show up as installed
* Currently modules work only with Magisk Delta Canary. Download and install the apk in waydroid, and update by following the instructions in the [How to update](#how-to-update) section in this document.

## How to update?
* Using Magisk Delta, we have the option to install Magisk directly into the system partition. Always update from the magisk app, and not this script!

## Does it survives waydroid updates?
* If the android system is updated, magisk gets removed and you need to run `install.sh` again to install it.

## Does zygisk work?
* Zygisk only works on devices with selinux enabled or by using Magisk Debug. Any attempt to enable it without selinux enabled or any other versions will crash Waydroid. (A fix is on its way)

## How is this different from the other scripts?
* Runs Magisk Delta, a fork of Magisk with some reimplemented features such as magisk hide, and better support of Android emulators.
* Follows the same installation workflow as Magisk. This also allows users to update Magisk from within the Magisk Delta Manager, instead of relying on the installer script from this repository/

## What is Magisk Delta?
* It's a fork of the official Magisk Manager, with the old Magisk Hide feature re-added to the app. Useful for us since we don't have zygisk.
* [Diffs to official Magisk](https://github.com/HuskyDG/magisk-files/blob/main/note_stable.md#diffs-to-official-magisk)
