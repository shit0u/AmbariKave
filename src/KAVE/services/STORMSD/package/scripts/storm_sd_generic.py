##############################################################################
#
# Copyright 2016 KPMG Advisory N.V. (unless otherwise stated)
#
# Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
##############################################################################
import kavecommon as kc
import os
import subprocess
from resource_management import *
from resource_management.core.exceptions import ComponentIsNotRunning


class StormGeneric(Script):

    def install(self, env):
        self.install_packages(env)
        self.install_storm(env)
        self.configure(env)

    def install_storm(self, env):
        # install ZeroMQ which is prerequisite for storm
        user_exist = os.system('grep storm /etc/passwd > /dev/null')
        if user_exist != 0:
            # zeromq no longer needed?
            # kc.copy_cache_or_repo('zeromq-2.1.7-1.el6.x86_64.rpm')
            # Execute('yum install -y zeromq-2.1.7-1.el6.x86_64.rpm')
            Execute('groupadd -g 53001 storm')
            Execute('mkdir -p /app/home')
            Execute('useradd -u 53001 -g 53001 -d /app/home/storm -s /bin/bash storm -c "Storm service account"')
            Execute('chmod 700 /app/home/storm')

        storm_dir_present = os.path.isdir('/usr/local/storm')
        if not storm_dir_present:
            # download storm
            kc.copy_cache_or_repo('apache-storm-1.0.2.tar.gz', arch='noarch')
            # Execute('wget http://www.us.apache.org/dist/storm/apache-storm-1.0.2/apache-storm-1.0.2.tar.gz')
            Execute('tar -xvf apache-storm-1.0.2.tar.gz -C /usr/local')
            Execute('mv /usr/local/apache-storm-1.0.2* /usr/local/storm-1.0.2')
            Execute('chown -R storm:storm /usr/local/storm-1.0.2')
            Execute('ln -s /usr/local/storm-1.0.2 /usr/local/storm')
            Execute('ln -s /usr/local/storm/bin/storm /usr/local/bin/storm')
        storm_log_dir = os.path.isdir('/var/log/storm')
        if not storm_log_dir:
            # Creating local directory for storm
            Execute('mkdir -p /var/log/storm')
            Execute('chown -R storm:storm /var/log/storm')
            Execute('chmod 750 /var/log/storm')

    def configure(self, env):
        return self.configure_storm(env)

    def status(self, env):
        raise ClientComponentHasNoStatus()

    def configure_storm(self, env):
        import params
        env.set_params(params)
        File(params.storm_conf_file,
             content=InlineTemplate(params.storm_yaml_config),
             mode=0644
             )
        File("/usr/local/storm/log4j2/cluster.xml",
             content=InlineTemplate(params.storm_cluster_config),
             mode=0664)


class StormGenericSD(StormGeneric):
    PROG = None

    def ctlcmd(self, cmd, bg=False):
        stat, stdout, stderr = (0, "", "")
        if not bg:
            stat, stdout, stderr = kc.shell_call_wrapper('supervisorctl ' + cmd + ' storm-' + self.PROG)
            if stat or "error" in stdout.lower() or "error" in stderr.lower() or "failed" in stdout.lower() or \
                    "failed" in stderr.lower() or 'refused' in stdout or 'refused' in stderr:
                self.fail_with_error(cmd + ' ' + self.PROG + ' Failed!' + stdout + stderr)
        else:
            # TODO: Ambari 2.0 method should be replacing the below call
            # since Ambari 1.7.3 execute method never returns the control to script
            # So, we use nohup to detach the start process, and we also need to redirect all the input and output
            os.system('nohup supervisorctl ' + cmd + ' storm-' + self.PROG + ' 2> /dev/null > /dev/null < /dev/null &')
        return stdout

    def install(self, env):
        self.install_packages(env)
        self.install_storm(env)
        self.install_supervisor(env)
        self.configure(env)

    def install_supervisor(self, env):
        import params

        params.PROG = self.PROG
        env.set_params(params)
        if not os.path.exists('/etc/supervisord.conf'):
            File('/etc/supervisord.conf',
                 content=Template("supervisord.conf.j2"),
                 mode=0755
                 )
        Execute('mkdir -p %s' % params.childlogdir)
        kc.install_epel()
        Package('python-meld3')
        Package('python-devel')
        Package('python-pip')
        Execute('pip install supervisor')

    def start(self, env):
        """
        The start method for Storm is pretty convoluted.
        Supervisord may already be running due to other storm modules.
        Then there is the generic problem that the storm serivce start/stop/restart
        commands don't return control to the script,
        so they need to be executed with nohup,
        and then we need to wait for supevisord to actually be started properly
        before trying to start our supervised programs
        Tests indicated 5s is enough of a wait for this
        """
        self.configure(env)
        stat, stdout, stderr = kc.shell_call_wrapper("service supervisord status")
        if "running" not in stdout:
            Execute('service supervisord start')
        self.ctlcmd('start', bg=True)
        import time

        time.sleep(5)
        stdout = self.ctlcmd('status')
        if "START" not in stdout and "RUNNING" not in stdout:
            self.fail_with_error('Start Failed!' + stdout + stderr)
        return True

    def stop(self, env):
        self.ctlcmd('stop', bg=True)

    def restart(self, env):
        """
        Akin to the start method, the storm restart method must also be treated with care
        Since the stop command is run in the background, we must wait until the service
        is actually stopped before trying to start it.
        Tests indicated 5s is enough of a wait for this
        """
        self.stop(env)
        import time
        time.sleep(5)
        self.start(env)

    def status(self, env):
        Execute('service supervisord status')
        stdout = self.ctlcmd('status')
        if "RUNNING" not in stdout:
            raise ComponentIsNotRunning()

    def configure(self, env):
        self.configure_storm(env)
        return self.configure_sd(env)

    def configure_sd(self, env):
        import params
        params.PROG = self.PROG
        env.set_params(params)
        if not os.path.exists('/etc/supervisord.conf'):
            File('/etc/supervisord.conf',
                 content=Template("supervisord.conf.j2"),
                 mode=0755
                 )
        Execute('mkdir -p /etc/supervisord.d/')
        File("/etc/supervisord.d/" + self.PROG + ".conf",
             content=Template("prog.conf"),
             mode=0644
             )
        File("/etc/init.d/supervisord",
             content=Template("supervisor.j2"),
             mode=0755
             )
        kc.chown_r('/etc/supervisord.d/', 'storm')
