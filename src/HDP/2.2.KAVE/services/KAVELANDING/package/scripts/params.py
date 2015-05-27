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
from resource_management import *
from resource_management.core.system import System
import os

config = Script.get_config()

hostname = config["hostname"]
short_host = config["hostname"].split('.')[0]

AMBARI_ADMIN = config['configurations']['kavelanding']['AMBARI_ADMIN']
AMBARI_ADMIN_PASS = config['configurations']['kavelanding']['AMBARI_ADMIN_PASS']
AMBARI_SERVER = default("/clusterHostInfo/ambari_server_host", ['ambari'])[
    0]  #default('configurations/kavelanding/AMBARI_SERVER','ambari')
www_folder = default('configurations/kavelanding/www_folder', '/var/www/html/')
PORT = default('configurations/kavelanding/PORT', '80')
AMBARI_SHORT_HOST = AMBARI_SERVER.split('.')[0]
servername = default('configurations/kavelanding/servername', hostname)
if servername == "default":
    servername = hostname