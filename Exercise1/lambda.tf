# Zips up lambda1/lambda_function.py automatically — Terraform's way of
# doing what the console's "upload code" button does
# It tells Terraform:
# “Take the file or folder at this path: ${path.module}/lambda1”
# “Create a ZIP archive from it” ,“Save the zip file here: ${path.module}/lambda1.zip”
# data means “read something from Terraform, not create AWS infrastructure directly”
# archive_file is a built-in Terraform provider resource/data source that archives files
# resource = Terraform is creating real infrastructure
# aws_lambda_function = the AWS Lambda resource type
# "poc_lambda_1" = the name you gave this resource inside Terraform

data "archive_file" "lambda1_zip" {
  type        = "zip"
  source_dir = "${path.module}/lambda1"
  output_path = "${path.module}/lambda1.zip"
}

# <section lambda 2> For Lambda 2, we do the same thing as above, but for the second Lambda function's code in lambda2/lambda_function.py
data "archive_file" "lambda2_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda2"
  output_path = "${path.module}/lambda2.zip"
}

# ---  Step 4.1: Creating the Lambda function ---
resource "aws_lambda_function" "poc_lambda_1" {
  function_name = "POC-Lambda-1"
  filename      = data.archive_file.lambda1_zip.output_path # the path to the zip file that Terraform just created
  role          = aws_iam_role.local_exec_role.arn # our one shared role from Step 1 workaround
  handler       = "lambda_function.lambda_handler" # the name of the file and function inside that file that AWS Lambda should invoke when the function is called
  runtime       = "python3.9"
  source_code_hash = data.archive_file.lambda1_zip.output_base64sha256

  
}

# ---  Step 4.2: Setting up SQS as a trigger ---
resource "aws_lambda_event_source_mapping" "sqs_to_lambda1" {
  event_source_arn = aws_sqs_queue.poc_queue.arn
  function_name    = aws_lambda_function.poc_lambda_1.arn
  batch_size       = 10
}

# ---  Step 7.1: Creating the POC-Lambda-2 function ---
resource "aws_lambda_function" "poc_lambda_2" {
  function_name    = "POC-Lambda-2"
  runtime          = "python3.9"
  handler          = "lambda_function.lambda_handler"
  role             = aws_iam_role.local_exec_role.arn
  filename         = data.archive_file.lambda2_zip.output_path
  source_code_hash = data.archive_file.lambda2_zip.output_base64sha256

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.poc_topic.arn   # this replaces PDF Step 7.3's manual ARN paste
    }
  }
}

# ---  Step 7.2: Setting up DynamoDB as a trigger ---
resource "aws_lambda_event_source_mapping" "dynamodb_to_lambda2" {
  event_source_arn  = aws_dynamodb_table.orders.stream_arn
  function_name     = aws_lambda_function.poc_lambda_2.arn
  starting_position = "LATEST"
}