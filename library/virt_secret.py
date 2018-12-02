#!/usr/bin/python

# Copyright: (c) 2018, Theo Ouzhinski <touzhinski@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
    module: virt_secret
    short_description: Manages Libvirt secrets
    description:
        - Manages Libvirt secrets.
    version_added: "2.8"
    author: "Theo Ouzhinski (@theo-o)"
    options:
        uuid:
            description:
                - The UUID of the secret being managed.
                - Must be in the format specified by RFC4122.
                - Either this or I(secret) must be used to identify the secret in question.
        secret:
            description:
                - A Base64-encoded secret value.
                - Either this or I(uuid) must be used to identify the secret in question.
        usage:
            description:
                - Describes what the secret is used for.
                - Required when I(state=present).
            choices:
                - volume
                - ceph
                - iscsi
                - tls
        usage_element:
            description:
                - Required when usage is defined.
                - See L(the Libvirt docs, https://libvirt.org/formatsecret.html) for more information.
        description:
            description:
                - A human-readable description of the secret''s purpose
                - Not required
        ephemeral:
            description:
                - Whether the secret should only be kept in memory.
            type: bool
        private:
            description:
                - Whether the secret should not be revealed to a caller of libvirt.
            type: bool
        state:
            description:
                - Specify what state you want the secret to be in.
            required: true
            choices:
                - present
                - absent
    notes:
        - Check mode is supported for this module.
    requirements:
        - libvirt
'''

EXAMPLES = '''
- name: Define a Ceph secret without a value
  virt_secret:
    uuid: 50f71783-f894-4acc-8054-4e8f270c4f4b
    usage: ceph
    usage_element: client.libvirt secret
    private: no
    ephemeral: no
    state: present

- name: Define a Ceph secret with a value and description (with random UUID)
  virt_secret:
    secret: AQBHCbtT6APDHhAA5W00cBchwkQjh3dkKsyPjw==
    usage: ceph
    usage_element: another client.libvirt secret
    private: no
    ephemeral: no
    state: present

- name: Remove a secret with given UUID
  virt_secret:
    uuid: 50f71783-f894-4acc-8054-4e8f270c4f4b
    state: absent

- name: Remove a secret with given value
  virt_secret:
    secret: AQBHCbtT6APDHhAA5W00cBchwkQjh3dkKsyPjw==
    state: absent
'''

RETURN = '''
uuid:
    description: UUID of changed secret else an empty string
    returned: always
    type: string
    sample: 50f71783-f894-4acc-8054-4e8f270c4f4b
'''

STATE_CHOICES = ['present', 'absent']
USAGE_CHOICES = ['volume', 'ceph', 'iscsi', 'tls']

TYPE_TO_ELEMENT = dict(volume='volume',
                       ceph='name',
                       iscsi='target',
                       tls='name')


from xml.etree import ElementTree as ET
from os import remove
from uuid import UUID
from tempfile import mkstemp
from base64 import b64encode, b64decode

from ansible.module_utils.basic import AnsibleModule


def list_secrets(module, bin_path):
    command = "{0} -q secret-list".format(bin_path)

    rc, stdout, stderr = module.run_command(command)
    secret_list = []
    for line in stdout.splitlines():
        rc, value, stderr = get_secret_value(module, bin_path, line.strip().split("  ")[0])
        if rc != 0:
            value = ""
        secret_list.append(dict(
            uuid=line.strip().split("  ")[0],
            usage=line.strip().split("  ")[1].strip(),
            value=value.strip()))

    return secret_list


def check_usage(module, bin_path, usage, usage_element):
    all_secrets = list_secrets(module, bin_path)
    for sct_slug in all_secrets:
        if sct_slug['usage'] == "{0} {1}".format(usage, usage_element):
            module.fail_json(msg="A secret already exists with given usage and usage_element.", **result)


def get_secret_value(module, bin_path, uuid):
    return module.run_command("{0} -q secret-get-value {1}".format(bin_path, uuid))


def get_secret(module, bin_path, uuid, secret):
    all_secrets = list_secrets(module, bin_path)

    for sct in all_secrets:
        if uuid and uuid == sct['uuid']:
            return sct
        if secret and secret == sct['value']:
            return sct

    return None


def define_secret(module, bin_path, uuid, secret, usage, usage_element, description, ephemeral, private):
    global result

    root = ET.Element('secret')
    if ephemeral:
        root.set('ephemeral', 'yes')
    else:
        root.set('ephemeral', 'no')

    if private:
        root.set('private', 'yes')
    else:
        root.set('private', 'no')

    if uuid:
        uuid_element = ET.SubElement(root, 'uuid')
        uuid_element.text = uuid

    if description:
        description_element = ET.SubElement(root, 'description')
        description_element.text = description

    usage_elmnt = ET.SubElement(root, 'usage')
    usage_elmnt.set('type', usage)
    usage_sbelmnt = ET.SubElement(usage_elmnt, TYPE_TO_ELEMENT[usage])
    usage_sbelmnt.text = usage_element

    if not module.check_mode:
        tree = ET.ElementTree(element=root)
        f, path = mkstemp()

        try:
            tree.write(path)
        except Exception as err:
            remove(path)
            raise Exception(err)

        rc, stdout, stderr = module.run_command("{0} secret-define {1}".format(bin_path, path))
        remove(path)
        if rc != 0:
            module.fail_json(msg="Defining secret failed.", stderr=stderr, **result)
        uuid = stdout.split(" ")[1]
        result['uuid'] = uuid
    else:
        result['changed'] = True

    if secret:
        set_value(module, bin_path, uuid, secret)


def modify_secret(module, bin_path, uuid, secret, usage, usage_element, description, ephemeral, private):
    global result
    sct = get_secret(module, bin_path, uuid, secret)
    if sct is None:
        return None

    rc, stdout, stderr = module.run_command("{0} secret-dumpxml {1}".format(bin_path, sct['uuid']))
    if rc != 0:
        module.fail_json(msg="Error getting secret XML.", **result)
    xml = stdout.strip()

    root = ET.fromstring(xml)

    needs_change = False

    if uuid and uuid != sct['uuid']:
        needs_change = True

    is_ephemeral = root.attrib['ephemeral']
    if (ephemeral and is_ephemeral == 'no') or (not ephemeral and is_ephemeral == 'yes'):
        needs_change = True

    is_private = root.attrib['private']
    if (private and is_private == 'no') or (not private and is_private == 'yes'):
        needs_change = True

    usage_elmnt = root.find('usage')
    if usage and usage_elmnt.attrib['type'] != usage:
        needs_change = True

    sub = usage_elmnt.find(TYPE_TO_ELEMENT[usage])
    if usage_element and sub.text != usage_element:
        needs_change = True

    if description and root.find('description') and root.find('description').text != description:
        needs_change = True

    if needs_change:
        rc, stdout, stderr = module.run_command("{0} secret-undefine {1}".format(bin_path, sct['uuid']))
        check_usage(module, bin_path, usage, usage_element)
        return define_secret(module, bin_path, uuid, secret, usage, usage_element, description, ephemeral, private)
    else:
        return sct['uuid']


def set_value(module, bin_path, uuid, secret_value):
    global result
    if not module.check_mode:
        rc, stdout, stderr = module.run_command("{0} secret-set-value {1} {2}".format(bin_path, uuid, secret_value))
    result['changed'] = True


def remove_secret(module, bin_path, uuid, secret):
    global result
    sct = get_secret(module, bin_path, uuid, secret)
    if sct is None:
        return None

    if not module.check_mode:
        rc, stdout, stderr = module.run_command("{0} secret-undefine {1}".format(bin_path, sct["uuid"]))
        if rc != 0:
            module.fail_json(msg=stdout, **result)
        result['changed'] = True
        return sct["uuid"]
    else:
        result['changed'] = True
        return None


def main():
    module = AnsibleModule(
        argument_spec=dict(
            uuid=dict(type='str'),
            secret=dict(type='str'),
            usage=dict(type='str', choices=USAGE_CHOICES),
            usage_element=dict(type='str'),
            description=dict(type='str'),
            ephemeral=dict(type='bool'),
            private=dict(type='bool'),
            state=dict(type='str', choices=STATE_CHOICES, required=True)),
        supports_check_mode=True)

    binary_path = module.get_bin_path('virsh')

    uuid = module.params.get('uuid', None)
    secret = module.params.get('secret', None)
    usage = module.params.get('usage', None)
    usage_element = module.params.get('usage_element', None)
    description = module.params.get('description', None)
    ephemeral = module.params.get('ephemeral', None)
    private = module.params.get('private', None)
    state = module.params.get('state', None)

    global result
    result = dict(
        changed=False,
        uuid='')

    if not binary_path:
        module.fail_json(msg="Exectuable virsh not found on system.", **result)

    if uuid is None and secret is None:
        module.fail_json(msg="Either a UUID or a secret must be defined.", **result)

    if secret:
        try:
            b64encode(b64decode(secret)) == secret
        except Exception:
            module.fail_json(msg="Secret must be Base64-encoded.", **result)

    if uuid:
        try:
            UUID(uuid)
        except Exception:
            module.fail_json(msg="uuid not compliant with RFC 4122.", **result)

    if state == 'present':
        sct = get_secret(module, binary_path, uuid, secret)

        if usage is None:
            module.fail_json(msg="Usage must be defined.", **result)
        if usage and usage_element is None:
            module.fail_json(msg="Description must be defined with a usage.", **result)

        if sct:
            uuid = modify_secret(module, binary_path, uuid, secret, usage, usage_element, description, ephemeral, private)
            if uuid:
                result['uuid'] = uuid
        else:
            check_usage(module, binary_path, usage, usage_element)
            uuid = define_secret(module, binary_path, uuid, secret, usage, usage_element, description, ephemeral, private)
            if uuid:
                result['uuid'] = uuid
    elif state == 'absent':
        uuid = remove_secret(module, binary_path, uuid, secret)
        if uuid:
            result['uuid'] = uuid

    module.exit_json(**result)


if __name__ == '__main__':
    main()
