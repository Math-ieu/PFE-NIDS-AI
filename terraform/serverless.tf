# SQS Queue for flow buffering
resource "aws_sqs_queue" "flow_queue" {
  name                      = "nids-flow-queue"
  delay_seconds             = 0
  max_message_size          = 262144
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
}

# DynamoDB for Alerts
resource "aws_dynamodb_table" "alerts_table" {
  name           = "NIDS-Alerts"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "alert_id"
  range_key      = "timestamp"

  attribute {
    name = "alert_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = { Name = "NIDS-Alerts-Table" }
}

# Lambda for Preprocessing
resource "aws_iam_role" "lambda_role" {
  name = "nids_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_sqs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

resource "aws_lambda_function" "preprocessor" {
  filename      = "lambda_function_payload.zip" # Placeholder
  function_name = "nids_preprocessor"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.handler"
  runtime       = "python3.10"

  environment {
    variables = {
      SQS_QUEUE_URL = aws_sqs_queue.flow_queue.id
    }
  }
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.flow_queue.arn
  function_name    = aws_lambda_function.preprocessor.arn
}
