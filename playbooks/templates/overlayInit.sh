#!/bin/sh
echo "loading overlay kernel module"
modprobe overlay

echo "executing init now"
exec /sbin/init
