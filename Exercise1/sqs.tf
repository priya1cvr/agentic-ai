# resource = Terraform is creating real infrastructure
# aws_sqs_queue = the AWS SQS resource type
# "poc_queue" = the name you gave this resource inside Terraform

resource "aws_sqs_queue" "poc_queue" {
  name = "POC-Queue"
}