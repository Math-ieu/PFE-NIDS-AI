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

variable "victims" {
  type = map(object({
    name          = string
    instance_type = string
    service_name  = string
  }))
  default = {
    "web" = {
      name          = "Victim-Web"
      instance_type = "t3.micro"
      service_name  = "apache2"
    },
    "db" = {
      name          = "Victim-DB"
      instance_type = "t3.micro"
      service_name  = "mariadb"
    },
    "file" = {
      name          = "Victim-File"
      instance_type = "t3.micro"
      service_name  = "samba"
    }
  }
}

variable "instance_type_kali" {
  description = "Instance type for Kali Linux attack machine"
  default     = "t3.medium"
}

