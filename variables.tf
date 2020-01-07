
variable "include" {
  description = "Include in install.  If set to false related resources will not be installed."
  default     = true
  type        = bool
}

variable "additional_roles" {
  type        = list(string)
  description = "Additional instance role ARN's to include in backups"
  default     = []
}

variable "enable_msp_healthcheck_role" {
  description = "If true, the bsi_healthcheck cross account role will be provisioned"
  default     = "true"
}

variable "run_at_expression" {
  description = "Interval used for running backup as a cron expression"
  default     = "cron(00 03 ? * * *)"
}

variable "tags" {
  type    = map(string)
  default = {}
}