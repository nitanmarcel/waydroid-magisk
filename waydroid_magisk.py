#!/usr/bin/env python3

import argparse
import filecmp
import gzip
import logging
import os
import platform
import random
import re
import shutil
import string
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
import subprocess

import dbus

logging.basicConfig(
    format="[%(asctime)s] - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S")

MAGISK_HOST = "https://huskydg.github.io/magisk-files/"
MAGISK_CANARY = "%s/app-release.apk" % MAGISK_HOST

WAYDROID_DIR = "/var/lib/waydroid/"

OVERLAY = os.path.join(WAYDROID_DIR, "overlay")
INIT_OVERLAY = os.path.join(OVERLAY, "system", "etc", "init")
MAGISK_OVERLAY = os.path.join(INIT_OVERLAY, "magisk")

OVERLAY_RW = os.path.join(WAYDROID_DIR, "overlay_rw")
INIT_OVERLAY_RW = os.path.join(OVERLAY, "system", "etc", "init", "magisk")
MAGISK_OVERLAY_RW = os.path.join(INIT_OVERLAY, "magisk")

MAGISK_FILES = [
    "/var/lib/waydroid/overlay_rw/system/system/addon.d/99-magisk.sh",
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
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/chromeos",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/config",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/magiskpolicy",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/magisk32",
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/magiskboot"
]


def check_root():
    if not os.getuid() == 0:
        logging.error("This app needs to be ran as a priviliged user!")
        return


def download_obj(url, destination, filename):
    try:
        with urllib.request.urlopen(url) as response:
            with open(os.path.join(destination, filename), "wb") as handle:
                shutil.copyfileobj(response, handle)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            logging.error("Failed to download %s" % filename)
            return


def get_arch():
    plat = platform.machine()
    if plat == "x86":
        return plat
    if plat == "x86_64":
        with open("/proc/cpuinfo", "r") as cpuinfo:
            if "sse4_2" not in cpuinfo.read():
                return "x86", 32
        return "x86_64", 64
    if plat in ["armv7l", "armv8l"]:
        return "armeabi-v7a", 32
    if plat == "aarch64":
        return "arm64-v8a", 64
    if plat == "i686":
        return "x86_64", 64
    logging.error("%s not supported" % plat)


def is_installed():
    return os.path.exists(os.path.join(WAYDROID_DIR, "overlay/system/etc/init/magisk"))


def WaydroidContainerDbus():
    return dbus.Interface(dbus.SystemBus().get_object("id.waydro.Container", "/ContainerManager"), "id.waydro.ContainerManager")


def WaydroidSessionDbus():
    return dbus.Interface(dbus.SystemBus().get_object("id.waydro.Session", "/SessionManager"), "id.waydro.SessionManager")

def get_waydroid_session():
    try:
        return WaydroidContainerDbus().GetSession()
    except dbus.exceptions.DBusException:
        return None

def restart_session_if_needed():
    waydroid_session = get_waydroid_session()
    if waydroid_session:
        logging.info("Stopping Waydroid")
        WaydroidContainerDbus().Stop()
        logging.info("Starting Waydroid")
        WaydroidContainerDbus().Start(waydroid_session)


class WaydroidFreezeUnfreeze:
    def __init__(self, session) -> None:
        self._session = session
    def __enter__(self):
        if self._frozen:
            WaydroidContainerDbus().Unfreeze()
    def __exit__(self, exc_type, exc_value, tracebac):
        if self._frozen:
            WaydroidContainerDbus().Freeze()
    @property
    def _Pfrozen(self):
        if self._session:
            return self.session["state"] == "FROZEN"
        else:
            return False

