#!/usr/bin/python3

import os
import sys 
import time
import shutil
import filecmp

MAGISK_MAIN_FOLDER = "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk"
SBIN_DIR = "/var/lib/waydroid/overlay/sbin"

MAGISK_FILES = [
    # "/var/lib/waydroid/overlay_rw/system/system/addon.d/99-magisk.sh",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/bootanim.rc",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/bootanim.rc.gz",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/boot_patch.sh",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/stub.apk",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/util_functions.sh",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/addon.d.sh",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/magisk64",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/magiskinit",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/magisk.apk",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/busybox",
    # "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/chromeos",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/config",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/magiskpolicy",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/magisk32",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/magiskboot"
]

LAST_MODIFIED_TIME = {}

def copy(source):
    print("Copying Magisk File: %s" % os.path.basename(source))
    dest = source.replace("overlay_rw/system/", "overlay/")
    if os.path.isdir(source):
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
    else:
        if os.path.exists(dest):
            os.remove(dest)
        shutil.copy(source, dest)

def remove(source):
    print("Removing Magisk Delta File '%s'" % os.path.basename(source))
    dest = source.replace("overlay_rw/system/", "overlay/")
    if os.path.exists(dest):
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        else:
            os.remove(dest)
    os.remove(source)
    if os.path.isdir(SBIN_DIR):
        os.rmdir(SBIN_DIR)

def main():
    while True:
        if os.path.exists(MAGISK_MAIN_FOLDER):
            if os.path.isfile(MAGISK_MAIN_FOLDER):
                for mfile in MAGISK_FILES:
                    if os.path.exists(mfile):
                        remove(mfile)
                remove(MAGISK_MAIN_FOLDER)
            else:
                for mfile in MAGISK_FILES:
                    overlay = mfile.replace("overlay_rw/system/", "overlay/")
                    #print(mfile, overlay)
                    if os.path.exists(mfile) and os.path.exists(overlay):
                        if not filecmp.cmp(mfile, overlay):
                            copy(mfile)
                    if os.path.exists(mfile) and not os.path.exists(overlay):
                        copy(mfile)
        time.sleep(1)


if not os.environ.get("WMAGISKD_SERVICE"):
    exit()

main()