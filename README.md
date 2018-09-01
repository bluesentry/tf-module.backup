# tf-module.backup #
Terraform module for setup of instance snapshots.

## Usage ##
```hcl-terraform
module "ec2-backup" {
  source            = "git@github.com:bluesentry/tf-module.backup.git"
  version           = "v1.0.0"
  run_at_expression = "cron(30 02 ? * * *)"
  tags              = "${local.tags}"
}
```

## What's created? ##

* BSIBackup profile instance & associated role and policy
* Lambda functions (windows and linux)
* Cloudwatch rule and target for cron job that will trigger backup


## Argument Reference ##
The following module level arguments are supported.

* additional_roles - (Optional) List of additional roles that will be included in backups

* run_at_expression - (Optional) Expression used by cron job to determine when backup will run.  Defaults to ``cron(00 03 ? * * *)``, which will run backup every day at 3am.  For more details, see AWS documentation.  (https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html)

* tags - (Optional) The tags assigned to all related resources that can be tagged.


## Outputs ##

* backup_role_arn - ARN for the newly created backup role

* backup_role_name - Name of the backup role