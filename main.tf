resource "aws_iam_role" "BsiBackup" {
  count = "${var.include == "true" ? 1 : 0}"
  name  = "BsiBackup"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": [
          "ec2.amazonaws.com",
          "lambda.amazonaws.com"
        ]
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_instance_profile" "BsiBackup" {
  count = "${var.include == "true" ? 1 : 0}"
  name  = "BsiBackup"
  role  = "${aws_iam_role.BsiBackup.name}"
}

resource "aws_iam_policy" "BsiBackuppolicy" {
  count  = "${var.include == "true" ? 1 : 0}"
  name   = "ec2-access-policy"
  policy = "${data.aws_iam_policy_document.BsiBackuppolicyDoc.json}"
}
data "aws_iam_policy_document" "BsiBackuppolicyDoc"{
  "statement" {
    sid = "BsiBackuppolicy"
    effect = "Allow"
    actions = [
      "ec2:CreateImage",
      "ec2:CreateSnapshot",
      "ec2:CreateTags",
      "ec2:DeleteSnapshot",
      "ec2:DescribeInstanceAttribute",
      "ec2:DescribeInstanceStatus",
      "ec2:DescribeInstances",
      "ec2:DescribeSnapshotAttribute",
      "ec2:DescribeSnapshots",
      "ec2:DescribeTags",
      "ec2:DescribeVolumeAttribute",
      "ec2:DescribeVolumeStatus",
      "ec2:DescribeVolumes",
      "ec2:ModifySnapshotAttribute"
    ]
    resources = ["*"]
  }
}
resource "aws_iam_role_policy_attachment" "bsiaccess" {
  count      = "${var.include == "true" ? 1 : 0}"
  role       = "${aws_iam_role.BsiBackup.name}"
  policy_arn = "${aws_iam_policy.BsiBackuppolicy.arn}"
}


resource "aws_iam_role_policy_attachment" "ec2ssm" {
  count      = "${var.include == "true" ? 1 : 0}"
  role       = "${aws_iam_role.BsiBackup.name}"
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
}

resource "aws_iam_role_policy_attachment" "bsiaccess_extra" {
  count ="${length(var.additional_roles)}"
  policy_arn = "${aws_iam_policy.BsiBackuppolicy.arn}"
  role = "${var.additional_roles[count.index]}"
}

resource "aws_iam_role_policy_attachment" "ec2ssm_extra" {
  count ="${length(var.additional_roles)}"
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
  role = "${var.additional_roles[count.index]}"
}

locals {
  arns = "${concat(aws_iam_role.BsiBackup.*.arn, var.additional_roles)}"
}


//  Lambda - windows
data "template_file" "win-backup" {
  template = "${file("${path.module}/win-lambda/win_lambda.py")}"
  vars {
    PROFILE_ARN = "${join(",", local.arns)}"
  }
}

data "archive_file" "win-backup" {
  source_content = "${data.template_file.win-backup.rendered}"
  source_content_filename = "win_lambda.py"
  output_path = "win-backup-lambda.zip"
  type        = "zip"
}

resource "aws_lambda_function" "win-backup" {
  count            = "${var.include == "true" ? 1 : 0}"
  function_name    = "bsi-win-backup"
  role             = "${aws_iam_role.BsiBackup.arn}"
  handler          = "win_lambda.lambda_handler"
  runtime          = "python2.7"
  timeout          = 300
  filename         = "${data.archive_file.win-backup.output_path}"
  source_code_hash = "${data.archive_file.win-backup.output_base64sha256}"
  tags             = "${var.tags}"
}

resource "aws_lambda_permission" "win" {
  count = "${(var.run_at_expression != "" && var.include == "true") ? 1 : 0}"

  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.win-backup.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.win.arn}"
}

resource "aws_cloudwatch_event_rule" "win" {
  count = "${(var.run_at_expression != "" && var.include == "true") ? 1 : 0}"

  name                = "${aws_lambda_function.win-backup.function_name}_main_cron"
  description         = "${aws_lambda_function.win-backup.function_name}_main_cron"
  schedule_expression = "${var.run_at_expression}"
}

