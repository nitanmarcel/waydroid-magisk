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
import configparser
import json

WITH_DBUS = True

try:
    import dbus
except ImportError:
    WITH_DBUS = False

logging.basicConfig(
    format="[%(asctime)s] - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S")

VERSION = '1.2.0'

MAGISK_HOST = "https://huskydg.github.io/magisk-files/"
MAGISK_CANARY = "%s/app-release.apk" % MAGISK_HOST

WAYDROID_DIR = "/var/lib/waydroid/"
CONFIG_FILE = os.path.join(WAYDROID_DIR, "waydroid.cfg")

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
        return False
    return True


def has_overlay():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    if "mount_overlays" in config["waydroid"].keys():
        return config["waydroid"]["mount_overlays"].lower() == "true"
    return False


def get_systemimg_path():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return os.path.join(config["waydroid"]["images_path"], "system.img")


def download_obj(url, destination, filename):
    try:
        with urllib.request.urlopen(url) as response:
            with open(os.path.join(destination, filename), "wb") as handle:
                shutil.copyfileobj(response, handle)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            logging.error("Failed to download %s" % filename)
            return
    return True


def download_json(url):
    result = {}
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
            result = json.loads(data.decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            logging.error("Failed to download Magisk Delta channel info")
    return result


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


def is_waydroid_initialized():
    return os.path.exists(CONFIG_FILE)

def is_installed():
    overlay_magisk = os.path.join(WAYDROID_DIR, "overlay/system/etc/init/magisk")
    rootfs_magisk = os.path.join(WAYDROID_DIR, "rootfs/system/etc/init/magisk")
    installed = os.path.exists(overlay_magisk)
    if not has_overlay():
        if len(os.listdir(os.path.join(WAYDROID_DIR, "rootfs"))) > 0:
            installed = os.path.exists(rootfs_magisk)
        else:
            mount_system()
            installed = os.path.exists(overlay_magisk)
            umount_system()
    return installed


def WaydroidContainerDbus():
    return dbus.Interface(dbus.SystemBus().get_object("id.waydro.Container", "/ContainerManager"), "id.waydro.ContainerManager")


def WaydroidSessionDbus():
    return dbus.Interface(dbus.SystemBus().get_object("id.waydro.Session", "/SessionManager"), "id.waydro.SessionManager")

def get_waydroid_session():
    if WITH_DBUS:
        try:
            return WaydroidContainerDbus().GetSession()
        except dbus.exceptions.DBusException:
            return

def xdg_data_home():
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(WAYDROID_DIR, "session.cfg"))
    return cfg["session"]["xdg_data_home"]


def is_running():
    return len(os.listdir(os.path.join(WAYDROID_DIR, "rootfs"))) > 0

def stop_session_if_needed():
    waydroid_session = get_waydroid_session()
    if waydroid_session:
        logging.info("Stopping Waydroid")
        WaydroidContainerDbus().Stop(True)

def restart_session_if_needed():
    waydroid_session = get_waydroid_session()
    if waydroid_session:
        logging.info("Stopping Waydroid")
        WaydroidContainerDbus().Stop(False)
        logging.info("Starting Waydroid")
        WaydroidContainerDbus().Start(waydroid_session)


class WaydroidFreezeUnfreeze:
    def __init__(self, session) -> None:
        self._session = session
    def __enter__(self):
        if self._frozen:
            WaydroidContainerDbus().Unfreeze()
    def __exit__(self, exc_type, exc_value, traceback):
        if self._frozen:
            WaydroidContainerDbus().Freeze()
    @property
    def _frozen(self):
        if self._session:
            return self._session["state"] == "FROZEN"
        else:
            return False