def install(arch, bits, workdir=None):
    check_root()
    if is_installed():
        logging.error("Magisk Delta already installed!")
        return
    with tempfile.TemporaryDirectory(dir=workdir) as tempdir:
        logging.info("Downloading Magisk Delta")
        download_obj(MAGISK_CANARY, tempdir, "magisk-delta.apk")
        logging.info("Extracting Magisk Delta")
        with zipfile.ZipFile(os.path.join(tempdir, "magisk-delta.apk")) as handle:
            handle.extractall(tempdir)
        logging.info("Installing Magisk Delta")
        libs = os.path.join(tempdir, "lib", arch)
        if not os.path.exists(MAGISK_OVERLAY):
            os.makedirs(MAGISK_OVERLAY)
        for lib in os.listdir(libs):
            shutil.copyfile(os.path.join(libs, lib), os.path.join(
                MAGISK_OVERLAY, re.match("lib(.*)\.so", lib).group(1)))
            os.chmod(os.path.join(MAGISK_OVERLAY, re.match(
                "lib(.*)\.so", lib).group(1)), 0o775)

        logging.info("Creating bootanim.rc")
        with open(os.path.join(INIT_OVERLAY, "bootanim.rc"), "w+") as handle:
            handle.write("service bootanim /system/bin/bootanimation\n")
            handle.write("\tclass core animation\n")
            handle.write("\tuser graphics\n")
            handle.write("\tgroup graphics audio\n")
            handle.write("\tdisabled\n")
            handle.write("\toneshot\n")
            handle.write("\tioprio rt 0\n")
            handle.write("\ttask_profiles MaxPerformance\n")
            handle.write("\n")
        logging.info("Backup bootanim.rc")
        with open(os.path.join(INIT_OVERLAY, "bootanim.rc"), "rb") as handle:
            with gzip.open(os.path.join(INIT_OVERLAY, "bootanim.rc.gz"), "wb") as ghandle:
                ghandle.writelines(handle)
        # Patch bootanim.rc
        with open(os.path.join(INIT_OVERLAY, "bootanim.rc"), "a") as handle:
            handle.write("\n")
            handle.write("on post-fs-data\n")
            handle.write("\tstart logd\n")
            handle.write(
                "\texec u:r:su:s0 root root -- /system/etc/init/magisk/magisk%s --auto-selinux --setup-sbin /system/etc/init/magisk\n" % str(bits))
            handle.write(
                "\texec u:r:su:s0 root root -- /system/etc/init/magisk/magiskpolicy --live --magisk \"allow * magisk_file lnk_file *\"\n")
            handle.write("\tmkdir /sbin/.magisk 700\n")
            handle.write("\tmkdir /sbin/.magisk/mirror 700\n")
            handle.write("\tmkdir /sbin/.magisk/block 700\n")
            handle.write(
                "\tcopy /system/etc/init/magisk/config /sbin/.magisk/config\n")
            handle.write("\trm /dev/.magisk_unblock\n")
            x = ''.join(random.choice(string.ascii_letters + string.digits)
                        for i in range(15))
            y = ''.join(random.choice(string.ascii_letters + string.digits)
                        for i in range(15))
            handle.write("\tstart %s\n" % x)
            handle.write("\twait /dev/.magisk_unblock 40\n")
            handle.write("\trm /dev/.magisk_unblock\n")
            handle.write("\n\n")

            handle.write("service %s /sbin/magisk --auto-selinux --post-fs-data\n" % x)
            handle.write("\tuser root\n")
            handle.write("\tseclabel u:r:su:s0\n")
            handle.write("\toneshot\n")
            handle.write("\n\n")

            handle.write("service %s /sbin/magisk --auto-selinux --service\n" % y)
            handle.write("\tclass late_start\n")
            handle.write("\tuser root\n")
            handle.write("\tseclabel u:r:su:s0\n")
            handle.write("\toneshot\n")
            handle.write("\n\n")

            handle.write("on property:sys.boot_completed=1\n")
            handle.write("\tmkdir /data/adb/magisk 755\n")
            handle.write(
                "\texec u:r:su:s0 root root -- /sbin/magisk --auto-selinux --boot-complete\n")
            handle.write("\n\n")

            handle.write("on property:init.svc.zygote=restarting\n")
            handle.write("\texec u:r:su:s0 root root -- /sbin/magisk --auto-selinux --zygote-restart")
            handle.write("\n\n")

            handle.write("on property:init.svc.zygote=stopped\n")
            handle.write("\texec u:r:su:s0 root root -- /sbin/magisk --auto-selinux --zygote-restart")
            handle.write("\n")

            logging.info("Finishing installation")
            os.makedirs(os.path.join(OVERLAY, "sbin"))
            os.makedirs(os.path.join(OVERLAY, "system/addon.d"))
            restart_session_if_needed()
            logging.info("Done")


