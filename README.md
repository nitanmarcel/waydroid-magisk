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
3. Make the script executable with `chmod +x ./install.sh`.
4. Run the script with `sudo ./install.sh`.
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
* ~~ota updates survival~~ (requires [#580](https://github.com/waydroid/waydroid/pull/580)/Not implemented. )

## Waydroid won't start
Note that Waydroid may take longer to boot due to Magisk being set up.

## No internet connection
Try restarting Waydroid using either systemd or init (depending on your system).

## Magisk was installed but I have no root
Is possible, depending on your OS and setup that Magisk won't be able to properly work on your Waydroid installation.
 * This isn't related to Magisk but to something that your OS or kernel does, or to a broken Waydroid installation.
 * To check if you are affected, after Waydroid booted run `sudo waydroid shell` then inside Waydroid shell run `dmesg` and check for anything related to Magisk. Last known logs from a broken installation is:
 ```
 [10830.400377] DEBUG: pid: 49, tid: 49, name: magiskd  >>> magiskd <<<
[10830.400493] DEBUG: uid: 0
[10830.400606] DEBUG: signal 6 (SIGABRT), code -1 (SI_QUEUE), fault addr --------
[10830.401020] DEBUG: Abort message: 'stack corruption detected (-fstack-protector)'
[10830.401165] DEBUG:     rax 0000000000000000  rbx 0000000000000031  rcx 00007fdc5b2de758  rdx 0000000000000006
[10830.401275] DEBUG:     r8  0000000000000001  r9  0000000000000001  r10 00007fffbe8d8760  r11 0000000000000246
[10830.401379] DEBUG:     r12 0000000000000009  r13 0000000000000000  r14 00007fffbe8d8758  r15 0000000000000031
[10830.401490] DEBUG:     rdi 0000000000000031  rsi 0000000000000031
[10830.401597] DEBUG:     rbp 000000000000000d  rsp 00007fffbe8d8748  rip 00007fdc5b2de758
[10830.403010] DEBUG: 
[10830.403020] DEBUG: backtrace:
[10830.403385] DEBUG:       #00 pc 000000000009d758  /apex/com.android.runtime/lib64/bionic/libc.so (syscall+24) (BuildId: 082396c74061b06f8ce2a645b3a60e84)
[10830.403523] DEBUG:       #01 pc 00000000000a06c2  /apex/com.android.runtime/lib64/bionic/libc.so (abort+194) (BuildId: 082396c74061b06f8ce2a645b3a60e84)
[10830.403656] DEBUG:       #02 pc 00000000000b5433  /apex/com.android.runtime/lib64/bionic/libc.so (__stack_chk_fail+19) (BuildId: 082396c74061b06f8ce2a645b3a60e84)
[10830.403775] DEBUG:       #03 pc 0000000000020523  /sbin/magisk64 (BuildId: 7d7ae72288e42018ac0f0dcb0557b36f132e1fd5)
[10830.403893] DEBUG:       #04 pc 0000000000020615  /sbin/magisk64 (BuildId: 7d7ae72288e42018ac0f0dcb0557b36f132e1fd5)
[10830.404161] DEBUG:       #05 pc 000000000001ff5d  /sbin/magisk64 (BuildId: 7d7ae72288e42018ac0f0dcb0557b36f132e1fd5)
[10830.404436] DEBUG:       #06 pc 000000000001db1b  /sbin/magisk64 (BuildId: 7d7ae72288e42018ac0f0dcb0557b36f132e1fd5)
 ``` 

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
