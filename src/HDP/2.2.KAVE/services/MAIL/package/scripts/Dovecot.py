##############################################################################
#
# Copyright 2015 KPMG N.V. (unless otherwise stated)
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
import os

from resource_management import *


class Dovecot(Script):
    def install(self, env):
        import params

        self.install_packages(env)
        self.configure(env)

    def configure(self, env):
        import params

        env.set_params(params)
        print "Configuring Dovecot"
        File('/etc/dovecot/dovecot.conf',
             content=Template("dovecot.conf.j2"),
             mode=0644
             )
        File('/etc/dovecot/conf.d/10-auth.conf',
             content=Template("10-auth.conf.j2"),
             mode=0644
             )
        File('/etc/dovecot/conf.d/10-mail.conf',
             content=Template("10-mail.conf.j2"),
             mode=0644
             )
        File('/etc/dovecot/conf.d/10-master.conf',
             content=Template("10-master.conf.j2"),
             mode=0644
             )
        if not os.path.isfile('/etc/dovecot/dovecot.conf'):
            raise RuntimeError("Service not installed correctly")

    def start(self, env):
        print "start dovecot"
        #return Execute('service dovecot start > /dev/null')
        # TODO: Ambari 2.0 method should be replacing the below call
        #since Ambari 1.7.3 execute method never returns the control to script
        return os.system("service dovecot start")


    def stop(self, env):
        print "stop dovecot.."
        return Execute('service dovecot stop > /dev/null')


    def status(self, env):
        print "checking status..."
        print Execute('service dovecot status > /dev/null')


if __name__ == "__main__":
    Dovecot().execute()