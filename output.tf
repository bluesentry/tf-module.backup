
output "backup_role_arn" {
  value = "${aws_iam_role.BsiBackup.arn}"
}

output "backup_role_name" {
  value = "${aws_iam_role.BsiBackup.name}"
}