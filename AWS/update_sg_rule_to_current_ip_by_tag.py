# -*- coding: utf-8 -*-
# Project: sysadmin/AWS
# Filename: update_sg_rule_to_current_ip_by_tag.py
#
# File Description: Update
#
# By: endavis

"""
Updates any rules with a specific tag to the current hosts public ipv4 or ipv6 address.

This assumes that AWS credentials have been setup through the IAM console
or the aws cli. The script will use the default profile and region.

see: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#configuration
"""
# Standard Library
import sys
import datetime
import argparse
import re
import logging
from pathlib import Path

# 3rd Party
import boto3
import dns.message
import dns.rdatatype
import dns.query
import dns.resolver

LOG_IN_UTC_TZ = True

# change boto3 logging levels
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('boto3').setLevel(logging.CRITICAL)


def formatTime_RFC3339_UTC(self, record, datefmt=None):
    """
    Formats a timestamp in the RFC3339 format in the UTC timezone.

    Args:
        record: The record object containing the timestamp.
        datefmt: Not used, but required by the logging module.

    Returns:
        str: The formatted timestamp in RFC3339 format with UTC timezone.
    """
    return (
        datetime.datetime.fromtimestamp(record.created)
        .astimezone(datetime.timezone.utc)
        .isoformat()
    )

def formatTime_RFC3339(self, record, datefmt=None):
    """
    Formats a timestamp in the RFC3339 format in the local timezone.

    Args:
        record: The record object containing the timestamp.
        datefmt: Not used, but required by the logging module.

    Returns:
        str: The formatted timestamp in RFC3339 format.
    """
    return (
        datetime.datetime.fromtimestamp(record.created)
        .astimezone()
        .isoformat()
    )

# set up logging, log to stdout
logging.basicConfig(
    stream=sys.stdout,
    level='INFO',
    format="%(asctime)s : %(levelname)-9s - %(name)-22s - %(message)s",
)

# change LOG_IN_UTC_TZ to False if you want to log in local time
# updates the formatter for the logging module
if LOG_IN_UTC_TZ:
    logging.Formatter.formatTime = formatTime_RFC3339_UTC
else:
    logging.Formatter.formatTime = formatTime_RFC3339

f_path = Path(__file__)

# create a logger for the script
logger = logging.getLogger(f_path.stem)

def parse_args():
    """
    Parses the command line arguments for updating a security group rule based on a tag.

    Returns:
        tuple: A tuple containing the parsed arguments:
            - region: The AWS region the security group is in. If not provided, the default region will be used.
            - tag: The tag of the rule to search for and update.
    """
    parser = argparse.ArgumentParser(description='A script to update a security group rule with the current hosts public ipv4 and ipv6 based on a tag')

    parser.add_argument(
        '-t',
        '--tag',
        help='the tag of the rule to search for and update',
        required=True)

    parser.add_argument(
        '-r',
        '--region',
        help='the AWS region the security group is in, if not provided the default region will be used',
        default='')

    args = vars(parser.parse_args())
    return args['region'], args['tag']


def get_ips():
    """
    get the current ipv4 and ipv6 addresses for the host

    we use google's DNS servers to get the public IPs for the host

    dig ipv6 command: dig -6 TXT +short o-o.myaddr.l.google.com @ns1.google.com
    dig ipv4 command: dig -4 TXT +short o-o.myaddr.l.google.com @ns1.google.com
    """
    # find the ips for google's DNS servers
    r_google_ipv6 = dns.resolver.resolve("ns1.google.com", 'AAAA')
    r_google_ipv4 = dns.resolver.resolve("ns1.google.com", 'A')
    google_ipv6 = r_google_ipv6[0].address
    google_ipv4 = r_google_ipv4[0].address

    # create a query to get the address for the host
    q = dns.message.make_query("o-o.myaddr.l.google.com", dns.rdatatype.TXT)

    # get the ipv6 address
    r_ipv6 = dns.query.udp(q, google_ipv6)
    public_ipv6_address = r_ipv6.answer[0][0].strings[0].decode()

    # get the ipv4 address
    r_ipv4 = dns.query.udp(q, google_ipv4)
    public_ipv4_address = r_ipv4.answer[0][0].strings[0].decode()

    return public_ipv4_address, public_ipv6_address

