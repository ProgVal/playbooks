#!/bin/sh
echo "loading overlay kernel module"
modprobe overlay

echo "mounting /mnt/__upper_etc"
mkdir -p /mnt/__upper_etc
mount -t tmpfs tmpfs /mnt/__upper_etc

echo "making directories in /mnt/__upper_etc"
mkdir /mnt/__upper_etc/data
mkdir /mnt/__upper_etc/workdir

echo "overlaying /etc"
mount -t overlay overlay -o lowerdir=/etc,upperdir=/mnt/__upper_etc/data,workdir=/mnt/__upper_etc/workdir /etc

echo "executing init now"
exec /sbin/init
