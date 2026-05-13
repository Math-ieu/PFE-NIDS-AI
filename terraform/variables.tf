variable "aws_region" {
  description = "AWS Region"
  default     = "eu-west-1"
}

variable "instance_type_victim" {
  default = "t3.micro" # Free Tier
}

variable "instance_type_ids" {
  default = "m7i.large" # 8 GB RAM - Compute optimized
}

variable "instance_type_soc" {
  default = "t3.micro" # Free Tier
}

variable "key_name" {
  description = "Name of the SSH key pair"
  default     = "nids-pfe-key"
}
