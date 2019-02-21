
variable "include" {
  description = "Include in install.  If set to false related resources will not be installed."
  default = "true"
}

variable "additional_roles" {
  type        = "list"
  description = "Additional instance role profile ARN's to include in backups"
  default     = []
}

variable "run_at_expression" {
  description = "Interval used for running backup as a cron expression"
  default     = "cron(00 03 ? * * *)"
}

variable "tags" {
  type    = "map"
  default = {}
}