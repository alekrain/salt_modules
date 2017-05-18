# =============================================================================
# SaltStack Execution Module
#
# NAME: _modules/virsh.py
# VERSION: 0.1
# DATE  : 2016.08.03
#
# PURPOSE: Provide a salt interface to virsh commands on KVM hosts.
#
# CHANGE LOG:
#
# NOTES:
#

import sys
import logging
import re
from time import sleep
from sys import exit

# Import Salt libs
import salt.utils

log = logging.getLogger(__name__)

__virtualname__ = 'virsh'

# Import third party libs
try:
    import libvirt
    HAS_LIBVIRT = True
except ImportError:
    HAS_LIBVIRT = False


def __virtual__():
    '''
    Only load on machines with libvirt installed
    '''
    if HAS_LIBVIRT:
        return __virtualname__
    else:
        return (False, 'The libvirt execution module failed to load: the libvirt python library is not available.')


def _connect_to_libvirt():
    conn = libvirt.open("qemu:///system")

    if conn is None:
        log.debug("Failed to open a connection to the hypervisor.")
        exit(1)
    else:
        return conn


def _list_vms(state=0):
    '''Worker function that provides data back to all the list functions.'''
    conn = _connect_to_libvirt()

    try:
        domains = conn.listAllDomains(state)
        conn.close()
    except:
        error = sys.exc_info()[0]
        log.debug("Unable to list VMs: {}".format(error))
        return False

    vm_list = []
    for domain in domains:
        vm_list.append(domain.name())
    return vm_list


def list(match='.*', state='all'):
    '''List VMs on the minion.

    CLI Example:

    .. code-block:: bash
        salt '*' virsh.list [match='regex'] [state=all|running|shutdown]
    '''
    if state == 'all':
        code = 0
    elif state == 'running':
        code = 1
    elif state == 'shutdown':
        code = 2
    else:
        log.debug("Invalid State: {0}".format(state))
        exit(1)

    log.info("Listing {0} VMs".format(state))
    vm_list = _list_vms(code)
    matching_list = []
    if vm_list is not False:
        log.debug("Looking for matches in: {0}".format(vm_list))
        for domain in vm_list:
            log.debug("Checking if match: {0} to {1}".format(match, domain))
            if re.search(match, domain, re.I | re.S | re.M) is not None:
                log.debug("Adding {0} to list".format(domain))
                matching_list.append(domain)
        return matching_list
    else:
        log.debug("Could not get the VM list")
        return False


def reboot(domain):
    '''Attempt to gracefully reboot a VM.

    CLI Example:

    .. code-block:: bash

        salt '*' virsh.reboot host1
    '''
    conn = _connect_to_libvirt()

    log.info("Reboot".format(domain))
    try:
        dom = conn.lookupByName(domain)
        dom.reboot(0)
        conn.close()
    except:
        error = sys.exc_info()[0]
        log.debug("Reboot failed: {0}".format(error))
        return False
    return True


def shutdown(domain, force=False):
    '''Attempt to gracefully shutdown a VM. Optionally, force the shutdown.

    CLI Example:

    .. code-block:: bash

        salt '*' virsh.shutdown host1 [force=True]
    '''
    conn = _connect_to_libvirt()

    log.info("Shutting down: {0}".format(domain))
    try:
        dom = conn.lookupByName(domain)
        if force is True:
            dom.destroy()
        else:
            dom.shutdown()
        conn.close()
    except:
        error = sys.exc_info()[0]
        log.debug("Shutdown failed: {0}".format(error))
        return False
    return True


def shutdown_matching(match='.*', force=False):
    '''Attempt to shutdown all VMs that start with a particular string. Optionally, force the shutdown.

    CLI Example:

    .. code-block:: bash

        salt '*' virsh.shutdown_matching [match='regex'] [force=True]
    '''
    conn = _connect_to_libvirt()
    domains = []

    try:
        domain_objects = conn.listAllDomains(0)
        for domain in domain_objects:
            domains.append(domain.name())
    except:
        log.debug("Failed to get a list of domains: {0}".format(sys.exc_info()[0]))
        return False

    log.debug("Domains: {0}".format(domains))
    for domain in domains:
        log.debug("Checking if match: {0}".format(domain))
        if re.search(match, domain, re.I | re.S | re.M) is not None:
            log.info("Shutting down: {0}".format(domain))
            try:
                dom = conn.lookupByName(domain)
                if force is True:
                    dom.destroy()
                else:
                    dom.shutdown()
            except:
                log.debug("Failed to shutdown domain: {0}".format(sys.exc_info()[0]))
    conn.close()
    return domains


def start(domain):
    '''Attempt to start up a domain.

    CLI Example:

    .. code-block:: bash

        salt '*' virsh.start domain
    '''
    conn = _connect_to_libvirt()

    try:
        dom = conn.lookupByName(domain)
        dom.create()
        conn.close()
        return True
    except:
        log.debug("Failed to start domain: {0}".format(sys.exc_info()[0]))
        conn.close()
        return False


def start_matching(match='.*', sleep_secs=1):
    '''Attempt to start all VMs that match a regex. By default the regex matches everything. The optional argument\
    sleep_secs, sleeps for the specified number of seconds between starting up VMs.

    CLI Example:

    .. code-block:: bash

        salt '*' virsh.start_matching [match='regex'] [sleep_secs=1]
    '''
    conn = _connect_to_libvirt()
    domains = []
    try:
        domain_objects = conn.listAllDomains(0)
        for domain in domain_objects:
            domains.append(domain.name())
    except:
        log.debug("Failed to get a list of domains: {0}".format(sys.exc_info()[0]))
        return False

    log.debug("Domains: {0}".format(domains))
    for domain in domains:
        log.debug("Checking if match: {0}".format(domain))
        if re.search(match, domain, re.I | re.S | re.M) is not None:
            log.info("Starting: {0}".format(domain))
            try:
                dom = conn.lookupByName(domain)
                dom.create()
            except:
                log.debug("Failed to start domain: {0}".format(sys.exc_info()[0]))
    conn.close()
    return domains
