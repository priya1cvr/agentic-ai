# ---  Step 6.1: Creating a topic ---
resource "aws_sns_topic" "poc_topic" {
  name = "POC-Topic"
}

# ---  Step 6.2: Subscribing to email notifications ---
resource "aws_sns_topic_subscription" "poc_email_sub" {
  topic_arn = aws_sns_topic.poc_topic.arn
  protocol  = "email"
  endpoint  = "john@zoho.com"
}