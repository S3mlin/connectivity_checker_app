terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket         = "site-connectivity-checker-terraform-state"
    key            = "global/s3/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = "eu-central-1"
}

# --- 1. DATA SOURCES ---

data "aws_ami" "ubuntu" {
  most_recent = true
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["099720109477"]
}

data "aws_secretsmanager_secret" "app_secrets" {
  name = "django_production_secrets"
}

data "aws_secretsmanager_secret_version" "app_secrets_values" {
  secret_id = data.aws_secretsmanager_secret.app_secrets.id
}


# --- 2. IAM ROLE FOR EC2 ---

resource "aws_iam_role" "ec2_secrets_role" {
  name = "ec2_secrets_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "secrets_policy" {
  name        = "ec2_read_secrets_policy"
  description = "Allow EC2 to read Secrets Manager"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action   = ["secretsmanager:GetSecretValue"]
      Effect   = "Allow"
      Resource = data.aws_secretsmanager_secret.app_secrets.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "attach_secrets_policy" {
  role       = aws_iam_role.ec2_secrets_role.name
  policy_arn = aws_iam_policy.secrets_policy.arn
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ec2_secrets_profile"
  role = aws_iam_role.ec2_secrets_role.name
}

resource "aws_eip" "django_eip" {
  instance = aws_instance.django_server.id
  vpc      = true
}


# --- 3. SECURITY GROUPS ---

resource "aws_security_group" "django_sg" {
  name        = "django-web-sg"
  description = "Allow Web and SSH"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 22
    to_port     = 22
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

resource "aws_security_group" "rds_sg" {
  name        = "django-db-sg"
  description = "Allow traffic from Web Server"
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.django_sg.id] 
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}


# --- 4. SSH KEY ---

resource "aws_key_pair" "deployer" {
  key_name   = "django-deploy-key"
  public_key = file("~/.ssh/aws_deploy_key.pub")
}


# --- 5. THE DATABASE (RDS) ---

resource "aws_db_instance" "default" {
  allocated_storage      = 10
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.micro" 
  
  db_name  = jsondecode(data.aws_secretsmanager_secret_version.app_secrets_values.secret_string)["POSTGRES_NAME"]
  username = jsondecode(data.aws_secretsmanager_secret_version.app_secrets_values.secret_string)["POSTGRES_USER"]
  password = jsondecode(data.aws_secretsmanager_secret_version.app_secrets_values.secret_string)["POSTGRES_PASSWORD"]
  
  parameter_group_name   = "default.postgres16"
  skip_final_snapshot    = true
  publicly_accessible    = false 
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
}


# --- 6. THE WEB SERVER (EC2) ---

resource "aws_instance" "django_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.micro"
  key_name               = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.django_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  user_data = <<-EOF
#!/bin/bash
set -e

# 1. ADD SWAP MEMORY
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 2. Install Docker, Compose, jq, and unzip
apt-get update
apt-get install -y docker.io docker-compose-v2 jq unzip
systemctl start docker
systemctl enable docker
usermod -aG docker ubuntu

# 3. Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
./aws/install

# 4. FETCH SECRETS & CREATE .env FILE
export AWS_PAGER=""
/usr/local/bin/aws secretsmanager get-secret-value --secret-id django_production_secrets --region eu-central-1 --query SecretString --output text > /tmp/secrets.json

jq -r 'to_entries | .[] | .key + "=" + .value' /tmp/secrets.json > /home/ubuntu/.env
rm /tmp/secrets.json

# Append dynamic variables
echo "POSTGRES_HOST=${aws_db_instance.default.address}" >> /home/ubuntu/.env
echo "POSTGRES_PORT=${aws_db_instance.default.port}" >> /home/ubuntu/.env
echo "DEBUG=False" >> /home/ubuntu/.env
echo "CELERY_BROKER_URL=redis://redis:6379/0" >> /home/ubuntu/.env
echo "CELERY_RESULT_BACKEND=redis://redis:6379/0" >> /home/ubuntu/.env

# Fix permissions so the ubuntu user can read the .env file
chown ubuntu:ubuntu /home/ubuntu/.env

EOF

  tags = {
    Name = "Django-RDS-Server"
  }
}

# --- 7. OUTPUTS ---

output "app_url" {
  value = "http://${aws_eip.django_eip.public_ip}"
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/aws_deploy_key ubuntu@${aws_eip.django_eip.public_ip}"
}

# --- 8. TERRAFORM STATE BACKEND RESOURCES ---

# Create the S3 Bucket
resource "aws_s3_bucket" "terraform_state" {
  bucket = "site-connectivity-checker-terraform-state"
}

# Enable versioning so you can recover from accidental state deletions
resource "aws_s3_bucket_versioning" "terraform_state_versioning" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption by default
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state_crypto" {
  bucket = aws_s3_bucket.terraform_state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Create the DynamoDB table for state locking
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "terraform-state-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}