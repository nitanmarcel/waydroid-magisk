#!/usr/bin/env python3

import argparse
import configparser
import contextlib
import datetime
import filecmp
import gzip
import json
import logging
import os
import platform
import random
import re
import shutil
import string
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

WITH_DBUS = True

try:
    import dbus
except ImportError:
    WITH_DBUS = False

logging.basicConfig(
    format="[%(asctime)s] - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S")

VERSION = '1.2.9'

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
    "/var/lib/waydroid/overlay_rw/system/system/etc/init/magisk/magiskboot"]


# UTILS

def WaydroidContainerDbus():
    return dbus.Interface(
        dbus.SystemBus().get_object(
            "id.waydro.Container", "/ContainerManager"),
        "id.waydro.ContainerManager")


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
        return self._session["state"] == "FROZEN" if self._session else False


def mount_system():
    if has_overlay():
        return True
    if is_running():
        return False
    if not os.path.exists(OVERLAY):
        os.mkdir(OVERLAY)
    rootfs = get_systemimg_path()
    subprocess.run(["e2fsck", "-y", "-f", rootfs],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["resize2fs", rootfs, "2G"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tries = 5
    for x in range(tries):
        with contextlib.suppress(subprocess.CalledProcessError):
            subprocess.run(["mount", "-o", "rw,loop", rootfs, OVERLAY],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.ismount(OVERLAY):
            return True
        time.sleep(1)
    logging.info("Failed to mount waydroid system")
    return False


def umount_system():
    tries = 5
    for x in range(tries):
        with contextlib.suppress(subprocess.CalledProcessError):
            subprocess.run(
                ["umount", OVERLAY],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.ismount(OVERLAY):
            return True
    time.sleep(1)
    logging.info("Failed to umount waydroid system")
    return False


class SystemMount:
    def __enter__(self):
        return mount_system()
    def __exit__(self, exc_type, exc_val, exc_tb):
        umount_system()


def download_obj(url, destination, filename):
    try:
        with urllib.request.urlopen(url) as response:
            with open(os.path.join(destination, filename), "wb") as handle:
                shutil.copyfileobj(response, handle)
    except urllib.error.HTTPError as exc:
        raise ValueError("Failed to download %s: %s" % (filename, exc.code))


def download_json(url, scope):
    result = {}
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
            result = json.loads(data.decode())
    except urllib.error.HTTPError as exc:
        raise ValueError("Failed to download %s : %s" % (scope, exc.code))
    return result


def is_running():
    waydroid_session = get_waydroid_session()
    if not waydroid_session:
        return os.path.exists(os.path.join(WAYDROID_DIR, "session.cfg"))
    return waydroid_session.get("state") is not None

def is_root():
    return os.getuid() == 0


def is_waydroid_initialized():
    return os.path.exists(CONFIG_FILE)


def has_overlay():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    if "mount_overlays" in config["waydroid"].keys():
        return config["waydroid"]["mount_overlays"].lower() == "true"
    return False


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
    raise ValueError("%s not supported" % plat)


def get_waydroid_session():
    if WITH_DBUS:
        try:
            return WaydroidContainerDbus().GetSession()
        except dbus.exceptions.DBusException:
            return


def get_systemimg_path():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return os.path.join(config["waydroid"]["images_path"], "system.img")


def xdg_data_home():
    waydroid_session = get_waydroid_session()
    if waydroid_session:
        return waydroid_session["xdg_data_home"]
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(WAYDROID_DIR, "session.cfg"))
    return cfg["session"]["xdg_data_home"]


def stop_session_if_needed():
    waydroid_session = get_waydroid_session()
    if waydroid_session:
        logging.info("Stopping Waydroid")
        WaydroidContainerDbus().Stop(True)


def restart_session_if_needed():
    try:
        _restart_session_if_needed()
    except KeyboardInterrupt:
        logging.info("Canceled")


def _restart_session_if_needed():
    waydroid_session = get_waydroid_session()
    seconds = 5
    if waydroid_session:
        for i in range(seconds):
            logging.info("Restarting Waydroid in %s (press ^C to cancel)" %
                  (seconds - i))
            time.sleep(1)
        logging.info("Stopping Waydroid")
        WaydroidContainerDbus().Stop(False)
        logging.info("Starting Waydroid")
        WaydroidContainerDbus().Start(waydroid_session)
    elif is_running():
        for i in range(seconds):
            logging.info(
                "Stopping Waydroid in %s (press ^C to cancel)" %
                (seconds - i))
            time.sleep(1)
        lxc = os.path.join(WAYDROID_DIR, "lxc")
        command = ["lxc-attach", "-P", lxc, "-n",
                   "waydroid", "--", "service", "call", "waydroidhardware", "4"]
        logging.info("Stopping waydroid")
        subprocess.run(command,
                       env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"})
        logging.info("Starting Waydroid")


# Manager

def su(args=None, pipe=True):
    if not is_root():
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
        command = [
            "lxc-attach", "-P", lxc, "-n", "waydroid", "--", "su", "-c",
            "mknod", "-m", "666", "/dev/tty", "c", "5", "0", "2>", "/dev/null"]
        subprocess.run(
            command,
            env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"})
        command = ["lxc-attach", "-P", lxc, "-n", "waydroid", "--", "su"]
        if args:
            command.append("-c")
            command.extend(args)
        if not args:
            subprocess.run(
                command,
                env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"}, 
                stdout=subprocess.PIPE if pipe else None, 
                stderr=subprocess.DEVNULL)
        else:
            proc = subprocess.run(
                command,
                env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"},
                stdout=subprocess.PIPE if pipe else None,
                stderr=subprocess.DEVNULL)
            if proc.stdout:
                result = proc.stdout.decode()
    return result


def magisk_cmd(args, pipe=True):
    pipe = subprocess.PIPE if pipe else None

    status = 0
    result = ""
    if not is_root():
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
        command = ["lxc-attach", "-P", lxc, "-n",
                   "waydroid", "--", "/sbin/magisk"]
        command.extend(args)
        proc = subprocess.run(
            command,
            env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"},
            stderr=pipe, stdout=pipe)
        if proc.stdout:
            status = 0
            result = proc.stdout.decode()
        elif proc.stderr:
            status = 1
            result = proc.stderr.decode()
    return (status, result)


def magisk_sqlite(query):
    if not is_root():
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
        command = ["lxc-attach", "-P", lxc, "-n", "waydroid",
                   "--", "/sbin/magisk", "--sqlite", query]
        proc = subprocess.run(
            command,
            env={"PATH": os.environ['PATH'] + ":/system/bin:/vendor/bin"},
            universal_newlines=False, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL)
        result = proc.stdout.decode()
    return result


def list_modules():
    if not is_root():
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
        modpath = os.path.join(
            xdg_data_home(), "waydroid", "data", "adb", "modules")
        if not os.path.isdir(modpath):
            logging.error("No Magisk modules are currently installed")
            return
        print("\n".join("- %s" % mod for mod in os.listdir(modpath)))


def remove_module(modname):
    if not is_root():
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
        modpath = os.path.join(
            xdg_data_home(), "waydroid", "data", "adb", "modules")
        if not os.path.isdir(os.path.join(modpath, modname)):
            logging.error("'%s' is not an installed Magisk module" % modname)
            return
        logging.info("Removing '%s' Magisk module" % modname)
        while os.path.isdir(os.path.join(modpath, modname)):
            shutil.rmtree(os.path.join(modpath, modname))
        logging.info("'%s' Magisk module has been removed" % modname)
        restart_session_if_needed()


def get_package(query):
    name = ""
    app_id = 0
    result = su(["pm", "list", "packages -U", "|", "grep", str(query)])
    if result:
        name, app_id = result.split()
        name = name.split(":")[-1]
        app_id = int(app_id.split(":")[-1])
    return (name, app_id)


def magisk_log(save=False):
    if not is_root():
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_running():
        logging.error("Waydroid session is not running")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    if not save:
        su(["tail", "-f", "/cache/magisk.log"], False)
    else:
        save_to = os.path.join(xdg_data_home(),
                               "waydroid_magisk", "magisk_log_%s.log" %
                               datetime.datetime.now().strftime(
                                   "%Y-%m-%d_%H:%M:%S"))
        if not os.path.isdir(os.path.basename(save_to)):
            os.makedirs(os.path.basename(save_to))
        with open(save_to, "w") as out:
            if (
                os.path.isdir("/sys/fs/selinux")
                and len(os.listdir("/sys/fs/selinux")) > 0
            ):
                out.write(
                    "!!!!!! If you're seeing this you're running with SELinux enabled which shouldn't work on Waydroid !!!!!!\n\n")
            out.write("---Detected Device Info---\n\n")
            out.write("isAB=false\n")
            out.write("isSAR=false\n")
            out.write("ramdisk=true\n")
            uname = os.uname()
            out.write("kernel=%s %s %s %s\n" % (uname.sysname,
                      uname.machine, uname.release, uname.version))
            proc = subprocess.run(
                ["waydroid", "--version"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            out.write("waydroid arch=%s\n" % get_arch()[0])
            out.write("waydroid version=%s" % proc.stdout.decode())

            out.write("\n\n---System Properties---\n\n")
            out.write(su(["getprop"]))

            out.write("\n\n---Environment Variables---\n\n")
            out.write(su(["env"]))

            out.write("\n\n---System MountInfo---\n\n")
            out.write(su(["cat", "/proc/self/mountinfo"]))

            out.write("\n---Manager Logs---\n")
            out.write(su("cat", "/cache/magisk.log"))
            logging.info("Logs saved to: %s" % save_to)


def magisk_status():
    if not is_root():
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_running():
        logging.error("Waydroid session is not running")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    daemon_running = bool(su(["pidof", "magiskd"]))
    logging.info("Daemon: %s" % ("Running" if daemon_running else "Stopped"))
    if not daemon_running:
        if os.path.isfile("/var/log/syslog"):
            with open("/var/log/syslog", "r") as dmesg:
                error = "Abort message: 'stack corruption detected (-fstack-protector)'"
                if dmesg.read().find(error) > -1:
                    logging.error(error)
    logging.info("Magisk Version: %s" % su(["magisk", "su", "--version"]))


def install_module(modpath):
    if not is_root():
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_running():
        logging.error("Waydroid session is not running")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    waydroid_session = get_waydroid_session()
    tmpdir = os.path.join(xdg_data_home(), "waydroid",
                          "data", "adb", "magisk_tmp")
    if not os.path.exists(tmpdir):
        os.makedirs(tmpdir)
    shutil.copyfile(modpath, os.path.join(tmpdir, "module.zip"))
    args = ["--install-module",
            os.path.join("/data", "adb", "magisk_tmp", "module.zip")]
    magisk_cmd(args, pipe=False)
    os.remove(os.path.join(tmpdir, "module.zip"))
    restart_session_if_needed()


def list_modules():
    if not is_root():
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
        modpath = os.path.join(
            xdg_data_home(), "waydroid", "data", "adb", "modules")
        if not os.path.isdir(modpath):
            logging.error("No Magisk modules are currently installed")
            return
        print("\n".join("- %s" % mod for mod in os.listdir(modpath)))


def remove_module(modname):
    if not is_root():
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
        modpath = os.path.join(
            xdg_data_home(), "waydroid", "data", "adb", "modules")
        if not os.path.isdir(os.path.join(modpath, modname)):
            logging.error("'%s' is not an installed Magisk module" % modname)
            return
        logging.info("Removing '%s' Magisk module" % modname)
        while os.path.isdir(os.path.join(modpath, modname)):
            shutil.rmtree(os.path.join(modpath, modname))
        logging.info("'%s' Magisk module has been removed" % modname)
        restart_session_if_needed()


# Installer

def is_installed():
    if is_running():
        magisk_dir = os.path.join(WAYDROID_DIR, "rootfs", "system", "etc", "init", "magisk")
    elif has_overlay():
        magisk_dir = os.path.join(
            WAYDROID_DIR, "overlay/system/etc/init/magisk")
    else:
        with SystemMount():
            magisk_dir = os.path.join(
                WAYDROID_DIR, "overlay/system/etc/init/magisk")
            return os.path.exists(magisk_dir)
    return os.path.isdir(magisk_dir)

def is_set_up():
    magisk_init = os.path.join(
        MAGISK_OVERLAY, "magisk%s" % get_arch()[-1])
    if not has_overlay():
        magisk_init = os.path.join(
            WAYDROID_DIR, "rootfs", "system", "etc", "init", "magisk",
            "magisk%s" % get_arch()[-1])
    magisk_data = os.path.join(xdg_data_home(
    ), "waydroid", "data", "adb", "magisk", "magisk%s" % get_arch()[-1])
    return os.path.exists(magisk_data) and filecmp.cmp(
        magisk_init, magisk_data, shallow=False)


def backup_bootanim():
    logging.info("Backing up bootanim.rc")
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
    with open(os.path.join(INIT_OVERLAY, "bootanim.rc"), "rb") as handle:
        with gzip.open(os.path.join(INIT_OVERLAY, "bootanim.rc.gz"), "wb") as ghandle:
            ghandle.writelines(handle)


def patch_bootanim(bits):
    logging.info("Patching bootanim.rc")

    x = ''.join(
        random.choice(string.ascii_letters + string.digits)
        for _ in range(15)
    )
    y = ''.join(
        random.choice(string.ascii_letters + string.digits)
        for _ in range(15)
    )

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
        handle.write("\tstart %s\n" % x)
        handle.write("\twait /dev/.magisk_unblock 40\n")
        handle.write("\trm /dev/.magisk_unblock\n")
        handle.write("\n\n")

        handle.write(
            "service %s /sbin/magisk --auto-selinux --post-fs-data\n" % x)
        handle.write("\tuser root\n")
        handle.write("\tseclabel u:r:su:s0\n")
        handle.write("\toneshot\n")
        handle.write("\n\n")

        handle.write(
            "service %s /sbin/magisk --auto-selinux --service\n" % y)
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
        handle.write(
            "\texec u:r:su:s0 root root -- /sbin/magisk --auto-selinux --zygote-restart")
        handle.write("\n\n")

        handle.write("on property:init.svc.zygote=stopped\n")
        handle.write(
            "\texec u:r:su:s0 root root -- /sbin/magisk --auto-selinux --zygote-restart")
        handle.write("\n")


def install(arch, bits, magisk_channel, workdir=None,
            restart_after=True, with_manager=False):
    if not is_root():
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if is_installed():
        logging.error("Magisk Delta already installed!")
        return
    stop_session_if_needed()
    with SystemMount() as mount:
        if not mount:
            logging.error(
                "Failed to mount rootfs. Make sure Waydroid is stopped during the installation.")
            return
        if workdir and not os.path.exists(workdir):
            os.makedirs(workdir)
        with tempfile.TemporaryDirectory(dir=workdir) as tempdir:
            magisk = download_json(
                "https://raw.githubusercontent.com/HuskyDG/magisk-files/main/%s.json" % magisk_channel,
                "Magisk Delta channels")
            logging.info("Downloading Magisk Delta: %s-%s" % (magisk_channel, magisk["magisk"]["version"]))
            download_obj(magisk["magisk"]["link"], tempdir, "magisk-delta.apk")
            logging.info("Extracting Magisk Delta")
            with zipfile.ZipFile(os.path.join(tempdir, "magisk-delta.apk")) as handle:
                handle.extractall(tempdir)
            logging.info("Installing Magisk Delta")
            libs = os.path.join(tempdir, "lib", arch)
            if not os.path.exists(MAGISK_OVERLAY):
                os.makedirs(MAGISK_OVERLAY)
            for lib in os.listdir(libs):
                shutil.copyfile(
                    os.path.join(libs, lib),
                    os.path.join(MAGISK_OVERLAY, re.match("lib(.*)\\.so", lib).group(1)),
                )
                os.chmod(
                    os.path.join(MAGISK_OVERLAY, re.match("lib(.*)\\.so", lib).group(1)),
                    0o775,
                )
            if bits == 64:
                if arch == "arm64-v8a":
                    magisk32 = os.path.join(
                        tempdir, "lib", "armeabi-v7a", "libmagisk32.so")
                elif arch == "x86_64":
                    magisk32 = os.path.join(
                        tempdir, "lib", "x86", "libmagisk32.so")
                shutil.copyfile(magisk32, os.path.join(MAGISK_OVERLAY, "magisk32"))
                os.chmod(os.path.join(MAGISK_OVERLAY, "magisk32"), 0o775)
            assets = os.path.join(tempdir, "assets")
            extra_copy = ["util_functions.sh", "addon.d.sh", "boot_patch.sh"]
            for extra in extra_copy:
                shutil.copyfile(os.path.join(assets, extra),
                                os.path.join(MAGISK_OVERLAY, extra))
            if with_manager:
                shutil.copyfile(os.path.join(tempdir, "magisk-delta.apk"),
                                os.path.join(MAGISK_OVERLAY, "magisk.apk"))

            backup_bootanim()
            patch_bootanim(bits)
            logging.info("Finishing installation")
            if not os.path.exists(os.path.join(OVERLAY, "sbin")):
                os.makedirs(os.path.join(OVERLAY, "sbin"))
            if not os.path.exists(os.path.join(OVERLAY, "system/addon.d")):
                os.makedirs(os.path.join(OVERLAY, "system/addon.d"))
    if restart_after:
        restart_session_if_needed()
    logging.info("Done")
    logging.info(
        "Run waydroid_magisk setup after waydroid starts again or install Magisk Delta Manager")


def update(arch, bits, magisk_channel, restart_after=False,
           workdir=None, with_manager=False):
    uninstalled = uninstall(restart_after=False)
    if uninstalled:
        installed = install(arch, bits, magisk_channel,
                            workdir=workdir, with_manager=with_manager)
        if installed:
            logging.info(
                "Manually update Magisk Manager after booting Waydroid.")


def setup():
    if not is_root():
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_running():
        logging.error("Waydroid session is not running")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed")
        return
    su(["rm", "-rf", "/data/adb/magisk"])
    su(["mkdir", "-p", "/data/adb/magisk"])
    su(["chmod", "700", "/data/adb"])
    su(["cp", "/system/etc/init/magisk/*", "/data/adb/magisk"])
    su(["chmod", "-R", "755", "/data/adb/magisk/"])
    su(["chown", "-R", "0:0", "/data/adb/magisk"])
    restart_session_if_needed()


def uninstall(restart_after=True):
    if not is_root():
        logging.error("This command needs to be ran as a priviliged user!")
        return
    if not is_installed():
        logging.error("Magisk Delta is not installed!")
        return
    stop_session_if_needed()
    with SystemMount() as mount:
        if not mount:
            logging.error(
                "Failed to mount rootfs. Make sure Waydroid is stopped during the installation.")
            return
        logging.info("Removing Magisk Delta")
        shutil.copyfile(os.path.join(INIT_OVERLAY, "bootanim.rc.gz"),
                        os.path.join(WAYDROID_DIR, "bootanim.rc.gz"))
        for file in MAGISK_FILES:
            if os.path.exists(file):
                if os.path.isdir(file):
                    shutil.rmtree(file)
                else:
                    os.remove(file)
            file = re.sub("overlay_rw\\/system\\/", "overlay/", file)
            if os.path.exists(file):
                if os.path.isdir(file):
                    shutil.rmtree(file)
                else:
                    os.remove(file)

        if os.path.exists(MAGISK_OVERLAY):
            if os.path.isdir(MAGISK_OVERLAY):
                shutil.rmtree(MAGISK_OVERLAY)
            else:
                os.remove(MAGISK_OVERLAY)

        if os.path.exists(MAGISK_OVERLAY_RW):
            if os.path.isdir(MAGISK_OVERLAY_RW):
                shutil.rmtree(MAGISK_OVERLAY_RW)
            else:
                os.remove(MAGISK_OVERLAY_RW)

        if has_overlay():
            if os.path.exists(os.path.join(OVERLAY, "sbin")):
                if os.path.isdir(os.path.join(OVERLAY, "sbin")):
                    shutil.rmtree(os.path.join(OVERLAY, "sbin"))
                else:
                    os.remove(os.path.join(OVERLAY, "sbin"))

            if os.path.exists(os.path.join(OVERLAY, "system/addon.d")):
                if os.path.isdir(os.path.join(OVERLAY, "system/addon.d")):
                    shutil.rmtree(os.path.join(OVERLAY, "system/addon.d"))
                else:
                    os.remove(os.path.join(OVERLAY, "system/addon.d"))
        if not has_overlay():
            with gzip.open(os.path.join(WAYDROID_DIR, "bootanim.rc.gz"), "rb") as gzfile:
                with open(os.path.join(INIT_OVERLAY, "bootanim.rc"), "wb") as rcfile:
                    shutil.copyfileobj(gzfile, rcfile)
    os.remove(os.path.join(WAYDROID_DIR, "bootanim.rc.gz"))
    if restart_after:
        restart_session_if_needed()
    logging.info("Done")
    return True


# OTA

def ota():
    # TODO: Clean this mess I wrote a few days ago when I feel like. And maybe
    # try to find a better way to manage this.
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
        dest = re.sub("overlay_rw\\/system\\/", "overlay/", source)
        if os.path.exists(dest):
            if os.path.isdir(dest):
                shutil.rmtree(dest)
            else:
                os.remove(dest)
        os.remove(source)
        if os.path.isdir(os.path.join(OVERLAY, "sbin")):
            shutil.rmtree(os.path.join(OVERLAY, "sbin"))

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
                    if (
                        os.path.exists(mfile)
                        and os.path.exists(overlay)
                        and not filecmp.cmp(mfile, overlay)
                    ):
                        copy(mfile)
                    if os.path.exists(mfile) and not os.path.exists(overlay):
                        copy(mfile)
        time.sleep(1)


def main():
    if os.path.exists("/sys/fs/selinux") and len(os.listdir("/sys/fs/selinux")) > 0:
        logging.error("Magisk Delta doesn't support SELinux in Waydroid")
        return
    if not is_waydroid_initialized():
        logging.error("Waydroid is not initialized.")
        return
    arch, bits = get_arch()

    parser = argparse.ArgumentParser(
        description="Magisk Delta installer and manager for Waydroid",
        prog="waydroid_magisk")
    parser.add_argument("-v", "--version",
                        action="store_true", help="Print version")
    parser.add_argument(
        "-o", "--ota", action="store_true",
        help="Handles survival during Waydroid updates (overlay only)")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("status", help="Query Magisk status")
    parser_install = subparsers.add_parser(
        "install", help="Install Magisk Delta in Waydroid")
    parser_install.add_argument(
        "-c", "--canary", action="store_true",
        help="Install Magisk Delta canary channel (default canary)")
    parser_install.add_argument(
        "-d", "--debug", action="store_true",
        help="Install Magisk Delta debug channel (default canary)")
    parser_install.add_argument(
        "-t", "--tmpdir", nargs="?", type=str, default="tmpdir",
        help="Custom path to use as an temporary  directory")
    parser_install.add_argument(
        "-m", "--manager", action="store_true",
        help="Also install Magisk Delta Manager")

    parser_install = subparsers.add_parser(
        "update", help="Update Magisk Delta in Waydroid")
    parser_install.add_argument(
        "-c", "--canary", action="store_true",
        help="Update Magisk Delta canary channel (default canary)")
    parser_install.add_argument(
        "-d", "--debug", action="store_true",
        help="Update Magisk Delta debug channel (default canary)")
    parser_install.add_argument(
        "-t", "--tmpdir", nargs="?", type=str, default="tmpdir",
        help="Custom path to use as an temporary  directory")
    parser_install.add_argument(
        "-m", "--manager", action="store_true",
        help="Also install Magisk Delta Manager")

    subparsers.add_parser("setup", help="Setup magisk env")

    subparsers.add_parser("remove", help="Remove Magisk Delta from Waydroid")

    parser_log = subparsers.add_parser("log", help="Follow magisk log.")
    parser_log.add_argument(
        "-s", "--save", action="store_true", help="Save magisk log locally")

    parser_modules = subparsers.add_parser(
        "module", help="Manage modules in Magisk Delta")
    parser_modules_subparser = parser_modules.add_subparsers(
        dest="command_module")
    parser_modules_install = parser_modules_subparser.add_parser(
        "install", help="Install magisk module")
    parser_modules_install.add_argument(
        "MODULE", type=str, help="Path to magisk module to install")
    parser_modules_remove = parser_modules_subparser.add_parser(
        "remove", help="Remove magisk module")
    parser_modules_remove.add_argument(
        "MODULE", type=str, help="Module name to remove")
    parser_modules_list = parser_modules_subparser.add_parser(
        "list", help="List all installed magisk modules")

    parser_su = subparsers.add_parser("su", help="Manage su in Magisk Delta")
    parser_su_subparser = parser_su.add_subparsers(dest="command_su")
    parser_su_subparser.add_parser("shell", help="Opens the magisk su shell")
    parser_su_subparser.add_parser(
        "list", help="Return apps status in su database")
    parser_su_allow = parser_su_subparser.add_parser(
        "allow", help="Allow su access to app")
    parser_su_allow.add_argument("PKG", type=str, help="PKG")
    parser_su_deny = parser_su_subparser.add_parser(
        "deny", help="Deny su access to app")
    parser_su_deny.add_argument("PKG", type=str, help="PKG")

    parser_hide = subparsers.add_parser(
        "magiskhide", help="Execute magisk hide commands")
    parser_hide_subparser = parser_hide.add_subparsers(
        dest="command_magiskhide")
    parser_hide_subparser.add_parser(
        "status", help="Return the MagiskHide status")
    parser_hide_subparser.add_parser("sulist", help="Return the SuList status")
    parser_hide_subparser.add_parser("enable", help="Enable MagiskHide")
    parser_hide_subparser.add_parser("disable", help="Disable MagiskHide")
    parser_hide_add = parser_hide_subparser.add_parser(
        "add", help="Add a new target to the hidelist (sulist)")
    parser_hide_add.add_argument("PKG", type=str, help="PKG [PROC]")
    parser_hide_remove = parser_hide_subparser.add_parser(
        "rm", help="Remove target(s) from the hidelist (sulist)")
    parser_hide_remove.add_argument(
        "PKG", nargs="+", type=str, help="PKG [PROC]")
    parser_hide_ls = parser_hide_subparser.add_parser(
        "ls", help="Print the current hidelist (sulist)")

    parser_zygisk = subparsers.add_parser(
        "zygisk", help="Execute zygisk commands")
    parser_zygisk_subparser = parser_zygisk.add_subparsers(
        dest="command_zygisk")
    parser_zygisk_subparser.add_parser(
        "status", help="Return the zygisk status")
    parser_zygisk_subparser.add_parser(
        "enable", help="Enable zygisk (requires waydroid restart)")
    parser_zygisk_subparser.add_parser(
        "disable", help="Disable zygisk (requires waydroid restart)")

    args = parser.parse_args()

    if args.command == "status":
        magisk_status()
    elif args.command == "install" or args.command == "update":
        # stable is disabled for now
        magisk_channel = "canary" if args.canary else "debug" if args.debug else "canary"
        install_fnc = update if args.command == "update" else install
        if args.tmpdir == "tmpdir":
            install_fnc(arch, bits, magisk_channel, restart_after=True,
                        with_manager=args.manager)
        else:
            install_fnc(
                arch, bits, magisk_channel, workdir=args.tmpdir,
                restart_after=True, with_manager=args.manager)
    elif args.command == "setup":
        setup()
    elif args.command == "remove":
        uninstall(restart_after=True)
    elif args.command == "log":
        magisk_log(save=args.save)
    elif args.command == "module":
        if is_running() and not is_set_up():
            logging.error("Incomplete magisk setup")
            return
        if args.command_module == "install":
            install_module(args.MODULE)
        elif args.command_module == "remove":
            remove_module(args.MODULE)
        elif args.command_module == "list":
            list_modules()
        else:
            parser_modules.print_help()
    elif args.command == "su":
        if is_running() and not is_set_up():
            logging.error("Incomplete magisk setup")
            return
        if args.command_su == "shell":
            su()
        elif args.command_su == "list":
            result = magisk_sqlite("SELECT * FROM policies")
            for line in result.splitlines():
                _logging, notification, policy, uid, until = line.split("|")
                pkg, uid = get_package(int(uid.split("=")[-1]))
                if pkg:
                    print(
                        "- %s | %s" %
                        (pkg, "allowed"
                         if int(policy.split("=")[-1]) == 2 else "denied"))
        elif args.command_su in ["allow", "deny"]:
            policy = "2" if args.command_su == "allow" else "1"
            pkg, app_id = get_package(args.PKG)
            if not app_id:
                logging.error("Invalid package name")
                return
            magisk_sqlite("REPLACE INTO policies VALUES(%s,%s,0,1,1)" %
                          (app_id, policy))
        else:
            parser_su.print_help()
    elif args.command == "magiskhide":
        if is_running() and not is_set_up():
            logging.error("Incomplete magisk setup")
            return
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
            parser_hide.print_help()
        if len(cmd) > 1:
            status, message = magisk_cmd(cmd)
            if status == 1:
                logging.error(message)
    elif args.command == "zygisk":
        if is_running() and not is_set_up():
            logging.error("Incomplete magisk setup")
            return
        if args.command_zygisk == "status":
            result = magisk_sqlite(
                "SELECT value FROM settings WHERE key == 'zygisk'")
            state = result and int(result.split("=")[-1]) == 1
            logging.info("Zygisk is %s" %
                         ("enabled" if state else "disabled"))
        elif args.command_zygisk == "enable":
            magisk_sqlite(
                "REPLACE INTO settings (key,value) VALUES('zygisk',1)")
        elif args.command_zygisk == "disable":
            magisk_sqlite(
                "REPLACE INTO settings (key,value) VALUES('zygisk',0)")
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