def uninstall():
    check_root()
    if not is_installed():
        logging.error("Magisk Delta is not installed!")
        return
    logging.info("Removing Magisk Delta")
    for file in MAGISK_FILES:
        if os.path.exists(file):
            if os.path.isdir(file):
                os.rmdir(file)
            else:
                os.remove(file)
        file = re.sub("overlay_rw\/system\/", "overlay/", file)
        if os.path.exists(file):
            if os.path.isdir(file):
                os.rmdir(file)
            else:
                os.remove(file)

    if os.path.exists(MAGISK_OVERLAY):
        if os.path.isdir(MAGISK_OVERLAY):
            os.rmdir(MAGISK_OVERLAY)
        else:
            os.remove(MAGISK_OVERLAY)

    if os.path.exists(MAGISK_OVERLAY_RW):
        if os.path.isdir(MAGISK_OVERLAY_RW):
            os.rmdir(MAGISK_OVERLAY_RW)
        else:
            os.remove(MAGISK_OVERLAY_RW)

    if os.path.exists(os.path.join(OVERLAY, "sbin")):
        if os.path.isdir(os.path.join(OVERLAY, "sbin")):
            os.rmdir(os.path.join(OVERLAY, "sbin"))
        else:
            os.remove(os.path.join(OVERLAY, "sbin"))

    if os.path.exists(os.path.join(OVERLAY, "system/addon.d")):
        if os.path.isdir(os.path.join(OVERLAY, "system/addon.d")):
            os.rmdir(os.path.join(OVERLAY, "system/addon.d"))
        else:
            os.remove(os.path.join(OVERLAY, "system/addon.d"))
    restart_session_if_needed()
    logging.info("Done")


def ota():
    # TODO: Clean this mess I wrote a few days ago when I feel like. And maybe try to find a better way to manage this.
    def copy(source):
        logging.info("Copying Magisk File: %s" % os.path.basename(source))
        dest = source.replace("overlay_rw/system/", "overlay/")
        if os.path.isdir(source):
            if os.path.exists(dest):
                shutil.rmtree(dest)
            os.makedirs(dest)
            shutil.copytree(source, dest)
        else:
            if os.path.exists(dest):
                os.remove(dest)
            shutil.copy(source, dest)

    def remove(source):
        logging.info("Removing Magisk Delta File '%s'" %
                     os.path.basename(source))
        dest = re.sub("overlay_rw\/system\/", "overlay/", source)
        if os.path.exists(dest):
            if os.path.isdir(dest):
                shutil.rmtree(dest)
            else:
                os.remove(dest)
        os.remove(source)
        if os.path.isdir(os.path.join(OVERLAY, "sbin")):
            os.rmdir(os.path.join(OVERLAY, "sbin"))
    while True:
        if os.path.exists(MAGISK_OVERLAY):
            if os.path.isfile(MAGISK_OVERLAY):
                for mfile in MAGISK_FILES:
                    if os.path.exists(mfile):
                        remove(mfile)
                remove(MAGISK_OVERLAY)
            else:
                for mfile in MAGISK_FILES:
                    overlay = mfile.replace("overlay_rw/system/", "overlay/")
                    if os.path.exists(mfile) and os.path.exists(overlay):
                        if not filecmp.cmp(mfile, overlay):
                            copy(mfile)
                    if os.path.exists(mfile) and not os.path.exists(overlay):
                        copy(mfile)
        time.sleep(1)

