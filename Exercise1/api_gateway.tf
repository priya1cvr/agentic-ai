# Steps 1-3: create the REST API shell (PDF: "POC-API")
resource "aws_api_gateway_rest_api" "poc_api" {
  name = "POC-API"
}

# The root resource ("/") already exists on every API — we attach our method there
# Steps 4-5: create the POST method
resource "aws_api_gateway_method" "post_method" {
  rest_api_id   = aws_api_gateway_rest_api.poc_api.id
  resource_id   = aws_api_gateway_rest_api.poc_api.root_resource_id
  http_method   = "POST"
  authorization = "NONE"
}

# Step 6: wire POST -> SQS SendMessage
resource "aws_api_gateway_integration" "post_to_sqs" {
  rest_api_id = aws_api_gateway_rest_api.poc_api.id
  resource_id = aws_api_gateway_rest_api.poc_api.root_resource_id
  http_method = aws_api_gateway_method.post_method.http_method
  integration_http_method = "POST"
  type                    = "AWS"
  credentials             = aws_iam_role.local_exec_role.arn
  uri                     = "arn:aws:apigateway:us-east-1:sqs:path/000000000000/${aws_sqs_queue.poc_queue.name}"

   # Steps 9-13: HTTP header - tells SQS the incoming content type
  request_parameters = {
    "integration.request.header.Content-Type" = "'application/x-www-form-urlencoded'"
  }

  # Steps 14-17: mapping template - reformats the JSON body into SQS's expected format
  request_templates = {
    "application/json" = "Action=SendMessage&MessageBody=$input.body"
  }

  passthrough_behavior = "NEVER"   # Step 14: "Request body passthrough: Never"
}

# Required so API Gateway knows what to do with SQS's response (even though we mostly ignore it)
resource "aws_api_gateway_method_response" "post_200" {  # Step 15: tells API Gateway what to do with SQS's response
  rest_api_id = aws_api_gateway_rest_api.poc_api.id
  resource_id = aws_api_gateway_rest_api.poc_api.root_resource_id
  http_method = aws_api_gateway_method.post_method.http_method
  status_code = "200"
}

resource "aws_api_gateway_integration_response" "post_to_sqs_response" { # Step 15: tells API Gateway what to do with SQS's response
  rest_api_id = aws_api_gateway_rest_api.poc_api.id # Step 15: attach the integration response to the API
  resource_id = aws_api_gateway_rest_api.poc_api.root_resource_id # Step 15: attach the integration response to the root resource
  http_method = aws_api_gateway_method.post_method.http_method # Step 15: attach the integration response to the POST method
  status_code = aws_api_gateway_method_response.post_200.status_code # Step 15: attach the integration response to the 200 method response

  depends_on = [aws_api_gateway_integration.post_to_sqs]
}

# Deploys the API so it's actually reachable at a URL
resource "aws_api_gateway_deployment" "poc_deployment" { # Step 18: create a deployment for the API
  rest_api_id = aws_api_gateway_rest_api.poc_api.id # Step 18: attach the deployment to the API

  depends_on = [ # Step 18: make sure the deployment happens after all the other API Gateway resources are created
    aws_api_gateway_integration.post_to_sqs, # Step 18: make sure the deployment happens after the integration is created
    aws_api_gateway_integration_response.post_to_sqs_response 
  ]
}

resource "aws_api_gateway_stage" "poc_stage" { # Step 18: create a stage for the deployment
  rest_api_id   = aws_api_gateway_rest_api.poc_api.id # Step 18: attach the stage to the API
  deployment_id = aws_api_gateway_deployment.poc_deployment.id # Step 18: attach the stage to the deployment
  stage_name    = "test" # Step 18: name the stage "test" (so the URL will be https://<api-id>.execute-api.<region>.amazonaws.com/test)
}
