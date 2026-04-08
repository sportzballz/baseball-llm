terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.38.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4.2"
    }
  }
  required_version = "~> 1.2"
}


variable "SPORTSPAGE_API_KEY" {
  default     = "SPORTSPAGE_API_KEY"
  description = "API key"
}


variable "SLACK_TOKEN" {
  default     = "invalid"
  description = "slack token"
}


variable "SPORTZBALLZ_SLACK_TOKEN" {
  default     = "invalid"
  description = "slack token"
}

variable "OPENAI_API_KEY" {
  default     = "OPENAI_API_KEY"
  description = "API key"
}


variable "MODEL" {
  default     = "dutch"
  description = "slack token"
}


resource "null_resource" "install_python_dependencies" {
  provisioner "local-exec" {
    command = "bash ${path.module}/src/scripts/create_pkg.sh"

    environment = {
      source_code_path = "${path.module}/src"
      function_name = "sportzballz"
      runtime = "python3.10"
      path_cwd = "${path.module}"
    }
  }
}


data "archive_file" "function_zip" {
  source_dir  = "src"
  type        = "zip"
  output_path = "${path.module}/sportzballz.zip"
  depends_on = [ null_resource.install_python_dependencies ]
}

resource "aws_s3_object" "file_upload" {
  bucket = "sportzballz-us-east-1-lambda"
  key    = "sportzballz.zip"
  source = "sportzballz.zip"
  depends_on = [ data.archive_file.function_zip ]
}

resource "aws_lambda_function" "function" {
  s3_bucket                       = "sportzballz-us-east-1-lambda"
  s3_key                          = "sportzballz.zip"
  function_name                   = "sportzballz"
  handler                        = "dutch.main"
  runtime                        = "python3.10"
  timeout                        = 900
  memory_size                    = 128
  role                           = "arn:aws:iam::716418748259:role/quantegy-execute-soak-us-east-1-lambdaRole"
  environment {
    variables = {
      SPORTSPAGE_API_KEY = var.SPORTSPAGE_API_KEY
      SLACK_TOKEN = var.SLACK_TOKEN
      SPORTZBALLZ_SLACK_TOKEN = var.SPORTZBALLZ_SLACK_TOKEN
      MODEL = var.MODEL
    }
  }
  depends_on = [ aws_s3_object.file_upload ]
}

