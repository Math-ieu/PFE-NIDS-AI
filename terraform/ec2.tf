data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
}

# Victim Node (Web Server)
resource "aws_instance" "victim_node" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type_victim
  subnet_id     = aws_subnet.public.id
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.victim_sg.id]

  root_block_device {
    volume_size = 10
    volume_type = "gp3"
  }

  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y apache2 php libapache2-mod-php
              systemctl start apache2
              systemctl enable apache2
              echo "<h1>NIDS Victim Node - PFE AI</h1>" > /var/www/html/index.html
              EOF

  tags = { Name = "Victim-Node" }
}

# IDS Node (FastAPI + AI Model)
resource "aws_instance" "ids_node" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type_ids
  subnet_id     = aws_subnet.public.id
  key_name      = var.key_name

  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids = [aws_security_group.ids_sg.id]

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y python3-pip python3-dev libpcap-dev
              pip3 install fastapi uvicorn torch pandas scikit-learn scapy nfstream boto3
              
              # Configuration pour recevoir le trafic miroir (VXLAN)
              # Note: Le trafic miroir arrive encapsulé dans du VXLAN (port 4789)
              EOF

  tags = { Name = "IDS-Node" }
}

# SOC Node (Grafana)
resource "aws_instance" "soc_node" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type_soc
  subnet_id     = aws_subnet.public.id
  key_name      = var.key_name

  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids = [aws_security_group.ids_sg.id] # Reuse SG for simplicity

  root_block_device {
    volume_size = 10
    volume_type = "gp3"
  }

  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y apt-transport-https software-properties-common wget
              wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -
              add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
              apt-get update
              apt-get install -y grafana
              systemctl start grafana-server
              systemctl enable grafana-server
              EOF

  tags = { Name = "SOC-Grafana" }
}

# Elastic IPs
resource "aws_eip" "victim_eip" {
  instance = aws_instance.victim_node.id
  domain   = "vpc"
}

resource "aws_eip" "ids_eip" {
  instance = aws_instance.ids_node.id
  domain   = "vpc"
}

resource "aws_eip" "soc_eip" {
  instance = aws_instance.soc_node.id
  domain   = "vpc"
}
