## resource = Terraform is creating real infrastructure
resource "aws_iam_role" "local_exec_role" {
  name = "local-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = ["lambda.amazonaws.com", "apigateway.amazonaws.com"]
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "local_exec_admin" {
  role       = aws_iam_role.local_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}