# =============================================================================
# SaltStack Execution Module
#
# NAME: _modules/vyos.py
# MODIFIED BY: Alek Tant of SmartAlek Solutions
# DATE  : 2017.05.17
#
# PURPOSE: Provide a SaltStack interface to vyOS.
#
# NOTES:
# Copyright (c) 2016 VyOS maintainers and contributors
# Portions copyright 2016 Hochikong
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


"""
.. module:: vymgmt
   :platform: Unix
   :synopsis: Provides a programmatic interface to VyOS router configuration sessions

.. moduleauthor:: VyOS Team <maintainers@vyos.net>, Hochikong


"""

import re
import logging
import pexpect

log = logging.getLogger(__name__)
vyos_dir = '/opt/vyatta/'
api = '{}/sbin/my_cli_shell_api'.format(vyos_dir)
__virtualname__ = 'vyos'


def __virtual__():
    # Only load on vyOS machines.
    if api:
        return __virtualname__
    else:
        log.error('The vyOS shell api could not be found at {}.'.format(api))
        return False


class VyOSError(Exception):
    """ Raised on general errors """
    pass


class ConfigError(VyOSError):
    """ Raised when an error is found in configuration """
    pass


class CommitError(ConfigError):
    """ Raised on commit failures """
    pass


class ConfigLocked(CommitError):
    """ Raised when commit failes due to another commit in progress """
    pass


class Router(object):
    """ Router configuration interface class """
    def __init__(self):
        # Session flags
        self.session_modified = False
        self.session_saved = True
        self.conf_mode = False

        # String codec, hardcoded for now
        self.codec = "utf8"

        # Create a session
        self.session = pexpect.spawn('su - vyos', echo=False)
        self.session.sendline('export TERM=xterm')
        self.session.sendline('set terminal length 0')

    def execute_command(self, command, config_mode_required=False):
        """ Executed a command on the router
    
        :param command: The configuration command
        :param config_mode_required: Specifies if the command needs to be executed from config mode.
        :returns: string -- Command output
        :raises: VyOSError
        """

        remove_top_lines = 1
        remove_bottom_lines = 2

        if config_mode_required:
            remove_top_lines += 3
            remove_bottom_lines += 1
            self.session.sendline('config')
            self.session.sendline(command)
            self.session.sendline('commit')
            self.session.sendline('save')

            self.session.sendline('exit')
        else:
            self.session.sendline(command)

        self.session.sendline('exit')
        self.session.expect(pexpect.EOF)

        # Store output from the command in an array
        output = []
        for line in self.session.before.splitlines():
            output.append(line.rstrip('?[m'))

        # Remove some of the top and bottom lines of output for readability
        if len(output) >= 3:
            for x in range(1, remove_top_lines, 1):
                del(output[0])
            for x in range(1, remove_bottom_lines, 1):
                del(output[-1])

        return output

    def status(self):
        """ Returns the router object status for debugging
    
        :returns: dict -- Router object status
        """
        return {"logged_in": self.logged_in,
                "session_modified": self.session_modified,
                "session_saved": self.session_saved,
                "conf_mode": self.conf_mode}

    def close_session(self):
        """ Close and terminate a session"""
        self.session.close()
        self.session.terminate(force=True)


def run_op_mode_command(command):
    """ Executes a VyOS operational command

    :param command: VyOS operational command
    :type command: str
    :returns: list -- Command output
    """

    if command.startswith('show'):
        router = Router()
        prefix = ""
        # In cond mode, op mode commands require the "run" prefix
        if router.conf_mode:
            prefix = "run"

        output = router.execute_command("{0} {1}".format(prefix, command))
        router.close_session()
        return output
    else:
        return 'Op mode commands must begin with "show".'


def run_config_mode_command(command, save_changes=False):
    """ Executes a VyOS configuration command

    :param command: VyOS configuration command
    :type command: str
    :returns: list -- Command output
    :raises: VyOSError
    """

    if command.startswith(('confirm', 'comment', 'compare', 'copy', 'delete', 'discard', 'edit', 'load', 'loadkey',
                           'merge', 'rename', 'rollback', 'run', 'set', 'show')):
        router = Router()
        output = router.execute_command(command, config_mode_required=True)
        router.close_session()
        return output


#####
# Functions below here have not been implemented to work with SaltStack yet.
# These will likely be useful as state functions.
#####
def _commit(self):
    """Commits configuration changes

    You must call the configure() method before using this one.

    :raises: VyOSError, ConfigError, CommitError, ConfigLocked

    """
    if not self.__conf_mode:
        raise VyOSError("Cannot commit without entering configuration mode")
    else:
        if not self.__session_modified:
            raise ConfigError("No configuration changes to commit")
        else:
            output = self.__execute_command("commit")

            if re.search(r"Commit\s+failed", output):
                raise CommitError(output)
            if re.search(r"another\s+commit\s+in\s+progress", output):
                raise ConfigLocked("Configuration is locked due to another commit in progress")

            self.__session_modified = False
            self.__session_saved = False


def _save(self):
    """Saves the configuration after commit

    You must call the configure() method before using this one.
    You do not need to make any changes and commit then to use this method.
    You cannot save if there are uncommited changes.

    :raises: VyOSError
    """
    if not self.__conf_mode:
        raise VyOSError("Cannot save when not in configuration mode")
    elif self.__session_modified:
        raise VyOSError("Cannot save when there are uncommited changes")
    else:
        self.__execute_command("save")
        self.__session_saved = True


def _exit(self, force=False):
    """ Exits configuration mode on the router

    You must call the configure() method before using this one.

    Unless the force argument is True, it disallows exit when there are unsaved
    or uncommited changes. Any uncommited changes are discarded on forced exit.

    If the session is not in configuration mode, this method does nothing.

    :param force: Force exit despite uncommited or unsaved changes
    :type force: bool
    :raises: VyOSError
    """
    if not self.__conf_mode:
        pass
    else:
        # XXX: would be nice to simplify these conditionals
        if self.__session_modified:
            if not force:
                raise VyOSError("Cannot exit a session with uncommited changes, use force flag to discard")
            else:
                self.__execute_command("exit discard")
                self.__conf_mode = False
                return
        elif (not self.__session_saved) and (not force):
            raise VyOSError("Cannot exit a session with unsaved changes, use force flag to ignore")
        else:
            self.__execute_command("exit")
            self.__conf_mode = False


def _set(self, path):
    """ Creates a new configuration node on the router

    You must call the configure() method before using this one.

    :param path: Configuration node path.
                   e.g. 'protocols static route ... next-hop ... distance ...'
    :raises: ConfigError
    """
    if not self.__conf_mode:
        raise ConfigError("Cannot execute set commands when not in configuration mode")
    else:
        output = self.__execute_command("{0} {1}". format("set", path))
        if re.search(r"Set\s+failed", output):
            raise ConfigError(output)
        elif re.search(r"already exists", output):
            raise ConfigError("Configuration path already exists")
        self.__session_modified = True


def _delete(self, path):
    """ Deletes a node from configuration on the router

    You must call the configure() method before using this one.

    :param path: Configuration node path.
                           e.g. 'protocols static route ... next-hop ... distance ...'
    :raises: ConfigError
    """
    if not self.__conf_mode:
        raise ConfigError("Cannot execute delete commands when not in configuration mode")
    else:
        output = self.__execute_command("{0} {1}". format("delete", path))
        if re.search(r"Nothing\s+to\s+delete", output):
            raise ConfigError(output)
        self.__session_modified = True


