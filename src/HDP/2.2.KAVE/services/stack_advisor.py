#!/usr/bin/env ambari-python-wrap
"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
class HDP22KAVEStackAdvisor(HDP22StackAdvisor):

    # List of validators which should also be evaluated if there is not recommended default present.
    validateWithoutRecommendedDefault = ['freeipa']

    def validatorPasswordStrength(self, properties, propertyName, minLength=8):
        if not propertyName in properties:
            return self.getErrorItem("Value should be set")
        if len(properties[propertyName]) < minLength:
            return self.getErrorItem("Password should be at least %s chars long" % minLength)
        return None

    def getServiceConfigurationValidators(self):
        parentValidators = super(HDP22KAVEStackAdvisor, self).getServiceConfigurationValidators()
        childValidators = {
            "FREEIPA": ["freeipa", self.validateFreeIPAConfigurations]
        }
        parentValidators.update(childValidators)
        return parentValidators

    def validateFreeIPAConfigurations(self, properties, recommendedDefaults, configurations):
        validationItems = [{"config-name": 'directory_password', "item": self.validatorPasswordStrength(properties, 'directory_password')}]
        return self.toConfigurationValidationProblems(validationItems, "freeipa")

    def getConfigurationsValidationItems(self, services, hosts):
        """
        Returns array of Validation objects about issues with configuration 
        values provided in services. This is overridden from HDP206StackAdvisor. 
        The added functionality is the use of validateWithoutRecommendedDefault. 
        We want the passwords to be validated even if there are no suitable 
        recommendedDefaults present in the blueprint. 
        """
        items = []

        recommendations = self.recommendConfigurations(services, hosts)
        recommendedDefaults = recommendations["recommendations"]["blueprint"]["configurations"]

        configurations = services["configurations"]
        for service in services["services"]:
            serviceName = service["StackServices"]["service_name"]
            validator = self.validateServiceConfigurations(serviceName)
            if validator is not None:
                siteName = validator[0]
                method = validator[1]
                if siteName in recommendedDefaults:
                    recommendedDefault = recommendedDefaults[siteName]["properties"]
                else:
                    recommendedDefault = None
        
                if recommendedDefault is not None or siteName in self.validateWithoutRecommendedDefault:
                    siteProperties = getSiteProperties(configurations, siteName)
                    if siteProperties is not None:
                        resultItems = method(siteProperties, recommendedDefault, configurations)
                        items.extend(resultItems)

        return items