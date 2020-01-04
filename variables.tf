

variable "additional_roles" {
  type        = list(string)
  description = "Additional instance role ARN's to include in backups"
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