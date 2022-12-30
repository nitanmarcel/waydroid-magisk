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
* Open it and complete the first time setup. It will try to reboot waydroid but will fail. You can restart Waydroid either by using systemd or init (depending on your system).

## Waydroid doesn't start anymore
* Waydroid will take longer to boot due to Magisk being set up.

## I have no internet connection
* In that case try to restart Waydroid again either by using systemd or init (depending on your system).

## Magisk module don't work/don't show up as installed
* Currently modules work only with Magisk Delta Canary. Download and install the apk in waydroid, and update by following the instructions in the [How to update](#how-to-update) section in this document.

## How to update
* Using Magisk Delta, we have an option to install Magisk dirrectly into the system partition. Always update from the magisk app, and not this script!

## Does zygdisk work?
* Not yet. Looking into it in the future.
* This also means that any modules that uses zygdisk won't work. (Riru, LSposed, etc.)

## What is Magisk Delta?
* It's a fork of the official Magisk Manager, with the old Magisk Hide feature re-added to the app. Useful for us since we don't have zygdisk.
* https://huskydg.github.io/magisk-files/docs/faq.html

## How is this different from the other scripts?
* I've tried my best to reproduce what magisk does when it installs itself. 
