# tf-module.backup #
Terraform module for setup of instance snapshots.

## Usage ##
```hcl-terraform
module "ec2-backup" {
  source            = "git@github.com:bluesentry/tf-module.backup.git?ref=v2.0.0"
  run_at_expression = "cron(30 02 ? * * *)"
  tags              = local.tags
}
```

## Terraform versions ##
Terraform 0.12. Pin module version to ~> v2.0. Code changes are handled in `master` branch

Terraform 0.11. Pin module version to ~> v1.0. Code changes are handled in `v11` branch

## What's created? ##

* BSIBackup profile instance & associated role and policy
* Lambda functions (windows and linux)
* Cloudwatch rule and target for cron job that will trigger backup
* BsiHealthCheck cross account role (if enabled)


## Argument Reference ##
The following module level arguments are supported.

* **additional_roles** - (Optional) List of additional roles that will be included in backups

* **include** - (Optional) If set to false, no resources will be added. Defaults to `true`.  See [details section](#include-argument-details)

* **enable_msp_healthcheck_role** - (Optional) If true, bsi_healthcheck cross account role will be provisioned.  Defaults to `true`.

* **run_at_expression** - (Optional) Expression used by cron job to determine when backup will run.  Defaults to ``cron(00 03 ? * * *)``, which will run backup every day at 3am.  If expression is left blank, no cloudwatch configurations will be made.  For more details, see AWS documentation.  (https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html)

* **tags** - (Optional) The tags assigned to all related resources that can be tagged.


## Outputs ##

* **backup_role_arn** - ARN for the newly created backup role

* **backup_role_name** - Name of the backup role



## Include Argument Details ##
The `Include` argument is provided as a way of conditionally installing this module.  Currently terraform doesn't offer module level condition logic.
This is a work around to that missing logic.  

Example Scenario:  Multiple workspaces exist in a single AWS account.  The backup module only needs to be installed once.  To do this, the include argument can be used to specify which environment/state file the backup module's resources will be installed

```hcl-terraform
module "backup" {
  source            = "git@github.com:bluesentry/tf-module.backup.git?ref=v1.0.3"
  run_at_expression = "cron(00 03 ? * * *)"
  include           = terraform.workspace == "dev" ? true : false
  tags              = local.tags
}
```