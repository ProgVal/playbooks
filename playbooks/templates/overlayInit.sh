#!/bin/sh
echo "loading overlay kernel module"
modprobe overlay

echo "preparing /mnt/__middle_etc"
mkdir -p /mnt/__middle_etc
#cat /dev/vdb | cryptsetup luksOpen UUID={{etc_uuid}} {{etc_crypt_target}}
#mount /dev/mapper/{{etc_crypt_target}} /mnt/__middle_etc
cat /dev/vdb | cut -d '' -f1 | tr -d '\n' > /run/etc_keyfile # 'cut' replaces trailing \x00 bytes with a newline, tr removes that newline.
chmod u=r,g=,o= /run/etc_keyfile

echo "executing init now"
exec /sbin/init
