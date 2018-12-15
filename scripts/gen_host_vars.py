#!/usr/bin/env python3

import os
import sys
import uuid
import base64
import tempfile
import subprocess

(_, hostname) = sys.argv

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

##########################################################
# SSH keys

with tempfile.TemporaryDirectory() as tempdir:
    keyfile_path = os.path.join(tempdir, 'ssh_host_ed25519_key')
    cmd = ['ssh-keygen', '-q', '-t', 'ed25519', '-f', keyfile_path,
           '-N', '' # no passphrase
          ]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as proc:
        proc.stdin.close()
    with open(keyfile_path) as fd:
        sk = fd.read()
    with open(keyfile_path + '.pub') as fd:
        pk = fd.read()

(pk_type, pk_value, _) = pk.strip().split()

print('ssh_host_keys:')
print('  ed25519:')
print('    pk: %s %s root@%s' % (pk_type, pk_value, hostname))
print_encrypted_var('    sk', sk)