resource "aws_cloudwatch_event_target" "win" {
  count = "${(var.run_at_expression != "" && var.include == "true") ? 1 : 0}"

  rule      = "${aws_cloudwatch_event_rule.win.name}"
  target_id = "${aws_lambda_function.win-backup.function_name}"
  arn       = "${aws_lambda_function.win-backup.arn}"
}


// Lambda - linux
data "archive_file" "linux-backup" {
  source_content = "${file("${path.module}/linux-lambda/linux-lambda.py")}"
  source_content_filename = "linux-lambda.py"
  output_path = "linux-backup-lambda.zip"
  type        = "zip"
}

resource "aws_lambda_function" "linux-backup" {
  count            = "${var.include == "true" ? 1 : 0}"
  function_name    = "bsi-linux-backup"
  role             = "${aws_iam_role.BsiBackup.arn}"
  handler          = "linux-lambda.lambda_handler"
  runtime          = "python2.7"
  timeout          = 300
  filename         = "${data.archive_file.linux-backup.output_path}"
  source_code_hash = "${data.archive_file.linux-backup.output_base64sha256}"
  tags             = "${var.tags}"
}

resource "aws_lambda_permission" "linux" {
  count = "${(var.run_at_expression != "" && var.include == "true") ? 1 : 0}"

  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.linux-backup.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.linux.arn}"
}

resource "aws_cloudwatch_event_rule" "linux" {
  count = "${(var.run_at_expression != "" && var.include == "true") ? 1 : 0}"

  name                = "${aws_lambda_function.linux-backup.function_name}_main_cron"
  description         = "${aws_lambda_function.linux-backup.function_name}_main_cron"
  schedule_expression = "${var.run_at_expression}"
}

resource "aws_cloudwatch_event_target" "linux" {
  count = "${(var.run_at_expression != "" && var.include == "true") ? 1 : 0}"

  rule      = "${aws_cloudwatch_event_rule.linux.name}"
  target_id = "${aws_lambda_function.linux-backup.function_name}"
  arn       = "${aws_lambda_function.linux-backup.arn}"
}


// Lambda - snapshot cleanup
data "archive_file" "ebs-cleanup" {
  source_content = "${file("${path.module}/snapshot-cleanup/snapshot-cleanup.py")}"
  source_content_filename = "snapshot-cleanup.py"
  output_path = "snapshot-cleanup-lambda.zip"
  type        = "zip"
}

resource "aws_lambda_function" "ebs-cleanup" {
  count            = "${var.include == "true" ? 1 : 0}"
  function_name    = "bsi-linux-backup"
  role             = "${aws_iam_role.BsiBackup.arn}"
  handler          = "snapshot-cleanup.lambda_handler"
  runtime          = "python2.7"
  timeout          = 300
  filename         = "${data.archive_file.ebs-cleanup.output_path}"
  source_code_hash = "${data.archive_file.ebs-cleanup.output_base64sha256}"
  tags             = "${var.tags}"
}

resource "aws_lambda_permission" "ebs-cleanup" {
  count = "${(var.run_after_expression != "" && var.include == "true") ? 1 : 0}"

  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.ebs-cleanup.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.snapshot-cleanup.arn}"
}

resource "aws_cloudwatch_event_rule" "snapshot-cleanup" {
  count = "${(var.run_at_expression != "" && var.include == "true") ? 1 : 0}"

  name                = "${aws_lambda_function.ebs-cleanup.function_name}_main_cron"
  description         = "${aws_lambda_function.ebs-cleanup.function_name}_main_cron"
  schedule_expression = "${var.run_after_expression}"
}

resource "aws_cloudwatch_event_target" "ebs-cleanup" {
  count = "${(var.run_after_expression != "" && var.include == "true") ? 1 : 0}"

  rule      = "${aws_cloudwatch_event_rule.snapshot-cleanup.name}"
  target_id = "${aws_lambda_function.ebs-cleanup.function_name}"
  arn       = "${aws_lambda_function.ebs-cleanup.arn}"
