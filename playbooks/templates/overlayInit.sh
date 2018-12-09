#!/bin/sh
echo "loading overlay kernel module"
modprobe overlay

echo "mounting /mnt/__middle_etc"
mkdir -p /mnt/__middle_etc
#cat /dev/vdb | cryptsetup luksOpen UUID={{etc_uuid}} {{etc_crypt_target}}
#mount /dev/mapper/{{etc_crypt_target}} /mnt/__middle_etc
cat /dev/vdb | cut -d '' -f1 | tr -d '\n' > /run/etc_keyfile # 'cut' replaces trailing \x00 bytes with a newline, tr removes that newline.
chmod u=r,g=,o= /run/etc_keyfile

echo "mounting /mnt/__upper_etc"
mkdir -p /mnt/__upper_etc
mount -t tmpfs tmpfs /mnt/__upper_etc

echo "making directories in /mnt/__upper_etc"
mkdir /mnt/__upper_etc/datadir
mkdir /mnt/__upper_etc/workdir

echo "overlaying /etc"
#mount -t overlay overlay -o lowerdir=/etc:/mnt/__middle_etc,upperdir=/mnt/__upper_etc/data,workdir=/mnt/__upper_etc/workdir /etc

echo "executing init now"
exec /sbin/init
