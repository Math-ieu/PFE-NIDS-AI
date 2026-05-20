data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
}

data "aws_ami" "kali" {
  most_recent = true
  owners      = ["679593333241"] # AWS Marketplace / Kali Linux

  filter {
    name   = "name"
    values = ["kali-last-snapshot-amd64-*"]
  }
}

locals {
  victim_user_data = {
    web = <<-EOF
          #!/bin/bash
          apt-get update
          apt-get install -y apache2 php libapache2-mod-php
          systemctl start apache2
          systemctl enable apache2
          echo "<h1>NIDS Victim Node - Web Service</h1>" > /var/www/html/index.html
          EOF
    db  = <<-EOF
          #!/bin/bash
          apt-get update
          apt-get install -y mariadb-server redis-server
          systemctl start mariadb
          systemctl enable mariadb
          systemctl start redis-server
          systemctl enable redis-server
          sed -i 's/127.0.0.1/0.0.0.0/g' /etc/mysql/mariadb.conf.d/50-server.cnf
          systemctl restart mariadb
          EOF
    file = <<-EOF
          #!/bin/bash
          apt-get update
          apt-get install -y samba vsftpd
          systemctl start smbd
          systemctl enable smbd
          systemctl start vsftpd
          systemctl enable vsftpd
          echo "anonymous_enable=YES" >> /etc/vsftpd.conf
          systemctl restart vsftpd
          EOF
  }
}

# Victim Nodes (Web, DB, File)
resource "aws_instance" "victim_node" {
  for_each      = var.victims
  ami           = data.aws_ami.ubuntu.id
  instance_type = each.value.instance_type
  subnet_id     = aws_subnet.public.id
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.victim_sg.id]

  root_block_device {
    volume_size = 10
    volume_type = "gp3"
  }

  user_data = local.victim_user_data[each.key]

  tags = {
    Name    = each.value.name
    Service = each.value.service_name
  }
}

# Security Group for Kali Linux Attack Machine
resource "aws_security_group" "kali_sg" {
  name        = "kali-sg"
  description = "Allow inbound SSH and RDP for Kali Attack machine"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Kali Linux Attack Machine
resource "aws_instance" "kali_attack" {
  ami           = data.aws_ami.kali.id
  instance_type = var.instance_type_kali
  subnet_id     = aws_subnet.public.id
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.kali_sg.id]

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  tags = { Name = "Kali-Attack" }
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

# SOC Node (Custom Dashboard)
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
              apt-get install -y python3-pip python3-dev nginx
              EOF

  tags = { Name = "SOC-Dashboard" }
}


resource "aws_eip" "ids_eip" {
  instance = aws_instance.ids_node.id
  domain   = "vpc"
}

resource "aws_eip" "soc_eip" {
  instance = aws_instance.soc_node.id
  domain   = "vpc"
}
