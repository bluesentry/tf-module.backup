#
# Filename:
# Description:
# Instructions:
# Author: Dennis Webb <dennis@bluesentryit.com>
# Date:
# History:
#
# Copyright (C) Blue Sentry, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
#
import json,boto3,botocore
from datetime import datetime, timedelta
access_key_id=''
secret_key_id=''
region=""
account_id=''
days_to_retain = 30
delete_snapshots = True
DO_NOT_DELETE_TAG = "DoNotDelete"
VERSION="0.1"

def main():
    start_time = datetime.utcnow()
    print("Script version %s started at %s\n" % \
          (VERSION, start_time.strftime("%Y/%m/%d %H:%M:%S UTC")))
    print "Searching for snapshots older than " + str(days_to_retain) + " days."
    ec2 = create_boto_resource("ec2",access_key_id,secret_key_id, region)
    all_snapshots = list(ec2.snapshots.filter(Filters=[
        {
            'Name': 'owner-id',
            'Values': [
                account_id
            ]
        }
    ]))
    print "Found " + str(len(all_snapshots)) + " snapshots."

    snapshot_retention_window_start_time = datetime.utcnow() - timedelta(days=days_to_retain)

    for snapshot in all_snapshots:
        #if snapshot age is less than retain days, don't check anything
        snapshot_date=snapshot.start_time.replace(tzinfo=None)
        #don't inspect anything if within retention window or tagged DoNotDelete
        if snapshot_date > snapshot_retention_window_start_time:
            print snapshot.id + " within retention window."
            continue
        if snapshot_tagged_do_not_delete(snapshot):
            print snapshot.id + " tagged " + DO_NOT_DELETE_TAG
            continue
        if delete_snapshots:
            try:
                snapshot.delete()
                print snapshot.id + " was deleted!"
            except:
                print snapshot.id + " in use!"
    print("Script finished at %s\n" % \
          datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S UTC"))

def snapshot_tagged_do_not_delete(snapshot):
    do_not_delete_tag_value = get_ec2_tag_value(snapshot,DO_NOT_DELETE_TAG)
    if do_not_delete_tag_value is None: return False
    #As long as some tag value is returned, then we'll say True
    return True

def get_name_tag(ec2_object):
    return get_ec2_tag_value(ec2_object,"Name")

def get_ec2_tag_value(ec2_object,tag_name):
    if ec2_object.tags is None: return None
    for tag in ec2_object.tags:
        if tag['Key'].lower()==tag_name.lower():
            tag_value = tag['Value']
            return tag_value or ""
    return None

def create_boto_resource(resource_name,access_key_id=None,secret_key_id=None,region=None):
    if access_key_id is None:
        access_key_id=''
    if secret_key_id is None:
        secret_key_id=''
    if region is None:
        region=''
    resource=None
    if len(access_key_id) > 0:
        resource = boto3.resource(
            resource_name,
            aws_access_key_id = access_key_id,
            aws_secret_access_key = secret_key_id,
            region_name=region
        )
    else:
        resource = boto3.resource(resource_name,region_name=region)
    return resource

#always at bottom
def lambda_handler(event, context):
    main()

if __name__ == '__main__':
    main()