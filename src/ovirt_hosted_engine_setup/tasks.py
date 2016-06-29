#
# ovirt-hosted-engine-setup -- ovirt hosted engine setup
# Copyright (C) 2013-2015 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#


import gettext
import time


from otopi import base
from otopi import util


from ovirt_hosted_engine_setup import constants as ohostedcons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-hosted-engine-setup')


@util.export
class VMDownWaiter(base.Base):
    """
    VM down waiting utility.
    """

    POLLING_INTERVAL = 5

    def __init__(self, environment):
        super(VMDownWaiter, self).__init__()
        self.environment = environment

    def wait(self):
        cli = self.environment[ohostedcons.VDSMEnv.VDS_CLI]
        down = False
        destroyed = False
        while not down:
            time.sleep(self.POLLING_INTERVAL)
            self.logger.debug('Waiting for VM down')
            response = cli.getVmStats(
                self.environment[ohostedcons.VMEnv.VM_UUID]
            )
            code = response['status']['code']
            message = response['status']['message']
            self.logger.debug(message)
            if code == 0:
                stats = response['items'][0]
                down = (stats['status'] == 'Down')
            elif code == 1:
                # Assuming VM destroyed
                down = True
                destroyed = True
            else:
                raise RuntimeError(_('Error acquiring VM status'))
        return destroyed


@util.export
class DomainMonitorWaiter(base.Base):
    """
    VM down waiting utility.
    """

    POLLING_INTERVAL = 5

    def __init__(self, environment):
        super(DomainMonitorWaiter, self).__init__()
        self.environment = environment

    def wait(self, sdUUID):
        cli = self.environment[ohostedcons.VDSMEnv.VDS_CLI]
        acquired = False
        while not acquired:
            time.sleep(self.POLLING_INTERVAL)
            self.logger.debug('Waiting for domain monitor')
            response = cli.getVdsStats()
            self.logger.debug(response)
            if response['status']['code'] != 0:
                self.logger.debug(response['status']['message'])
                raise RuntimeError(_('Error acquiring VDS status'))
            try:
                domains = response['storageDomains']
                acquired = domains[sdUUID]['acquired']
            except KeyError:
                self.logger.debug(
                    'Error getting VDS status',
                    exc_info=True,
                )
                raise RuntimeError(_('Error acquiring VDS status'))


@util.export
class TaskWaiter(base.Base):
    """
    Task waiting utility.
    """

    def __init__(self, environment):
        super(TaskWaiter, self).__init__()
        self.environment = environment

    def wait(self, task_id, timeout=600):
        cli = self.environment[ohostedcons.VDSMEnv.VDS_CLI]
        info = cli.getTaskInfo(taskID=task_id)
        self.logger.debug(info)
        if 'status' not in info or info['status']['code'] != 0:
            raise RuntimeError(
                _('Failed getting task info: {m}').format(
                    m=info['status']['message'],
                )
            )
        verb = 'unknown'
        if 'verb' in info:
            verb = info['verb']
        while timeout > 0:
            res = cli.getTaskStatus(taskID=task_id)
            self.logger.debug(res)
            if 'status' not in res or res['status']['code'] != 0:
                raise RuntimeError(
                    _('Failed getting task status: {m}').format(
                        m=res['status']['message'],
                    )
                )
            if 'taskState' in res and res['taskState'] == 'finished':
                return {
                    'message': res['status']['message'],
                    'code': res['code'],
                    'taskResult': res['taskResult'],
                }
            if timeout % 10 == 0:
                self.logger.info(
                    _('Waiting for {v} to complete').format(v=verb)
                )
            timeout -= 1
            time.sleep(1)
        raise RuntimeError(
            _('Timeout waiting for {v} to complete').format(v=verb)
        )


# vim: expandtab tabstop=4 shiftwidth=4
