#!/usr/bin/env python

#
# Filename: bsi_backup_ec2.py
# Description:
# Instructions:
# Author: Dennis Webb <dennis@bluesentryit.com>
# Date: November 2016
# History:
#
# Copyright (C) Blue Sentry, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
#

import json,boto3
from datetime import datetime, timedelta

powershell_script = '''
#
# Filename: EC2BackupWithVss.ps1
# Description: Creates necessary script files for DRIVESHADOW.EXE to create
#              VSS Snapshot before creating EC2 Snapshot
# Author: Dennis Webb <dennis@bluesentryit.com>
# Date: November 2016
# History:
#
# Copyright (C) Blue Sentry, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
#

#Global Variables
$DO_NOT_BACKUP_EC2_VOL_FLAG = "BsiDoNotBackup"
$scriptPath = split-path -parent $MyInvocation.MyCommand.Definition
$region = ""
#imports
import-module AwsPowerShell
$DshScriptFilename = $env:TEMP +"\Create.dsh" #Create.dsh passed to DiskShadow
                                                #to script shadow creation
$CreateSnapshotsFilename = $env:TEMP + "\CreateSnapshots.ps1"
$CreateSnapshotsCMDFilename = $env:TEMP + "\CreateSnapshots.cmd"
#createsnapshots.cmd calls createsnapshots.ps1 for each volume during diskshadow script
#Main-Function
function main {
    $global:region = get-region
    Initialize-AWSDefaults -Region $global:region
    #get list of all NTFS volumes
    $instanceID = GetInstanceId
    $NtfsVolumes = GetNtfsLocalFixedDisks
    $Ec2Volumes = GetEc2VolumesToBackup $instanceID

    CreateShadowStorage $NtfsVolumes
    $DshScript = CreateDshScript $NtfsVolumes $CreateSnapshotsCMDFilename
    $CreateSnapshotsPsScript = CreateSnapshotsPowershellScript $Ec2Volumes $instanceID $SNS_TOPIC
    $CreateSnapshotsCmdScript = CreateSnapshotsCmdScript $CreateSnapshotsFilename
    CreateTemporaryScriptFiles $DshScript $DshScriptFilename $CreateSnapshotsPsScript $CreateSnapshotsFilename $CreateSnapshotsCmdScript $CreateSnapshotsCMDFilename
    RunSnapshotScripts
    DeleteTemporaryScriptFiles $DshScriptFilename $CreateSnapshotsFilename $CreateSnapshotsCMDFilename
    #DeleteExpiredSnapshots $Ec2Volumes $RETENTION $RETENTION_MINIMUM
}
#Help-Functions
function GetNtfsLocalFixedDisks {
    Get-WmiObject -Class Win32_LogicalDisk |
            Where-Object {
                ($_.FileSystem -eq "NTFS") -and
                ($_.DeviceID.Length -eq 2) -and
                ($_.DriveType -eq 3) -and
                ($_.MediaType -eq 12)
            }
}
function GetInstanceId {
    return (New-Object System.Net.WebClient).DownloadString("http://169.254.169.254/latest/meta-data/instance-id")
}
function GetEc2VolumesToBackup ($instanceID){
    $ec2Vols = [System.Collections.ArrayList]@((Get-EC2Volume) | ? { $_.Attachments[0].InstanceId -eq $instanceID})
    $doNotBackupVols = New-Object system.Collections.ArrayList($null)

    foreach ($ec2Vol in $ec2Vols) {
        #let's see if it's flagged BsiDoNotBackup, if so, add it to the doNotBackup list
        $DoNotBackupFlag = (Get-EC2Tag | ? {$_.ResourceId -eq $ec2Vol.VolumeId -and $_.Key -eq $DO_NOT_BACKUP_EC2_VOL_FLAG}).value
        if($DoNotBackupFlag -eq $null){$DoNotBackupFlag=''}
        if($DoNotBackupFlag.ToLower().Trim() -eq "true"){
            $doNotBackupVols.Add($ec2Vol)
        }
    }
    #take doNotBackup volumes out of the backup array
    foreach ($doNotBackupVol in $doNotBackupVols) {
         $ec2Vols.Remove($doNotBackupVol)
    }
    return $ec2Vols
}
function CreateShadowStorage($Volumes){
    #create vssstorage on each volume.  Needed to make sure VSSStorage is located on same volume
    $Volumes | ForEach-Object {
        $DriveLetter = $_.DeviceID
        Start-Process "vssadmin.exe" -Args "Add ShadowStorage /For=$DriveLetter /On=$DriveLetter /MaxSize=10%" -NoNewWindow -Wait
        Start-Process "vssadmin.exe" -Args "Resize ShadowStorage /For=$DriveLetter /On=$DriveLetter /MaxSize=10%" -NoNewWindow -Wait
    }
}
function CreateDshScript($Volumes,$CMDFilename){
    $CreateDsh = "set context persistent`r`n"
    #this causes all the VSS Writers to flush their caches and make files consistent
    $CreateDsh += "set option txfrecover`r`n"
    #Add every NTFS Volume to the shadowset
    $Volumes | ForEach-Object {
        $DriveLetter = $_.DeviceID
        $CreateDsh += "add volume $DriveLetter ALIAS DRIVE_" + $DriveLetter.Substring(0,1) + "`r`n"
    }
    #create shadow set
    $CreateDsh += "create`r`n"
    #run the batch file that triggers the New-Ec2Snapshot
    $CreateDsh += "exec " + $CMDFilename + "`r`n"
    #delete shadow copies to cleaup
    $Volumes | ForEach-Object {
        $DriveLetter = $_.DeviceID
        $CreateDsh += "delete shadows ID %DRIVE_" + $DriveLetter.Substring(0,1) + "%`r`n"
    }
    return $CreateDsh
}
function CreateSnapshotsPowershellScript($Ec2Volumes, $instanceID, $SnsTopicArn){
    #attempt to retrieve Name tag from instance
    $Ec2Name = (Get-EC2Tag | ? {$_.ResourceId -eq $instanceId -and $_.Key -eq 'Name'}).value
    if($Ec2Name -eq $null){$Ec2Name=''}
    $WindowsName = hostname
    $BackupTimeStamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    $DescriptionPrefix = "Created by BSIBackup - " + $WindowsName
    If($Ec2Name -eq '' -or $Ec2Name -eq $WindowsName) {$DescriptionPrefix += '(' + $instanceID + ')'}
    Else {$DescriptionPrefix += '(' + $instanceID + ';' + $Ec2Name +')'}
    #Let's create our initial tags for each snapshot
    $CreateSnapshots = "import-module AwsPowerShell`r`n"
    $CreateSnapshots += "Initialize-AWSDefaults -AccessKey $AWSAccessKey -SecretKey $AWSSecretKey -Region $global:region`r`n"
    $CreateSnapshots += "`$CreatedByTag = New-Object Amazon.EC2.Model.Tag`r`n"
    $CreateSnapshots += "`$CreatedByTag.Key = `"CreatedBy`"`r`n"
    $CreateSnapshots += "`$CreatedByTag.Value = `"BSIBackup`"`r`n"
    $CreateSnapshots += "`$NameTag = New-Object Amazon.EC2.Model.Tag`r`n"
    $CreateSnapshots += "`$NameTag.Key = `"Name`"`r`n"
    $Ec2Volumes | ForEach-Object {
        $Ec2VolumeID = $_.VolumeId

        $CreateSnapshots += "`$NewSnapshot = New-Ec2Snapshot -VolumeId " + $Ec2VolumeID + " -Description '" + $DescriptionPrefix + ' from ' + $Ec2VolumeID + ' on ' + $BackupTimeStamp + "' `r`n"
        $CreateSnapshots += "`$NameTag.Value = `"$WindowsName($Ec2VolumeID)`"`r`n"
        $CreateSnapshots += "`$SnapshotTags = @()`r`n"
        $CreateSnapshots += "`$SnapshotTags += `$CreatedByTag`r`n"
        $CreateSnapshots += "`$SnapshotTags += `$NameTag`r`n"
        $CreateSnapshots += "New-EC2Tag -Resource `$NewSnapshot.SnapshotId -Tags `$SnapshotTags`r`n"
    }

    $CreateSnapshots += "sleep(15)`r`n"
    return $CreateSnapshots
}
function CreateSnapshotsCmdScript($PowershellFilename){
    return "powershell.exe  -executionpolicy unrestricted -file " + $PowershellFilename
}
function CreateTemporaryScriptFiles($DshScript, $DshFilename, $PowershellScript, $PowershellFilename, $CMDScript, $CMDFilename){
    $DshScript | Out-File -FilePath $DshFilename -Force -Encoding ascii
    $PowershellScript | Out-File -FilePath $PowershellFilename -Force -Encoding ascii
    $CMDScript | Out-File -FilePath $CMDFilename -Force -Encoding ascii
}
function RunSnapshotScripts{
    Start-Process "diskshadow.exe" -Args "-s %temp%\create.dsh" -WorkingDirectory $env:TEMP -Wait -NoNewWindow
}
function DeleteTemporaryScriptFiles($DshScriptFilename, $PowershellFilename, $CMDFilename){
    Remove-Item -Path $DshScriptFilename
    Remove-Item -Path $PowershellFilename
    Remove-Item -Path $CMDFilename
}
function get-metadata {
    $extendurl = $args
    $baseurl = "http://169.254.169.254/latest/meta-data"
    $fullurl = $baseurl + $extendurl
    return ((New-Object System.Net.WebClient).DownloadString($fullurl))
}
function get-region {
    $az = get-metadata ("/placement/availability-zone")
    return ($az.Substring(0, ($az.Length -1)))
}
#Entry point
main
'''

def main():
    start_time = datetime.utcnow()
    print("Script started at %s\n" % \
          (start_time.strftime("%Y/%m/%d %H:%M:%S UTC")))
    ec2 = boto3.resource('ec2')
    ssm_client = boto3.client('ssm')
    instances = list(ec2.instances.filter(Filters=[
        {
            'Name': 'platform',
            'Values': [
                'windows'
            ]
        },
        {
            'Name': 'instance-state-name',
            'Values': [
                'running'
            ]
        },
        {
            'Name': 'iam-instance-profile.arn',
            'Values': '${PROFILE_ARN}'.split(',')
        }
    ]))
    print ("Instance count: " + str(len(instances)))
    for instance in instances:
        try:
            ssm_client.send_command(
                InstanceIds=[instance.instance_id],
                DocumentName="AWS-RunPowerShellScript",
                TimeoutSeconds=3600,
                Parameters={
                    "commands": [
                        powershell_script,
                    ]
                },
            )
        except:
            print ("Error with send_command to " + instance.instance_id)
    print("Script finished at %s\n" % \
          datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S UTC"))

def lambda_handler(event, context):
    main()

if __name__ == '__main__':
    main()