def magisk_cmd(args):
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    waydroid_session = get_waydroid_session()
    if not waydroid_session:
        logging.error("Waydroid session is not started")
        return
    elif waydroid_session["state"] != "RUNNING":
        logging.error("Waydroid status is %s" % waydroid_session["status"])
        return
    with WaydroidFreezeUnfreeze(waydroid_session):
        lxc = os.path.join(WAYDROID_DIR, "lxc")
        command = ["lxc-attach", "-P", lxc, "-n", "waydroid", "--", "/sbin/magisk"]
        command.extend(args)
        subprocess.run(command, env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"})


def install_module(modpath):
    check_root()
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    waydroid_session = get_waydroid_session()
    if not waydroid_session:
        logging.error("Waydroid session is not started")
        return
    elif waydroid_session["state"] != "RUNNING":
        logging.error("Waydroid status is %s" % waydroid_session["status"])
        return
    tmpdir = os.path.join(waydroid_session["waydroid_data"], "waydroid_tmp")
    if not os.path.exists(tmpdir):
        os.makedirs(tmpdir)
    shutil.copyfile(modpath, os.path.join(tmpdir, "module.zip"))
    args = ["--install-module", os.path.join("/data", "waydroid_tmp", "module.zip")]
    magisk_cmd(args)
    os.remove(os.path.join(tmpdir, "module.zip"))
    restart_session_if_needed()

def list_modules():
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    waydroid_session = get_waydroid_session()
    if not waydroid_session:
        logging.error("Waydroid session is not started")
        return
    elif waydroid_session["state"] != "RUNNING":
        logging.error("Waydroid status is %s" % waydroid_session["state"])
        return
    with WaydroidFreezeUnfreeze(waydroid_session):
        modpath = os.path.join(waydroid_session["waydroid_data"], "adb", "modules")
        if not os.path.isdir(modpath):
            logging.error("No Magisk modules are currently installed")
            return
        print("\n".join("- %s" % mod for mod in os.listdir(modpath)))

def remove_module(modname):
    check_root()
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    waydroid_session = get_waydroid_session()
    if not waydroid_session:
        logging.error("Waydroid session is not started")
        return
    with WaydroidFreezeUnfreeze(waydroid_session):
        if waydroid_session["state"] != "RUNNING":
            logging.error("Waydroid status is %s" % waydroid_session["state"])
            return
        modpath = os.path.join(waydroid_session["waydroid_data"], "adb", "modules")    
        if not os.path.isdir(os.path.join(modpath, modname)):
            logging.error("'%s' is not an installed Magisk module" % modname)
            return
        logging.info("Removing '%s' Magisk module" % modname)
        while os.path.isdir(os.path.join(modpath, modname)):
            shutil.rmtree(os.path.join(modpath, modname))
        logging.info("'%s' Magisk module has been removed" % modname)
        restart_session_if_needed()

def su():
    check_root()
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    waydroid_session = get_waydroid_session()
    if not waydroid_session:
        logging.error("Waydroid session is not started")
        return
    with WaydroidFreezeUnfreeze(waydroid_session):
        if waydroid_session["state"] != "RUNNING":
            logging.error("Waydroid status is %s" % waydroid_session["state"])
            return
        lxc = os.path.join(WAYDROID_DIR, "lxc")
        command = ["lxc-attach", "-P", lxc, "-n", "waydroid", "--", "su", "-c", "mknod",  "-m", "666", "/dev/tty", "c", "5", "0", "2>", "/dev/null"]
        subprocess.run(command, env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"})
        command = ["lxc-attach", "-P", lxc, "-n", "waydroid", "--", "su"]
        subprocess.run(command, env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"})


def main():
    arch, bits = get_arch()
    parser = argparse.ArgumentParser(
        description='Magisk Delta installer for Waydroid.')
    parser.add_argument("-i", "--install", nargs='?', type=str,
                        const="tmpdir", help="Install Magisk Delta in Waydroid")
    parser.add_argument("-r", "--remove", action="store_true",
                        help="Remove Magisk Delta from Waydroid")
    parser.add_argument("-o", "--ota", action="store_true",
                        help="Handles OTA updates in Waydroid with Magisk Delta")
    parser.add_argument("--install-module", help="Installs a Magisk module")
    parser.add_argument("--remove-module", help="Removes a Magisk module")
    parser.add_argument("--list-modules", action="store_true", help="Lists all installed Magisk modules")
    parser.add_argument("--su", action="store_true", help="Starts Magisk SU inside waydroid.")
    args = parser.parse_args()

    if args.install:
        if args.install == "tmpdir":
            install(arch, bits)
        else:
            install(arch, bits, args.install)   
    elif args.remove:
        uninstall()
    elif args.install_module:
        install_module(args.install_module)
    elif args.remove_module:
        remove_module(args.remove_module)
    elif args.list_modules:
        list_modules()
    elif args.su:
        su()
    elif args.ota:
        if not os.environ.get("WMAGISKD_SERVICE"):
            exit()
        ota()
    else:
        logging.info("Run waydroid_magisk -h for usage information.")


if __name__ == "__main__":
    main()
