/**
 * TERRAFORM BACKEND CONFIGURATION
 * Configures remote state management in S3 with DynamoDB locking
 */

terraform {
  backend "s3" {
    bucket         = "tastefully-stained-tfstate"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