class AWS:
    """
    Represents an AWS connection and provides methods for updating security group rules.

    Args:
        region: The AWS region the security group is in. If not provided, the default region will be used.
    """
    def __init__(self, region):
        """
        Initializes an AWS connection.

        Args:
            region: The AWS region the security group is in. If not provided, the default region will be used.
        """
        if region:
            self.ec2_client = boto3.client('ec2', region_name=region)
        else:
            self.ec2_client = boto3.client('ec2')

    def find_tag(self, tag, tags):
        """
        Finds a specific tag in a list of tags.

        the boto3 describe_security_group_rules returns the tags as a list of dictionaries
            'Tags': [{'Key': 'SometagName', 'Value': 'TagValue'}, {'Key': 'SomeOtherName', 'Value': 'TagValue'}]

        Args:
            tag: The tag to search for.
            tags: The list of tags to search in.

        Returns:
            bool: True if the tag is found, False otherwise.
        """
        for item in tags:
            if item['Key'] == tag and item['Value'] == 'Yes':
                return True

    def update_sg_rules(self, tag, new_ipv4_address, new_ipv6_address):
        """
        Updates security group rules based on a tag.

        Args:
            tag: The tag of the rule to search for and update.
            new_ipv4_address: The new IPv4 address to update the rule with.
            new_ipv6_address: The new IPv6 address to update the rule with.
        """
        logger.info(f"Looking for rules with tag {tag} in region {self.ec2_client.meta.region_name}")

        # get all the security group rules
        sg_rules = self.ec2_client.describe_security_group_rules()

        # create a dictionary to store the status of the rules
        rules_status = {}

        # loop through the rules and update the ones with the tag
        for rule in sg_rules['SecurityGroupRules']:

            # check if the rule has the tag
            if 'Tags' in rule and self.find_tag(tag, rule['Tags']) and rule['IpProtocol'] in ['tcp', 'udp']:
                logger.info(f"Rule {rule['GroupId']} {rule['SecurityGroupRuleId']}: has tag {tag}")

                # update the rule
                status = self.update_single_sg_rule(
                        rule, new_ipv4_address, new_ipv6_address
                    )

                # if the status doesn't exist in the dictionary, add it
                if not rules_status.get(status):
                    rules_status[status] = []

                # add the rule id to the status
                rules_status[status].append(rule['SecurityGroupRuleId'])

        # log the status of the rules
        if not rules_status:
            logger.info(f"No rules found with tag {tag}")
        else:
            for status, rule_ids in rules_status.items():
                logger.info(f"{status}: {', '.join(rule_ids)}")

    def update_single_sg_rule(self, rule, ipv4_address=None, ipv6_address=None):
        """
        Updates a single security group rule.

        Args:
            rule: The rule to update.
            ipv4_address: Optional. The new IPv4 address to update the rule with.
            ipv6_address: Optional. The new IPv6 address to update the rule with.

        Returns:
            str: The status of the update operation: "Updated", "Error", or "Already Set".
        """
        # get the current date and time
        date = datetime.datetime.now(datetime.timezone.utc)
        datestring = date.strftime('%a %b %d %Y %H:%M:%S %Z')

        # The description of the rule is updated with the current date and time in the format:
        # #DATE .Mon Mar 29 2021 14:45:00 UTC.

        # update the description with the current date and time
        if 'Description' not in rule:
            rule['Description'] = ''

        if '#DATE' in rule['Description']:
            new_description = re.sub(r'#DATE \.(.*)\.', f'#DATE .{datestring}.', rule['Description'])
        else:
            new_description = f'{rule["Description"]} #DATE .{datestring}.'

        # create a dictionary to store the updated security group rule information,
        # this copies the needed information from the original rule and updates the description
        SecurityGroupRule = {
                'IpProtocol': rule['IpProtocol'],
                'FromPort': rule['FromPort'],
                'ToPort': rule['ToPort'],
                'Description': new_description
            }

        # check if the rule is an ipv6 rule
        if 'CidrIpv6' in rule and ipv6_address and ipv6_address != '':
            return self.update_single_sg_rule_ipv6(rule, ipv6_address, SecurityGroupRule)

        # check if the rule is an ipv4 rule
        if 'CidrIpv4' in rule and ipv4_address and ipv4_address != '':
            return self.update_single_sg_rule_ipv4(rule, ipv4_address, SecurityGroupRule)

    def update_single_sg_rule_ipv6(self, rule, ipv6_address, SecurityGroupRule):
        """
        Updates a single security group rule with an IPv6 address.

        Args:
            rule: The rule to update.
            ipv6_address: The new IPv6 address to update the rule with.
            SecurityGroupRule: The updated security group rule.

        Returns:
            str: The status of the update operation: "Updated", "Error", or "Already Set".
        """
        # create the new ipv6 cidr
        new_ipv6_cidr = f'{ipv6_address}/128'

        # check if the new ipv6 cidr is different from the current rule
        if rule['CidrIpv6'] != new_ipv6_cidr:
            logger.info(f"Rule {rule['GroupId']} {rule['SecurityGroupRuleId']}:  Updating ipv6 rule to {new_ipv6_cidr}")

            # update the ipv6 CIDR
            SecurityGroupRule['CidrIpv6'] = new_ipv6_cidr

            # update the rule
            return self._modify_rule(rule['GroupId'], rule['SecurityGroupRuleId'], SecurityGroupRule)

        else:
            logger.info(f"Rule {rule['GroupId']} {rule['SecurityGroupRuleId']}: ipv6 address is the same as the current rule {rule['CidrIpv6']}")
            return "Already Set"

    def update_single_sg_rule_ipv4(self, rule, ipv4_address, SecurityGroupRule):
        """
        Updates a single security group rule with an IPv4 address.

        Args:
            rule: The rule to update.
            ipv4_address: The new IPv4 address to update the rule with.
            SecurityGroupRule: The updated security group rule.

        Returns:
            str: The status of the update operation: "Updated", "Error", or "Already Set".
        """
        # create the new ipv4 cidr
        new_ipv4_cidr = f'{ipv4_address}/32'

        # check if the new ipv4 cidr is different from the current rule
        if rule['CidrIpv4'] != new_ipv4_cidr:
            logger.info(f"Rule {rule['GroupId']} {rule['SecurityGroupRuleId']}:  Updating ipv4 rule to {new_ipv4_cidr}")

            # update the ipv4 CIDR
            SecurityGroupRule['CidrIpv4'] = new_ipv4_cidr

            # update the rule
            return self._modify_rule(rule['GroupId'], rule['SecurityGroupRuleId'], SecurityGroupRule)

        else:
            logger.info(f"Rule {rule['GroupId']} {rule['SecurityGroupRuleId']}: ipv4 address is the same as the current rule {rule['CidrIpv4']}")
            return "Already Set"

    def _modify_rule(self, group_id, rule_id, new_security_group_rule):
        """
        Modifies a security group rule.

        Args:
            group_id: The ID of the security group to modify.
            new_security_group_rule: The new security group rule to apply.

        Returns:
            dict: The response from the modify_security_group_rules operation.
        """

        # update the rule
        try:
            sg = self.ec2_client.modify_security_group_rules(
                GroupId=group_id,
                SecurityGroupRules=[{'SecurityGroupRuleId':rule_id,
                                'SecurityGroupRule':new_security_group_rule}]
            )
        except Exception as e:
            logger.info(f"Rule {group_id} {rule_id}:  Update was UNSUCCESSFUL. {e = }")
            return "Error"

        # check if the update was successful
        if sg['Return']:
            logger.info(f"Rule {group_id} {rule_id}:  Update was successful.")
            return "Updated"
        else:
            logger.info(f"Rule {group_id} {rule_id}:  Update was UNSUCCESSFUL. {sg =}")
            return "Error"

if __name__ == '__main__':
    region, tag = parse_args()

    ipv4_address, ipv6_address = get_ips()

    AWS_conn = AWS(region)
    AWS_conn.update_sg_rules(tag, ipv4_address, ipv6_address)
