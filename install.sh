#!/bin/bash

set -e

user=$(whoami)

REQUIREMENTS=(waydroid curl zip gzip)

SHASUM=$(sha256sum install.sh | cut -d ' ' -f1)
REMOTE_SHASUM="$(curl -s https://raw.githubusercontent.com/nitanmarcel/waydroid-magisk-installer/main/sha)"

if [ "$SHASUM" != "$REMOTE_SHASUM" ]; then
    echo "install.sh was modified, or it's outdated."
    read -p "Do you want to continue anyway? (y/n) " answer
    case "$answer" in
        [yY][eE][sS]|[yY]) 
            echo " "
            ;;
        *)
            exit 1
            ;;
    esac
fi

for package in "${REQUIREMENTS[@]}"; do
    if ! which "$package" >/dev/null 2>&1; then
        echo "Error: $package is not installed."
        exit 1
    fi
done

if [ "$user" != "root" ]; then
    echo "This script needs to be ran as a priviliged user!"
    exit 1
fi

if waydroid status | grep -q "RUNNING"; then
    echo "Please stop waydroid before running this script"
    exit 1
fi

WORKDIR=""
if [ $# -eq 0 ]; then
  WORKDIR="$(mktemp -d)/.magisk_waydroid/"
else
  WORKDIR="$1/.magisk_waydroid/"
fi

if [ ! -e "$WORKDIR" ]; then
    mkdir "$WORKDIR/" -p
fi

MAGISK="https://huskydg.github.io/magisk-files/app-release.apk"
RESET="0"

if [ ! -e "$WORKDIR/magisk" ]; then
    mkdir "$WORKDIR/magisk" || true
fi

if [ ! -e "$WORKDIR/system" ]; then
    mkdir "$WORKDIR/system" || true
fi

echo " "

if [ "$SELINUX" == "0" ]; then
    echo "Magisk is not fully supported on kernels with SELinux disabled."
    read -p "Do you wish to continue anyway? (y/n) " answer
    case "$answer" in
        [yY][eE][sS]|[yY]) 
            echo " "
            ;;
        *)
            umount $WORKDIR/system
            rm -rf $WORKDIR
            exit 1
            ;;
    esac
fi

echo "Detecting system.img location"
echo " "

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

if test -e /sys/fs/selinux; then
    HAS_SELINUX="1"
fi

echo "system.img detected at $SYSTEM"

if [ ! -e "/var/lib/waydroid/.magisk_pending" ]; then
    echo "Resizing system.img (current size + 100mb)"
    echo "Run the installer again to install Magisk Delta."
    echo " "

    touch "/var/lib/waydroid/.magisk_pending"

    SYSTEM_SIZE="$(du -m $SYSTEM | cut -f 1)"
    SYSTEM_SIZE_SUM="$(echo $(expr "$SYSTEM_SIZE" + 100))"

    fsck.ext4 -f $SYSTEM
    resize2fs $SYSTEM "$SYSTEM_SIZE_SUM"M
    exit 1
fi

echo "Mounting system.img"
echo " "

mount -o rw,loop $SYSTEM $WORKDIR/system

ARCH=$(cat $WORKDIR/system/system/build.prop | grep ro.product.cpu.abi= | cut -d "=" -f2)
SDK=$(cat $WORKDIR/system/system/build.prop | grep ro.build.version.sdk= | cut -d "=" -f2)
SUPPORTED_SDKS=(30)
BITS=32
SELINUX="0"

if ! printf '%s\0' "${SUPPORTED_SDKS[@]}" | grep -Fxqz -- "$SDK"; then
    echo "SDK $SDK not supported"
    umount $WORKDIR/system
    rm -rf $WORKDIR
    exit 1
fi

if test -d $WORKDIR/system/system/etc/init/magisk; then
    echo "Magisk is already installed."
    echo "By continuing Magisk will reinstall itself!"
    read -p "Do you wish to continue? (y/n) " answer
    case "$answer" in
        [yY][eE][sS]|[yY]) 
            echo "Reinstalling Magisk!"
            echo " "
            ;;
        *)
            umount $WORKDIR/system
            rm -rf $WORKDIR
            exit 1
            ;;
    esac

    rm $WORKDIR/system/sbin -rf
    rm $WORKDIR/system/system/etc/init/magisk -rf
    rm $WORKDIR/system/system/etc/init/bootanim.rc.gz -f

    sed -i '/on post-fs-data/,$d' $WORKDIR/system/system/etc/init/bootanim.rc
    RESET="1"
fi

if [ -e "$(pwd)/magisk-delta.apk" ]; then
    echo "Unpacking Magisk Delta"
    unzip -qq "$(pwd)/magisk-delta.apk" -d $WORKDIR/magisk/
else
    echo "Downloading and unpacking Magisk Delta"
    curl $MAGISK -s --output "$WORKDIR/magisk/magisk-delta.apk"
    unzip -qq "$WORKDIR/magisk/magisk-delta.apk" -d $WORKDIR/magisk/
fi


if [ "$ARCH" = "arm64-v8a" ]; then
    ARCH="arm64-v8a"
    BITS="64"
fi

if [ "$ARCH" = "x86_64" ]; then
    BITS="64"
fi

echo "Patching Waydroid"
echo " "

echo "SDK: $SDK"
echo "ARCHITECTURE: $ARCH"
echo "INSTRUCTIONS: $BITS"
echo "SELINUX: $SELINUX"
echo "KERNEL: $(uname -r)"
echo "REINSTALLING: $RESET"

LIBDIR="$WORKDIR/magisk/lib/$ARCH"

mkdir $WORKDIR/system/system/etc/init/magisk
mkdir $WORKDIR/system/sbin

cp $LIBDIR/libmagisk$BITS.so $WORKDIR/system/system/etc/init/magisk/magisk$BITS

cp $LIBDIR/libbusybox.so $WORKDIR/system/system/etc/init/magisk/busybox

cp $LIBDIR/libmagiskboot.so $WORKDIR/system/system/etc/init/magisk/magiskboot
cp $LIBDIR/libmagiskinit.so $WORKDIR/system/system/etc/init/magisk/magiskinit
cp $LIBDIR/libmagiskpolicy.so $WORKDIR/system/system/etc/init/magisk/magiskpolicy

chmod +x $WORKDIR/system/system/etc/init/magisk/magisk*

X=$(< /dev/urandom tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1)
Y=$(< /dev/urandom tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1)

gzip -ck $WORKDIR/system/system/etc/init/bootanim.rc > $WORKDIR/system/system/etc/init/bootanim.rc.gz

cat <<EOT >> $WORKDIR/system/system/etc/init/bootanim.rc

on post-fs-data
    start logd
    exec - root root -- /system/etc/init/magisk/magisk$BITS --setup-sbin /system/etc/init/magisk
    exec - root root -- /system/etc/init/magisk/magiskpolicy --live --magisk "allow * magisk_file lnk_file *"
    mkdir /sbin/.magisk 700
    mkdir /sbin/.magisk/mirror 700
    mkdir /sbin/.magisk/block 700
    copy /system/etc/init/magisk/config /sbin/.magisk/config
    rm /dev/.magisk_unblock
    start $X
    wait /dev/.magisk_unblock 40
    rm /dev/.magisk_unblock

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


umount $WORKDIR/system
rm -rf $WORKDIR
rm "/var/lib/waydroid/.magisk_pending"

echo "DONE!"
echo "Do not enable zygdisk as it's not currently working"
echo "Always update Magisk from Magisk Delta. Use the direct install into system partition feature in the app."
