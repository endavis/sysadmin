# -*- coding: utf-8 -*-
# Project: sysadmin/AWS
# Filename: update_sg/update_sg_ipv6.py
#
# File Description: Update an SG with the ipv6 address of the current host.
#
# By: endavis

"""
This assumes there is a  ~/.aws/credentials of the form

-------------------------------
[<aws_profile>]
aws_access_key_id = <access_key_id>
aws_secret_access_key = <secret_access_key>
--------------------------------
"""
# Standard Library
import configparser
import os
import sys
import pprint
import datetime
import argparse

# 3rd Party
import boto3
import dns.message
import dns.rdatatype
import dns.query
import dns.resolver

def parse_args():
    parser = argparse.ArgumentParser(description='A script to update a security group with the current hosts public ipv4 and ipv6')
    parser.add_argument(
        '-sg',
        '--securitygroup',
        help='the security group id',
        required=True)

    parser.add_argument(
        '-p',
        '--profile',
        help='the name of the aws profile to use',
        required=True)

    parser.add_argument(
        '-r',
        '--region',
        help='the AWS region the security group is in',
        required=True)

    parser.add_argument(
        '-6',
        help='update ipv6 only',
        action='store_true',
        default=False)

    parser.add_argument(
        '-4',
        help='update ipv4 only',
        action='store_true',
        default=False)

    args = vars(parser.parse_args())
    return args['profile'], args['region'], args['securitygroup'], args['6'], args['4']


def get_ips():
    """
    we use google's DNS servers to get the public IPs for the host

    dig command: dig -6 TXT +short o-o.myaddr.l.google.com @ns1.google.com
    """
    r_google_ipv6 = dns.resolver.resolve("ns1.google.com", 'AAAA')
    r_google_ipv4 = dns.resolver.resolve("ns1.google.com", 'A')
    google_ipv6 = r_google_ipv6[0].address
    google_ipv4 = r_google_ipv4[0].address
    q = dns.message.make_query("o-o.myaddr.l.google.com", dns.rdatatype.TXT)
    r_ipv6 = dns.query.udp(q, google_ipv6)
    ipv6 = r_ipv6.answer[0][0].strings[0].decode()
    r_ipv4 = dns.query.udp(q, google_ipv4)
    ipv4 = r_ipv4.answer[0][0].strings[0].decode()

    return ipv4, ipv6

class AWS:
    def __init__(self, profile, region):
        path = os.environ['HOME'] + '/.aws/credentials'
        config = configparser.ConfigParser()
        config.read(path)
        self.profile = profile
        self.region = region

        if self.profile in config.sections():
            self.aws_access_key_id = config[self.profile]['aws_access_key_id']
            self.aws_secret_access_key = config[self.profile]['aws_secret_access_key']
        else:
            print(f"Cannot find profile '{self.profile}' in {path}")
            sys.exit()
        try:
            self.ec2 = boto3.resource('ec2',
                                    aws_access_key_id=self.aws_access_key_id,
                                    aws_secret_access_key=self.aws_secret_access_key,
                                    region_name=self.region)
        except Exception:
            print(e)
            sys.exit()

    def update_sg(self, sg_id, ipv4, ipv6):
        date = datetime.datetime.now(datetime.timezone.utc)
        datestring = date.strftime('%a %b %d %Y %H:%M:%S %Z')
        sg = self.ec2.SecurityGroup(sg_id)
        IpPermissions = {
                'IpProtocol':'tcp',
                'ToPort':22,
                'FromPort':22,
            }
        if ipv4:
            IpPermissions['IpRanges']=[{
                    'CidrIp':f'{ipv4}/32',
                    'Description': f'Added on {datestring}'
                    }]
        if ipv6:
            IpPermissions['Ipv6Ranges']= [{
                    'CidrIpv6':f'{ipv6}/128',
                    'Description': f'Added on {datestring}'
            }]

        retval = sg.authorize_ingress(
            GroupId=sg_id,
            IpPermissions=[IpPermissions]
        )

        if retval['Return'] == True:
            print('success!')


if __name__ == '__main__':
    profile, region, securitygroup, ipv6_only, ipv4_only = parse_args()

    ipv4, ipv6 = get_ips()

    if ipv4_only:
        ipv6 = None
    if ipv6_only:
        ipv4 = None
    AWS_conn = AWS(profile, region)
    AWS_conn.update_sg(securitygroup, ipv4, ipv6)
