#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024,  Yoan Müller <ymueller@puzzle.ch>, Puzzle ITC
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""system_high_availability_settings module: Module to configure general OPNsense system settings"""

__metaclass__ = type

# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html
# fmt: off

DOCUMENTATION = r'''
---
author:
  - Yoan Müller (@LuminatiHD)
module: system_high_availability_settings
short_description: Configure high availability settings
description:
  - Module to configure high availability system settings
options:
  synchronize_states:
    description: "pfsync transfers state insertion, update, and deletion messages between firewalls. Each firewall sends these messages out via multicast on a specified interface, using the PFSYNC protocol ([IP Protocol 240](https://www.openbsd.org/faq/pf/carp.html)). It also listens on that interface for similar messages from other firewalls, and imports them into the local state table. This setting should be enabled on all members of a failover group."
    type: bool
    default: false
  synchronize_interface:
    description: "If Synchronize States is enabled, it will utilize this interface for communication."
    type: str
    required: true
  synchronize_peer_ip:
    description: "Setting this option will force pfsync to synchronize its state table to this IP address. The default is directed multicast. "
    type: string
    required: false
  synchronize_config_to_ip:
    description: "IP address of the firewall to which the selected configuration sections should be synchronized."
    type: string
    required: false
  remote_system_username:
    description: "Enter the web GUI username of the system entered above for synchronizing your configuration."
    type: string
    required: false
  remote_system_password:
    description: "Enter the web GUI password of the system entered above for synchronizing your configuration."
    type: string
    required: false
  services_to_synchronize:
    description: "List of config items to synchronize to the other firewall."
    type: list
    elements: ["Dashboard", "User and Groups", "Auth Servers", "Certificates", "DHCPD", "DHCPv4: Relay", "DHCPDv6", "DHCPv6: Relay", "Virtual IPs", "Static Routes", "Network Time", "Netflow / Insight", "Cron", "System Tunables", "Web GUI", "Dnsmasq DNS", "FRR", "Shaper", "Captive Portal", "IPsec", "Kea DHCP", "Monit System Monitoring", "OpenSSH", "OpenVPN", "Firewall Groups", "Firewall Rules", "Firewall Schedules", "Firewall Categories", "Firewall Log Templates", "Aliases". "NAT", "Intrusion Detection", "Unbound DNS", "WireGuard" ]
    required: false
'''

EXAMPLES = r'''
---
- name: Enable State sync via CARP
  puzzle.opnsense.system_high_availability_settings:
    synchronize_interface: "sync"
    synchronize_states: true

- name: Synchronize Configuration Settings
  puzzle.opnsense.system_high_availability_settings:
    synchronize_config_to_ip: 192.168.1.3
    synchronize_system_username: root
    synchronize_system_passowrd: v3rys3cure
    services_to_synchronize:
      - "Dashboard"
      - "Users and Groups"
      - "Auth Servers"
      - "Certificates"
      - "Virtual IPs"
      - "OpenVPN"
      - "Firewall Groups"
      - "Firewall Rules"
      - "Firewall Schedules"
      - "Aliases"
      - "NAT"
'''
RETURN = ''''''

# fmt: on


from typing import Optional, List
from ansible.module_utils.basic import AnsibleModule
from xml.etree import ElementTree
from ansible_collections.puzzle.opnsense.plugins.module_utils.config_utils import (
    OPNsenseModuleConfig,
)


def check_hasync_node(config: OPNsenseModuleConfig):
    # When an opnsense instance is created, the hasync block does not exist at all.
    # This function checks if this element exists in the tree, and adds it if no.
    if config.get("parent_node") is None:
        ElementTree.SubElement(config._config_xml_tree,
                               config._config_maps["system_high_availability_settings"]["parent_node"])
        # default settings when nothing is selected
        synchronize_interface(config, "lan")
        remote_system_synchronization(config, None, None, None)


def synchronize_states(config: OPNsenseModuleConfig, params: bool):
    if params and config.get("synchronize_states") is None:
        config.set(value="on", setting="synchronize_states")
    elif not params and config.get("synchronize_states") is not None:
        config._config_xml_tree.find("hasync").remove(config.get("synchronize_states"))


def synchronize_interface(config: OPNsenseModuleConfig, params: str):
    config.set(value=params, setting="synchronize_interface")


def synchronize_peer_ip(config: OPNsenseModuleConfig, peer_ip: str):
    if peer_ip:
        config.set(value=peer_ip, setting="synchronize_peer_ip")
    elif not peer_ip and config.get("synchronize_peer_ip") is not None:
        config._config_xml_tree.find("hasync").remove(config.get("synchronize_peer_ip"))


def remote_system_synchronization(config: OPNsenseModuleConfig, remote_backup_url: Optional[str],
                                  username: Optional[str], password: Optional[str]):
    config.set(value=remote_backup_url, setting="synchronize_config_to_ip")
    config.set(value=username, setting="remote_system_username")
    config.set(value=password, setting="remote_system_password")


def get_all_services() -> List[str]:
    allowed_services = ["Aliases", "Auth Servers", "Captive Portal", "Certificates", "Cron", "DHCPD", "DHCPDv6",
                        "DHCPv4: Relay", "DHCPv6: Relay", "Dashboard", "Dnsmasq DNS", "FRR", "Firewall Categories",
                        "Firewall Groups", "Firewall Log Templates", "Firewall Rules", "Firewall Schedules", "IPsec",
                        "Intrusion Detection", "Kea DHCP", "Monit System Monitoring", "NAT", "Netflow / Insight",
                        "Network Time", "OpenSSH", "OpenVPN", "Shaper", "Static Routes", "System Tunables",
                        "Unbound DNS", "User and Groups", "Virtual IPs", "Web GUI", "WireGuard"]
    # do gschnüdel to remove services from allowed_services that aren't installed (at some point)
    # Remove frr for now since it is an opt-in plugin and is by default not configured.
    allowed_services.remove("FRR")

    return allowed_services


def services_to_synchronize(config: OPNsenseModuleConfig, services: List[str]):
    allowed_services = get_all_services()
    if isinstance(services, str):
        services = [services]
    for service in services:
        if service not in allowed_services:
            raise ValueError(f"Service {service} could not be found in your Opnsense installation")

        if config.get(service) is None:
            config.set(value="on", setting=service)
    for service in allowed_services:
        if service not in services and config.get(service) is not None:
            config._config_xml_tree.find("hasync").remove(config.get(service))


def main():
    """
    Main function of the system_settings_general module
    """

    module_args = {
        "synchronize_states": {"type": "bool", "default": False},
        "synchronize_interface": {"type": "str",  "required": True},
        "synchronize_peer_ip": {"type": "string",  "required": False},
        "synchronize_config_to_ip": {"type": "string",  "required": False},
        "remote_system_username": {"type": "string",  "required": False},
        "remote_system_password": {"type": "string",  "required": False},
        "services_to_synchronize": {"type": "list",  "required": False}
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_one_of=[
            ['synchronize_states', 'synchronize_interface', 'synchronize_peer_ip', 'synchronize_config_to_ip',
             'remote_system_username', 'remote_system_password', 'services_to_synchronize'],
        ],
    )
    result = {
        "changed": False,
        "invocation": module.params,
        "diff": None,
    }

    synchronize_states_param = module.params.get("synchronize_states")
    synchronize_interface_param = module.params.get("synchronize_interface")
    synchronize_peer_ip_param = module.params.get("synchronize_peer_ip")
    synchronize_config_to_ip_param = module.params.get("synchronize_config_to_ip")
    remote_system_username_param = module.params.get("remote_system_username")
    remote_system_password_param = module.params.get("remote_system_password")
    services_to_synchronize_param = module.params.get("services_to_synchronize")

    with OPNsenseModuleConfig(
        module_name="system_high_availability_settings",
        config_context_names=["system_high_availability_settings"],
        check_mode=module.check_mode,
    ) as config:
        check_hasync_node(config)

        remote_system_synchronization(config=config, remote_backup_url=synchronize_config_to_ip_param,
                                      username=remote_system_username_param, password=remote_system_password_param)
        if synchronize_states_param:
            synchronize_states(config=config, params=synchronize_states_param)

        if synchronize_interface_param:
            synchronize_interface(config=config, params=synchronize_interface_param)

        if synchronize_peer_ip_param:
            synchronize_peer_ip(config=config, peer_ip=synchronize_peer_ip_param)

        if services_to_synchronize_param:
            services_to_synchronize(config=config, services=services_to_synchronize_param)

        if config.changed:
            result["diff"] = config.diff
            result["changed"] = True

        if config.changed and not module.check_mode:
            config.save()
            result["opnsense_configure_output"] = config.apply_settings()
            for cmd_result in result["opnsense_configure_output"]:
                if cmd_result["rc"] != 0:
                    module.fail_json(
                        msg="Apply of the OPNsense settings failed",
                        details=cmd_result,
                    )


if __name__ == "__main__":
    main()
