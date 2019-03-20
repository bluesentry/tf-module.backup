
# Adds the BSI healthcheck role used to report on instance backup health

data "aws_iam_policy_document" "BSI-healthcheck-role-policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::964273422046:root"]
    }
  }
}

resource "aws_iam_role" "BSI_healthcheck_role" {
  count              = "${var.include == "true" && var.enable_msp_healthcheck_role =="true" ? 1 : 0}"
  name               = "BsiHealthCheck"
  assume_role_policy = "${data.aws_iam_policy_document.BSI-healthcheck-role-policy.json}"
}

resource "aws_iam_role_policy_attachment" "BSI-healthcheck-role-policy-attach" {
  count      = "${var.include == "true" && var.enable_msp_healthcheck_role =="true" ? 1 : 0}"
  role       = "${aws_iam_role.BSI_healthcheck_role.name}"
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess"
}