def mount_system():
    if not os.path.exists(OVERLAY):
        os.mkdir(OVERLAY)
    rootfs = get_systemimg_path()
    if len(os.listdir(os.path.join(WAYDROID_DIR, "rootfs"))) > 0:
        return False
    subprocess.run(["e2fsck", "-y", "-f", rootfs], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["resize2fs", rootfs, "2G"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["mount", "-o", "rw,loop", rootfs, OVERLAY], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True

def umount_system():
    mounted = os.path.ismount(OVERLAY)
    while mounted:
        try:
            subprocess.run(["umount", OVERLAY], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as exc:
            pass
        mounted = os.path.ismount(OVERLAY)
        time.sleep(1)

def install(arch, bits, magisk_url, workdir=None, restart_after=True):
    is_root = check_root()
    if not is_root:
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if is_installed():
        logging.error("Magisk Delta already installed!")
        return
    if not has_overlay():
        waydroid_session = get_waydroid_session()
        if waydroid_session:
            stop_session_if_needed()
        mount = mount_system()
        if not mount:
            logging.error("Failed to mount rootfs. Make sure Waydroid is stopped during the installation.")
            return
    if workdir:
        if not os.path.exists(workdir):
            os.makedirs(workdir)
    with tempfile.TemporaryDirectory(dir=workdir) as tempdir:
        logging.info("Downloading Magisk Delta")
        download_obj(magisk_url, tempdir, "magisk-delta.apk")
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
            if not os.path.exists(os.path.join(OVERLAY, "sbin")):
                os.makedirs(os.path.join(OVERLAY, "sbin"))
            if not os.path.exists(os.path.join(OVERLAY, "system/addon.d")):
                os.makedirs(os.path.join(OVERLAY, "system/addon.d"))
        if not has_overlay():
            umount_system()
        if restart_after:
            restart_session_if_needed()
        logging.info("Done")
        return True


def uninstall(restart_after=True):
    is_root = check_root()
    if not is_root:
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed!")
        return
    if not has_overlay():
        waydroid_session = get_waydroid_session()
        if waydroid_session:
            stop_session_if_needed()
        mount = mount_system()
        if not mount:
            logging.error("Failed to mount rootfs. Make sure Waydroid is stopped during the installation.")
            return
    logging.info("Removing Magisk Delta")
    shutil.copyfile(os.path.join(INIT_OVERLAY, "bootanim.rc.gz"), os.path.join(WAYDROID_DIR, "bootanim.rc.gz"))
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

    if has_overlay():
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
    if not has_overlay():
        with gzip.open(os.path.join(WAYDROID_DIR, "bootanim.rc.gz"), "rb") as gzfile:
            with open(os.path.join(INIT_OVERLAY, "bootanim.rc"), "wb") as rcfile:
                shutil.copyfileobj(gzfile, rcfile)
        umount_system()
    os.remove(os.path.join(WAYDROID_DIR, "bootanim.rc.gz"))
    if restart_after:
        restart_session_if_needed()
    logging.info("Done")
    return True

def update(arch, bits, magisk_url, workdir=None):
    uninstalled = uninstall(restart_after=False)
    if uninstalled:
        installed = install(arch, bits, magisk_url=magisk_url, workdir=workdir)
        if installed:
            logging.info("Manually update Magisk Manager after booting Waydroid.")

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
    
    if not has_overlay():
        raise ValueError("OTA survival not supported on non overlay Waydroid")
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
    is_root = check_root()
    status = 0
    result = ""
    if not is_root:
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_running():
        logging.error("Waydroid session is not running")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    waydroid_session = get_waydroid_session()
    with WaydroidFreezeUnfreeze(waydroid_session):
        lxc = os.path.join(WAYDROID_DIR, "lxc")
        command = ["lxc-attach", "-P", lxc, "-n", "waydroid", "--", "/sbin/magisk"]
        command.extend(args)
        proc = subprocess.run(command, env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"}, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if proc.stdout:
            status = 0
            result = proc.stdout.decode()
        elif proc.stderr:
            status = 1
            result = proc.stderr.decode()
    return (status, result)

def magisk_sqlite(query):
    is_root = check_root()
    if not is_root:
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_running():
        logging.error("Waydroid session is not running")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    result = ""
    waydroid_session = get_waydroid_session()
    with WaydroidFreezeUnfreeze(waydroid_session):
        lxc = os.path.join(WAYDROID_DIR, "lxc")
        command = ["lxc-attach", "-P", lxc, "-n", "waydroid", "--", "/sbin/magisk", "--sqlite", query]
        proc = subprocess.run(command, env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"}, universal_newlines=False, stdout=subprocess.PIPE, 
                                stderr=subprocess.DEVNULL)
        result = proc.stdout.decode()
    return result

def install_module(modpath):
    is_root = check_root()
    if not is_root:
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_running():
        logging.error("Waydroid session is not running")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    waydroid_session = get_waydroid_session()
    tmpdir = os.path.join(xdg_data_home(), "waydroid", "data", "waydroid_tmp")
    if not os.path.exists(tmpdir):
        os.makedirs(tmpdir)
    shutil.copyfile(modpath, os.path.join(tmpdir, "module.zip"))
    args = ["--install-module", os.path.join("/data", "waydroid_tmp", "module.zip")]
    magisk_cmd(args)
    os.remove(os.path.join(tmpdir, "module.zip"))
    restart_session_if_needed()

def list_modules():
    is_root = check_root()
    if not is_root:
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_running():
        logging.error("Waydroid session is not running")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    waydroid_session = get_waydroid_session()
    with WaydroidFreezeUnfreeze(waydroid_session):
        modpath = os.path.join(xdg_data_home(), "waydroid", "data", "adb", "modules")
        if not os.path.isdir(modpath):
            logging.error("No Magisk modules are currently installed")
            return
        print("\n".join("- %s" % mod for mod in os.listdir(modpath)))

def remove_module(modname):
    is_root = check_root()
    if not is_root:
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_running():
        logging.error("Waydroid session is not running")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    waydroid_session = get_waydroid_session()
    with WaydroidFreezeUnfreeze(waydroid_session):
        modpath = os.path.join(xdg_data_home(), "waydroid", "data", "adb", "modules")    
        if not os.path.isdir(os.path.join(modpath, modname)):
            logging.error("'%s' is not an installed Magisk module" % modname)
            return
        logging.info("Removing '%s' Magisk module" % modname)
        while os.path.isdir(os.path.join(modpath, modname)):
            shutil.rmtree(os.path.join(modpath, modname))
        logging.info("'%s' Magisk module has been removed" % modname)
        restart_session_if_needed()

def su(args=None):
    is_root = check_root()
    if not is_root:
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_running():
        logging.error("Waydroid session is not running")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    result = ""
    waydroid_session = get_waydroid_session()
    with WaydroidFreezeUnfreeze(waydroid_session):
        lxc = os.path.join(WAYDROID_DIR, "lxc")
        command = ["lxc-attach", "-P", lxc, "-n", "waydroid", "--", "su", "-c", "mknod",  "-m", "666", "/dev/tty", "c", "5", "0", "2>", "/dev/null"]
        subprocess.run(command, env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"})
        command = ["lxc-attach", "-P", lxc, "-n", "waydroid", "--", "su"]
        if args:
            command.append("-c")
            command.extend(args)
        if not args:
            subprocess.run(command, env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"})
        else:
            proc = subprocess.run(command, env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"}, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            result = proc.stdout.decode()
    return result

def get_package(query):
    name = ""
    app_id = 0
    result = su(["pm", "list", "packages -U", "|", "grep", str(query)])
    if result:
        name, app_id = result.split()
        name = name.split(":")[-1]
        app_id = int(app_id.split(":")[-1])
    return (name, app_id)

def main():
    if not is_waydroid_initialized():
        logging.error("Waydroid is not initialized.")
        return
    arch, bits = get_arch()

    parser = argparse.ArgumentParser(description="Magisk Delta installer and manager for Waydroid", prog="waydroid_magisk")
    parser.add_argument("-v", "--version", action="store_true", help="Print version")
    parser.add_argument("-o", "--ota", action="store_true", help="Handles survival during Waydroid updates (overlay only)")

    subparsers = parser.add_subparsers(dest="command")
    parser_install = subparsers.add_parser("install", help="Install Magisk Delta in Waydroid")
    parser_install.add_argument("-u", "--update", action="store_true", help="Update Magisk Delta")
    parser_install.add_argument("-c","--canary", action="store_true", help="Install Magisk Delta canary channel (default canary)")
    parser_install.add_argument("-d","--debug", action="store_true", help="Install Magisk Delta debug channel (default canary)")
    parser_install.add_argument("-t", "--tmpdir", nargs="?", type=str, default="tmpdir", help="Custom path to use as an temporary  directory")

    subparsers.add_parser("remove", help="Remove Magisk Delta from Waydroid")

    parser_modules = subparsers.add_parser("module", help="Manage modules in Magisk Delta")
    parser_modules_subparser = parser_modules.add_subparsers(dest="command_module")
    parser_modules_install = parser_modules_subparser.add_parser("install", help="Install magisk module")
    parser_modules_install.add_argument("MODULE", type=str, help="Path to magisk module to install")
    parser_modules_remove = parser_modules_subparser.add_parser("remove", help="Remove magisk module")
    parser_modules_remove.add_argument("MODULE", type=str, help="Module name to remove")
    parser_modules_list = parser_modules_subparser.add_parser("list", help="List all installed magisk modules")

    parser_su = subparsers.add_parser("su", help="Manage su in Magisk Delta")
    parser_su_subparser = parser_su.add_subparsers(dest="command_su")
    parser_su_subparser.add_parser("shell", help="Opens the magisk su shell")
    parser_su_subparser.add_parser("list", help="Return apps status in su database")
    parser_su_allow = parser_su_subparser.add_parser("allow", help="Allow su access to app")
    parser_su_allow.add_argument("PKG", type=str, help="PKG")
    parser_su_deny = parser_su_subparser.add_parser("deny", help="Deny su access to app")
    parser_su_deny.add_argument("PKG", type=str, help="PKG")


    parser_hide = subparsers.add_parser("magiskhide", help="Execute magisk hide commands")
    parser_hide_subparser = parser_hide.add_subparsers(dest="command_magiskhide")
    parser_hide_subparser.add_parser("status", help="Return the MagiskHide status")
    parser_hide_subparser.add_parser("sulist", help="Return the SuList status")
    parser_hide_subparser.add_parser("enable", help="Enable MagiskHide")
    parser_hide_subparser.add_parser("disable", help="Disable MagiskHide")   
    parser_hide_add = parser_hide_subparser.add_parser("add", help="Add a new target to the hidelist (sulist)")
    parser_hide_add.add_argument("PKG", type=str, help="PKG [PROC]")
    parser_hide_remove = parser_hide_subparser.add_parser("rm", help="Remove target(s) from the hidelist (sulist)")
    parser_hide_remove.add_argument("PKG", nargs="+", type=str, help="PKG [PROC]")
    parser_hide_ls = parser_hide_subparser.add_parser("ls", help="Print the current hidelist (sulist)")


    parser_zygisk = subparsers.add_parser("zygisk", help="Execute zygisk commands")
    parser_zygisk_subparser = parser_zygisk.add_subparsers(dest="command_zygisk")
    parser_zygisk_subparser.add_parser("status", help="Return the zygisk status")
    parser_zygisk_subparser.add_parser("enable", help="Enable zygisk (requires waydroid restart)")
    parser_zygisk_subparser.add_parser("disable", help="Disable zygisk (requires waydroid restart)")

    args = parser.parse_args()

    if args.command == "install":
        magisk_channels = download_json("https://raw.githubusercontent.com/nitanmarcel/waydroid-magisk/main/magisk.json")
        magisk_url = magisk_channels["canary"]
        magisk_url = magisk_channels["canary" if args.canary else "debug" if args.debug else "canary"] # stable is disabled for now
        install_fnc = install
        if args.update:
            install_fnc = update
        if args.tmpdir == "tmpdir":
            install_fnc(arch, bits, magisk_url, restart_after=True)
        else:
            install_fnc(arch, bits, magisk_url=magisk_url, workdir=args.tmpdir, restart_after=True)
    elif args.command == "remove":
        uninstall(restart_after=True)
    elif args.command == "module":
        if args.command_module == "install":
            install_module(args.MODULE)
        elif args.command_module == "remove":
            remove_module(args.MODULE)
        elif args.command_module == "list":
            list_modules()
        else:
            parser_modules.print_help()
    elif args.command == "su":
        if args.command_su == "shell":
            su()
        elif args.command_su == "list":
            result = magisk_sqlite("SELECT * FROM policies")
            for line in result.splitlines():
                _logging, notification, policy, uid, until = line.split("|")
                pkg, uid = get_package(int(uid.split("=")[-1]))
                if pkg:
                    print("- %s | %s" % (pkg, "allowed" if int(policy.split("=")[-1]) == 2 else "denied"))
        elif args.command_su == "allow" or args.command_su == "deny":
            policy = "2" if args.command_su == "allow" else "1"
            pkg, app_id = get_package(args.PKG)
            if not app_id:
                logging.error("Invalid package name")
                return
            magisk_sqlite("REPLACE INTO policies VALUES(%s,%s,0,1,1)" % (app_id, policy))
        else:
            parser_su.print_help()
    elif args.command == "magiskhide":
        cmd = ["magiskhide"]
        if args.command_magiskhide == "status":
            cmd.append("status")
        elif args.command_magiskhide == "sulist":
            cmd.append("sulist")
        elif args.command_magiskhide == "enable":
            cmd.append("enable")
        elif args.command_magiskhide == "disable":
            cmd.append("disable")
        elif args.command_magiskhide == "add":
            cmd.extend(["add", args.PKG])
        elif args.command_magiskhide == "rm":
            cmd.append("rm")
            cmd.extend(args.PKG)
        elif args.command_magiskhide == "ls":
            cmd.append("ls")
        else:
            print(parser_hide.print_help())
        if len(cmd) > 1:
            status, message = magisk_cmd(cmd)
            if status == 1:
                logging.error(message)
    elif args.command == "zygisk":
        if args.command_zygisk == "status":
            result = magisk_sqlite("SELECT value FROM settings WHERE key == 'zygisk'")
            state = False
            if result:
                state = bool(int(result.split("=")[-1]))
                logging.info("Zygisk is %s" % ("enabled" if state else "disabled"))
        elif args.command_zygisk == "enable":
            magisk_sqlite("REPLACE INTO settings (key,value) VALUES('zygisk',1)")
        elif args.command_zygisk == "disable":
            magisk_sqlite("REPLACE INTO settings (key,value) VALUES('zygisk',0)")
        else:
            parser_zygisk.print_help()
    elif args.ota:
        ota()
    elif args.version:
        print(VERSION)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
