#!/bin/bash

set -e

user=$(whoami)

if [ "$user" != "root" ]; then
    echo "This script needs to be ran as a priviliged user!"
    exit 1
fi

if waydroid status | grep -q "RUNNING"; then
    echo "Please stop waydroid before running this script"
    exit 1
fi

ARCH="$(uname -m)"

VARIANT=32


if [ "$ARCH" = "aarch64" ]; then
    ARCH="arm64-v8a"
    VARIANT="64"
fi

if [ "$ARCH" = "armhf" ]; then
    ARCH="armeabi-v7a"
fi

if [ "$ARCH" = "x86_64" ]; then
    VARIANT="64"
fi

MAGISK="https://huskydg.github.io/download/magisk/25.2-delta-5.apk"
WORKDIR="$(mktemp -d)"

mkdir "$WORKDIR/magisk" || true
mkdir "$WORKDIR/system" || true

echo Downloading and unpacking Magisk Delta

wget $MAGISK -qO "$WORKDIR/magisk/magisk.apk"
unzip "$WORKDIR/magisk/magisk.apk" -d $WORKDIR/magisk/

echo Detecting system.img location

SYSTEM="none"

if [ -e "/usr/share/waydroid-extra/images/system.img" ]; then
    SYSTEM="/usr/share/waydroid-extra/images/system.img"
fi

if [ -e "/var/lib/waydroid/images/system.img" ]; then
    SYSTEM="/var/lib/waydroid/images/system.img"
fi

if [ "$SYSTEM" = "none" ]; then
    echo "Can't find waydroid system image"
    exit 1
fi

echo "system.img detected at $SYSTEM"

LIBDIR="$WORKDIR/magisk/lib/$ARCH"

echo "Resizing system.img (current size + 100mb)"

SYSTEM_SIZE="$(du -m $SYSTEM | cut -f 1)"
SYSTEM_SIZE_SUM="$(echo $(expr "$SYSTEM_SIZE" + 100))"

fsck.ext4 -f $SYSTEM
resize2fs $SYSTEM "$SYSTEM_SIZE_SUM"M

echo "Mounting system.img"

mount -o rw,loop $SYSTEM $WORKDIR/system

echo "Patching Waydroid"

if test -d $WORKDIR/system/system/etc/init/magisk; then
    echo "Magisk is already installed. To update it, open the Magisk Delta app, installation, and select the option direct install into system partition"
    umount $WORKDIR/system
    exit 1
fi

mkdir $WORKDIR/system/system/etc/init/magisk

if [ -e "$LIBDIR/libmagisk64.so" ]; then
    cp $LIBDIR/libmagisk64.so $WORKDIR/system/system/etc/init/magisk/magisk64
fi
if [ -e "$LIBDIR/libmagisk32.so" ]; then
    cp $LIBDIR/libmagisk32.so $WORKDIR/system/system/etc/init/magisk/magisk32
fi

cp $LIBDIR/libbusybox.so $WORKDIR/system/system/etc/init/magisk/busybox

cp $LIBDIR/libmagiskboot.so $WORKDIR/system/system/etc/init/magisk/magiskboot
cp $LIBDIR/libmagiskinit.so $WORKDIR/system/system/etc/init/magisk/magiskinit
cp $LIBDIR/libmagiskpolicy.so $WORKDIR/system/system/etc/init/magisk/magiskpolicy

mkdir $WORKDIR/system/sbin

X=$(cat /dev/urandom | tr -dc '[:alpha:]' | fold -w ${1:-20} | head -n 1)
Y=$(cat /dev/urandom | tr -dc '[:alpha:]' | fold -w ${1:-20} | head -n 1)

cat <<EOT >> $WORKDIR/system/system/etc/init/bootanim.rc

echo "Variant is $VARIANT"

on post-fs-data
    start logd
    exec - root root -- /system/etc/init/magisk/mount-sbin.sh
    copy /system/etc/init/magisk/magisk$VARIANT /sbin/magisk$VARIANT
    chmod 0755 /sbin/magisk$VARIANT
    symlink /sbin/magisk$VARIANT /sbin/magisk
    exec - root root -- /system/etc/init/magisk/magisk$VARIANT --install
    copy /system/etc/init/magisk/magisk32 /sbin/magisk$VARIANT
    chmod 0755 /sbin/magisk$VARIANT
    copy /system/etc/init/magisk/magiskinit /sbin/magiskinit
    chmod 0755 /sbin/magiskinit
    copy /system/etc/init/magisk/magiskpolicy /sbin/magiskpolicy
    chmod 0755 /sbin/magiskpolicy
    exec - root root -- /sbin/magiskpolicy --live --magisk "allow * magisk_file lnk_file *"
    exec - root root -- /sbin/magiskinit -x manager  /sbin/stub.apk
    write /dev/.magisk_livepatch 0
    mkdir /sbin/.magisk 700
    mkdir /sbin/.magisk/mirror 700
    mkdir /sbin/.magisk/block 700
    copy /system/etc/init/magisk/config /sbin/.magisk/config
    rm /dev/.magisk_unblock
    start $X
    wait /dev/.magisk_unblock 40
    rm /dev/.magisk_unblock
    rm /dev/.magisk_livepatch

service $X /sbin/magisk --post-fs-data
    user root
    seclabel -
    oneshot

service $Y /sbin/magisk --service
    class late_start
    user root
    seclabel -
    oneshot

on property:sys.boot_completed=1
    mkdir /data/adb/magisk 755
    exec - root root -- /sbin/magisk --boot-complete

on property:init.svc.zygote=restarting
    exec - root root -- /sbin/magisk --zygote-restart
   
on property:init.svc.zygote=stopped
    exec - root root -- /sbin/magisk --zygote-restart

EOT

cat <<EOT >> $WORKDIR/system/system/etc/init/magisk/mount-sbin.sh
#!/bin/sh

## TODO : FIX
## https://github.com/topjohnwu/Magisk/blob/57d83635c6512f5e58753c7a1ae2d515c18cb70f/scripts/avd_magisk.sh#L22
### Should have been handled by magisk64/32 in post-fs-data. But it has to be executable to work and it get's "restricted" from being moved around

mount -t tmpfs -o 'mode=0755' tmpfs /sbin
chcon u:object_r:rootfs:s0 /sbin
EOT

chmod 755 $WORKDIR/system/system/etc/init/magisk/mount-sbin.sh

umount $WORKDIR/system

echo "DONE!"
echo "Do not enable zygdisk as it's not currently working"
echo "Always update Magisk from Magisk Delta. Use the direct install into system partition feature in the app."
