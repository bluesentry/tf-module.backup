#!/usr/bin/env python

#
# Filename: Ec2Backup.py
# Description:
# Instructions:
# Author: Dennis Webb <dennis@bluesentryit.com>
# Date: January 2016
# History:
#
# Copyright (C) Blue Sentry, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
#

import json,boto3
from datetime import datetime, timedelta

DO_NOT_BACKUP_EC2_VOL_FLAG = "BsiDoNotBackup"
SNAPSHOT_DESCRIPTION_PREFIX = "Created by BSIBackup - "
SKIP_WINDOWS=True
VERSION="0.1"

def main():
    start_time = datetime.utcnow()
    print("Script version %s started at %s\n" % \
          (VERSION, start_time.strftime("%Y/%m/%d %H:%M:%S UTC")))
    ec2 = boto3.resource("ec2")
    instances_to_backup = ec2.instances.all()
    volumes_to_backup = get_volumes_to_backup(instances_to_backup)
    create_snapshots(ec2,volumes_to_backup)
    print("Script finished at %s\n" % \
          datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S UTC"))

def get_volumes_to_backup(instances):
    volumes = list()
    for instance in instances:
        if (SKIP_WINDOWS and instance.platform == 'windows'):
            continue
        #if tagged BsiDoNotBackup, skip
        if (get_ec2_tag_value(instance,DO_NOT_BACKUP_EC2_VOL_FLAG) or "").lower() == "true":
            continue
        #go through the volumes now
        for instance_volume in instance.volumes.all():
            #if tagged BsiDoNotBackup, skip
            if (get_ec2_tag_value(instance_volume,DO_NOT_BACKUP_EC2_VOL_FLAG) or "").lower() == "true":
                continue
            volumes.append(instance_volume)
    return volumes

def create_snapshots(resource,volumes_to_backup):
    print("Preparing to snapshot %s volumes...\n" % (len(volumes_to_backup)))
    for volume in volumes_to_backup:
        #get instance name and device
        instance_id = volume.attachments[0]['InstanceId']
        instance_device = volume.attachments[0]['Device']
        instance_name = get_name_tag(resource.Instance(instance_id)) or ""
        if instance_name:
            instance_combined_name = instance_name + "(" + instance_id + ")"
        else:
            instance_combined_name = instance_id
        #create description
        snapshot_description = SNAPSHOT_DESCRIPTION_PREFIX + instance_combined_name
        #create snapshot
        volume_snapshot = volume.create_snapshot(snapshot_description)
        #tag snapshot
        volume_snapshot.create_tags(
            Tags=[
                {
                    'Key': 'CreatedBy',
                    'Value': 'BSIBackup'
                },
                {
                    'Key': 'InstanceId',
                    'Value': instance_id
                },
                {
                    'Key': 'InstanceDevice',
                    'Value': instance_device
                },
                {
                    'Key': 'Name',
                    'Value': instance_combined_name
                }
            ]
        )

def get_name_tag(ec2_object):
    return get_ec2_tag_value(ec2_object,"Name")

def get_ec2_tag_value(ec2_object,tag_name):
    if ec2_object.tags is None: return None
    for tag in ec2_object.tags:
        if tag['Key'].lower()==tag_name.lower():
            tag_value = tag['Value']
            return tag_value or ""
    return None

#always at bottom
def lambda_handler(event, context):
    main()

if __name__ == '__main__':
    main()