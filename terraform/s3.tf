resource "aws_s3_bucket" "models_bucket" {
  bucket = "nids-models-bucket"

  tags = { Name = "NIDS-Models-Registry" }
}

resource "aws_s3_bucket_versioning" "models_versioning" {
  bucket = aws_s3_bucket.models_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "models_pab" {
  bucket = aws_s3_bucket.models_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
