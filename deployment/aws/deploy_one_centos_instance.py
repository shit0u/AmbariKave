#!/usr/bin/env python
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
"""
up one centos instance

usage deploy_one_centos_instance.py hostname [security_config.json] [instance_type] [--verbose] [--ambari-dev]
    hostname:     hostname to apply to the machine (currently you cannot specify the domain here)
    security_config.json : a json file with the security group/subnet-id keypair/keyfile (see readme for details)


optional:
    --verbose : print all remotely running commands
    [instance_type]: optional, if not specified will use c3.large
    [security_config.json]: optional, if not specified will use the environemnt variable AWSSECCONF
    [--ambari-dev] : will use our ambari development image, this should speed up testing *a lot*
"""

import os
import sys
import time
import json


installfrom = os.path.realpath(os.path.dirname(__file__))
liblocation = os.path.realpath(installfrom + '/../lib')
sys.path.append(liblocation)

import libDeploy as lD

lD.debug = False
import libAws as lA


def help():
    print __doc__
    #sys.exit(code)


ambaridev = False


def parseOpts():
    global ambaridev
    if "-h" in sys.argv or "--help" in sys.argv:
        help()
        sys.exit(0)
    if "--ambari-dev" in sys.argv:
        ambaridev = True
        sys.argv = [s for s in sys.argv if s != "--ambari-dev"]
    if "--not-strict" in sys.argv:
        sys.argv = [s for s in sys.argv if s not in ["--not-strict"]]
        lD.strict_host_key_checking = False
    if "--verbose" in sys.argv:
        lD.debug = True
        sys.argv = [s for s in sys.argv if s != "--verbose"]
    if len(sys.argv) < 2:
        help()
        raise AttributeError("You did not supply sufficient arguments")
    elif len(sys.argv) > 4:
        help()
        raise AttributeError("You supplied too many arguments")
    macname = sys.argv[1]
    secf = ""
    insttype = "c3.large"
    if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        secf = sys.argv[2]
        if len(sys.argv) > 3:
            insttype = sys.argv[3]
    else:
        if "AWSSECCONF" not in os.environ:
            help()
            raise IOError("please specify security config file or set AWSSECCONF environment variable!")
        secf = os.path.expanduser(os.environ["AWSSECCONF"])
        if len(sys.argv) > 2:
            insttype = sys.argv[2]
    return macname, secf, insttype


machinename, secf, itype = parseOpts()
jsondat = open(secf)
security_config = json.loads(jsondat.read())
jsondat.close()
lA.checksecjson(security_config, requirekeys=["AWS"])

secGroup = security_config["SecurityGroup"]
keypair = security_config["AccessKeys"]["AWS"]["KeyName"]
keyloc = security_config["AccessKeys"]["AWS"]["KeyFile"]
subnet = None

if "Subnet" in security_config:
    subnet = security_config["Subnet"]

lA.testaws()

if lD.detect_proxy() and lD.proxy_blocks_22:
    raise SystemError(
        "This proxy blocks port 22, that means you can't ssh to your machines to do the initial configuration. To "
        "skip this check set libDeploy.proxy_blocks_22 to false and libDeploy.proxy_port=22")

lD.testproxy()

upped = lA.upCentos6(itype, secGroup, keypair, subnet=subnet, ambaridev=ambaridev)
print "submitted"

iid = lA.iidFromUpJSON(upped)[0]

import time

time.sleep(5)
lA.nameInstance(iid, machinename)

ip = lA.pubIP(iid)
acount = 0
while (ip is None and acount < 20):
    print "waiting for IP"
    lD.mysleep(1)
    ip = lA.pubIP(iid)
    acount = acount + 1

if os.path.exists(os.path.realpath(os.path.expanduser(keyloc))):
    print "waiting until contactable, ctrl-C to quit"
    try:
        remote = lD.remoteHost('root', ip, keyloc)
        lD.waitUntilUp(remote, 20)
        remote.register()
        if not ambaridev:
            lD.renameRemoteHost(remote, machinename, 'kave.io')
        lD.addAsHost(edit_remote=remote, add_remote=remote, dest_internal_ip=lA.privIP(iid))
        if ambaridev:
            if "GIT" in security_config["AccessKeys"]:
                remote.prepGit(security_config["AccessKeys"]["GIT"]["KeyFile"], force=True)
            remote.run("echo 0 > /selinux/enforce")
        remote.describe()
    except KeyboardInterrupt:
        pass
else:
    print "Warning: not contactable since keyfile supplied does not exist locally, also means I could not rename the host", keyloc

print "OK, iid " + iid + " now lives at IP " + ip