#!/usr/bin/env python3

import os
import sys
import uuid
import base64
import subprocess

##########################################################
# Randomness

def rand_passphrase():
    bytes_ = os.urandom(64)
    return base64.b64encode(bytes_).decode('ascii')

##########################################################
# Vault utility

def print_encrypted_var(var_name, content):
    print('%s: ' % var_name, end='') # '--name' does not work when using stdin
    sys.stdout.flush() # Commit the print() before ansible-vault prints
    with subprocess.Popen(['ansible-vault', 'encrypt_string'],
                          stdin=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, # Hide its output
                          ) as proc:
        proc.stdin.write(content.encode())
        proc.stdin.close()


##########################################################
# libvirt data
print('vm_uuid: %s' % str(uuid.uuid4()))

##########################################################
# cjdns keys
with subprocess.Popen(['/home/cjdns/cjdns/makekeys'],
                      stdout=subprocess.PIPE) as proc:
    line = proc.stdout.readline()
    proc.terminate()
(fe_sk, fe_addr, fe_pk) = line.decode('ascii').split()

print('fe_addr: %s' % fe_addr)
print('fe_pk: %s' % fe_pk)
print_encrypted_var('fe_sk', fe_sk)

##########################################################
# disk keys
print_encrypted_var('disk_passphrase', rand_passphrase())
print_encrypted_var('disk_keyfile', rand_passphrase())

