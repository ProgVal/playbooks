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

echo "mounting /mnt/__upper_var"
mkdir -p /mnt/__upper_var
mount -t tmpfs tmpfs /mnt/__upper_var

echo "making directories in /mnt/__upper_var"
mkdir /mnt/__upper_var/data
mkdir /mnt/__upper_var/workdir

echo "overlaying /var"
mount -t overlay overlay -o lowerdir=/var,upperdir=/mnt/__upper_var/data,workdir=/mnt/__upper_var/workdir /var

echo "executing init in 5 seconds"
sleep 5
exec /sbin/init
