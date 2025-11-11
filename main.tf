terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "= 5.40.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

provider "oci" {
  config_file_profile = "DEFAULT"
  user_ocid           = var.user_ocid
  fingerprint         = var.fingerprint
  private_key_path    = var.private_key_path
  tenancy_ocid        = var.tenancy_ocid
  region              = var.region
}

# ============================================================================
# NETWORKING CONFIGURATION
# ============================================================================

# VCN (Virtual Cloud Network)
resource "oci_core_vcn" "vcn" {
  compartment_id = var.compartment_id
  cidr_block     = "10.0.0.0/16"
  display_name   = "main-vcn"
  dns_label      = "mainvcn"
}

# Internet Gateway for public subnet
resource "oci_core_internet_gateway" "internet_gateway" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "internet-gateway"
  enabled        = true
}

# NAT Gateway for private subnet
resource "oci_core_nat_gateway" "nat_gateway" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "nat-gateway"
  block_traffic  = false
}

# Service Gateway for OCI services access
data "oci_core_services" "all_services" {
  filter {
    name   = "name"
    values = ["All .* Services In Oracle Services Network"]
    regex  = true
  }
}

resource "oci_core_service_gateway" "service_gateway" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "service-gateway"

  services {
    service_id = data.oci_core_services.all_services.services[0].id
  }
}

# Route Table for public subnet
resource "oci_core_route_table" "public_route_table" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "public-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.internet_gateway.id
    description       = "Route to Internet Gateway"
  }
}

# Route Table for private subnet
resource "oci_core_route_table" "private_route_table" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "private-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.nat_gateway.id
    description       = "Route to NAT Gateway"
  }

  route_rules {
    destination       = data.oci_core_services.all_services.services[0].cidr_block
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.service_gateway.id
    description       = "Route to Service Gateway"
  }
}

# ============================================================================
# SECURITY LISTS
# ============================================================================

# Security List for public subnet (Bastion)
resource "oci_core_security_list" "public_security_list" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "public-security-list"

  # Allow SSH from Internet
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false

    tcp_options {
      min = 22
      max = 22
    }

    description = "Allow SSH from Internet"
  }

  # Allow ICMP for diagnostics
  ingress_security_rules {
    protocol    = "1" # ICMP
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false

    icmp_options {
      type = 3
      code = 4
    }

    description = "Allow ICMP Path MTU Discovery"
  }

  # Allow all outbound traffic
  egress_security_rules {
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    protocol         = "all"
    stateless        = false

    description = "Allow all outbound traffic"
  }
}

# Security List for private subnet (Databases)
resource "oci_core_security_list" "private_security_list" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "private-security-list"

  # Allow SSH only from public subnet (bastion)
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "10.0.1.0/24" # Public subnet CIDR
    source_type = "CIDR_BLOCK"
    stateless   = false

    tcp_options {
      min = 22
      max = 22
    }

    description = "Allow SSH from bastion subnet"
  }

  # Allow PostgreSQL (5432) from public subnet
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "10.0.1.0/24"
    source_type = "CIDR_BLOCK"
    stateless   = false

    tcp_options {
      min = 5432
      max = 5432
    }

    description = "Allow PostgreSQL from bastion subnet"
  }

  # Allow traffic from VCN
  ingress_security_rules {
    protocol    = "all"
    source      = "10.0.0.0/16"
    source_type = "CIDR_BLOCK"
    stateless   = false

    description = "Allow all traffic from VCN"
  }

  # Allow all outbound traffic
  egress_security_rules {
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    protocol         = "all"
    stateless        = false

    description = "Allow all outbound traffic"
  }
}

# ============================================================================
# SUBNETS
# ============================================================================

# Public subnet for Bastion
resource "oci_core_subnet" "public_subnet" {
  compartment_id             = var.compartment_id
  vcn_id                     = oci_core_vcn.vcn.id
  cidr_block                 = "10.0.1.0/24"
  display_name               = "public-subnet"
  dns_label                  = "public"
  prohibit_public_ip_on_vnic = false
  route_table_id             = oci_core_route_table.public_route_table.id
  security_list_ids          = [oci_core_security_list.public_security_list.id]
}

# Private subnet for Databases (PostgreSQL, etc.)
resource "oci_core_subnet" "private_subnet" {
  compartment_id             = var.compartment_id
  vcn_id                     = oci_core_vcn.vcn.id
  cidr_block                 = "10.0.2.0/24"
  display_name               = "private-subnet"
  dns_label                  = "private"
  prohibit_public_ip_on_vnic = true
  prohibit_internet_ingress  = true
  route_table_id             = oci_core_route_table.private_route_table.id
  security_list_ids          = [oci_core_security_list.private_security_list.id]
}

# ============================================================================
# NETWORK SECURITY GROUPS
# ============================================================================

# Network Security Group for Autonomous Database
resource "oci_core_network_security_group" "adb_nsg" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "adb-nsg"
}

# Allow ingress from VCN to ADB on port 1522 (Oracle Database with mTLS)
resource "oci_core_network_security_group_security_rule" "adb_ingress_from_vcn" {
  network_security_group_id = oci_core_network_security_group.adb_nsg.id
  direction                 = "INGRESS"
  protocol                  = "6" # TCP
  source                    = "10.0.0.0/16"
  source_type               = "CIDR_BLOCK"
  stateless                 = false

  tcp_options {
    destination_port_range {
      min = 1522
      max = 1522
    }
  }

  description = "Allow Oracle Database mTLS connections from VCN"
}

# Allow egress to anywhere (for ADB to communicate back)
resource "oci_core_network_security_group_security_rule" "adb_egress_all" {
  network_security_group_id = oci_core_network_security_group.adb_nsg.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  stateless                 = false

  description = "Allow all outbound traffic"
}

# ============================================================================
# SSH KEYS
# ============================================================================

resource "tls_private_key" "ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "local_file" "private_key" {
  content         = tls_private_key.ssh_key.private_key_pem
  filename        = "${path.module}/ssh-keys/private.pem"
  file_permission = "0600"
}

resource "local_file" "public_key" {
  content         = tls_private_key.ssh_key.public_key_openssh
  filename        = "${path.module}/ssh-keys/public.pub"
  file_permission = "0644"
}

# ============================================================================
# AVAILABILITY DOMAINS & IMAGES
# ============================================================================

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_id
}

data "oci_core_images" "oracle_linux_images" {
  compartment_id           = var.compartment_id
  operating_system         = "Oracle Linux"
  operating_system_version = "8"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
  state                    = "AVAILABLE"
}

# ============================================================================
# BASTION HOST
# ============================================================================

resource "oci_core_instance" "bastion" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_id
  display_name        = "bastion-host"
  shape               = "VM.Standard.A1.Flex"

  create_vnic_details {
    subnet_id        = oci_core_subnet.public_subnet.id
    assign_public_ip = true
    display_name     = "bastion-vnic"
  }

  shape_config {
    ocpus         = 1
    memory_in_gbs = 6
  }

  metadata = {
    ssh_authorized_keys = tls_private_key.ssh_key.public_key_openssh
    user_data = base64encode(<<-EOF
      #!/bin/bash

      exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
      echo "Starting bastion configuration..."

      # Update system and install basic tools
      sudo yum update -y
      sudo yum install -y curl wget git

      # Install PostgreSQL client
      sudo yum install -y postgresql

      # Enable port forwarding for SSH tunnels
      sudo sed -i 's/#AllowTcpForwarding yes/AllowTcpForwarding yes/' /etc/ssh/sshd_config
      sudo sed -i 's/#GatewayPorts no/GatewayPorts yes/' /etc/ssh/sshd_config
      sudo systemctl restart sshd

      # Install Tailscale
      echo "Installing Tailscale..."
      curl -fsSL https://tailscale.com/install.sh | sh

      sudo systemctl enable tailscaled
      sudo systemctl start tailscaled

      echo "Configuring Tailscale with auth key..."
      sudo tailscale up --authkey="${var.tailscale_auth_key}" --accept-routes --accept-dns

      sleep 5
      echo "Tailscale status:"
      sudo tailscale status

      # Install Docker
      echo "Installing Docker..."
      sudo yum install -y yum-utils device-mapper-persistent-data lvm2

      sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
      sudo yum install -y docker-ce docker-ce-cli containerd.io

      sudo systemctl enable docker
      sudo systemctl start docker
      sudo usermod -aG docker opc

      echo "Bastion host configured successfully"
      echo "Installed services:"
      echo "- PostgreSQL client: $(psql --version)"
      echo "- Docker: $(docker --version)"
      echo "- Tailscale: $(sudo tailscale version)"
      echo ""
      echo "Tailscale connection established:"
      sudo tailscale status
      EOF
    )
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.oracle_linux_images.images[0].id
    boot_volume_size_in_gbs = 50
  }

  preserve_boot_volume = false

  # Prevent unnecessary updates that cause errors with kms_key_id
  lifecycle {
    ignore_changes = [
      source_details
    ]
  }
}

# ============================================================================
# POSTGRESQL DATABASE SYSTEM
# ============================================================================

# Generate random password for PostgreSQL
resource "random_password" "postgresql_admin_password" {
  length  = 16
  special = true
  # PostgreSQL password requirements
  min_upper   = 2
  min_lower   = 2
  min_numeric = 2
  min_special = 2
  # Avoid problematic characters in shell
  override_special = "@#-_"

  # Force regeneration by adding keepers
  keepers = {
    version = "2"  # Change this to regenerate password
  }
}

resource "oci_psql_db_system" "postgresql" {
  compartment_id = var.compartment_id
  display_name   = var.postgresql_db_name
  db_version     = var.postgresql_version

  # Shape configuration
  shape          = var.postgresql_shape
  instance_count = var.postgresql_instance_count

  # Storage configuration
  storage_details {
    is_regionally_durable = true
    system_type           = "OCI_OPTIMIZED_STORAGE"
  }

  # Network configuration - MUST be private subnet
  network_details {
    subnet_id = oci_core_subnet.private_subnet.id
  }

  # Administrator credentials
  credentials {
    username = var.postgresql_admin_username
    password_details {
      password_type = "PLAIN_TEXT"
      password      = random_password.postgresql_admin_password.result
    }
  }

  # Backup configuration
  management_policy {
    backup_policy {
      retention_days   = var.postgresql_backup_retention_days
      kind             = "WEEKLY"
      days_of_the_week = ["SUNDAY"]  # Required field for WEEKLY backups
      backup_start     = "02:00"     # Backup start time in HH:MM format (UTC)
    }
  }
}

# Data source to get PostgreSQL DB System details after creation
data "oci_psql_db_system" "postgresql_details" {
  db_system_id = oci_psql_db_system.postgresql.id

  depends_on = [oci_psql_db_system.postgresql]
}

# ============================================================================
# AUTONOMOUS DATABASE 23AI (WITH PRIVATE ENDPOINT)
# ============================================================================

# Generate random password for Autonomous Database
resource "random_password" "adb_admin_password" {
  length  = 20
  special = true
  # ADB password requirements: 12-30 chars, upper, lower, number, special
  min_upper   = 2
  min_lower   = 2
  min_numeric = 2
  min_special = 2
  # Avoid characters that may cause problems
  override_special = "_#-"
}

resource "oci_database_autonomous_database" "vector_db" {
  compartment_id = var.compartment_id
  display_name   = var.adb_display_name
  db_name        = var.adb_db_name

  # Basic configuration
  db_version              = "23ai"  # Oracle Database 23ai with AI Vector Search
  db_workload             = "OLTP"  # or "DW" for data warehouse
  license_model           = "LICENSE_INCLUDED"
  is_free_tier            = var.adb_is_free_tier
  admin_password          = random_password.adb_admin_password.result
  cpu_core_count          = var.adb_is_free_tier ? 0 : var.adb_cpu_core_count  # Always Free tier must use 0
  data_storage_size_in_tbs = var.adb_storage_size_in_tbs

  # Auto scaling - Disabled for Always Free tier
  is_auto_scaling_enabled              = var.adb_is_free_tier ? false : true
  is_auto_scaling_for_storage_enabled  = var.adb_is_free_tier ? false : true

  # Security configuration for 23ai
  # NOTE: Private endpoint not available (requires tenancy feature enablement)
  # Using mTLS for maximum security - requires wallet for all connections
  # This is still very secure: end-to-end encrypted, certificate-based auth
  # subnet_id = oci_core_subnet.private_subnet.id  # Not supported without feature flag
  # nsg_ids   = [oci_core_network_security_group.adb_nsg.id]

  # Mutual TLS is REQUIRED - provides strong encryption and authentication
  # You'll need to download the wallet to connect
  is_mtls_connection_required = true

  # Local Data Guard for high availability (optional)
  # is_local_data_guard_enabled = false

  # Tags
  freeform_tags = {
    "Environment" = var.environment
    "ManagedBy"   = "Terraform"
    "Service"     = "VectorDatabase"
  }
}

# Download and extract ADB wallet automatically
resource "null_resource" "download_adb_wallet" {
  depends_on = [oci_database_autonomous_database.vector_db]

  triggers = {
    adb_id = oci_database_autonomous_database.vector_db.id
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Create wallet directory
      mkdir -p .data/adb-wallet

      # Check if wallet already exists
      if [ -f .data/adb-wallet/tnsnames.ora ]; then
        echo "Wallet already exists in .data/adb-wallet/, skipping download"
        exit 0
      fi

      # Download wallet (will fail gracefully if OCI CLI not configured)
      if ! oci db autonomous-database generate-wallet \
        --autonomous-database-id ${oci_database_autonomous_database.vector_db.id} \
        --file .data/adb-wallet/wallet.zip \
        --password 'WalletPassword123#' 2>/dev/null; then
        echo "WARNING: Could not download wallet automatically. Please download manually:"
        echo "  oci db autonomous-database generate-wallet --autonomous-database-id ${oci_database_autonomous_database.vector_db.id} --file .data/adb-wallet/wallet.zip --password 'WalletPassword123#'"
        exit 0
      fi

      # Extract wallet
      cd .data/adb-wallet && unzip -o wallet.zip && rm wallet.zip

      echo "Wallet downloaded and extracted to .data/adb-wallet/"
    EOT
  }

  provisioner "local-exec" {
    when    = destroy
    command = "rm -rf .data/adb-wallet || true"
  }
}

# ============================================================================
# OBJECT STORAGE (S3-COMPATIBLE)
# ============================================================================

# Get Object Storage namespace
data "oci_objectstorage_namespace" "namespace" {
  compartment_id = var.compartment_id
}

# Customer Secret Key for S3-compatible access to Object Storage
resource "oci_identity_customer_secret_key" "s3_credentials" {
  user_id      = var.user_ocid
  display_name = "terraform-s3-access-${var.environment}"
}

# Private Object Storage bucket (access via bastion only)
resource "oci_objectstorage_bucket" "s3_compatible_bucket" {
  compartment_id = var.compartment_id
  namespace      = data.oci_objectstorage_namespace.namespace.namespace
  name           = var.object_storage_bucket_name

  # Storage tier
  storage_tier = "Standard" # or "Archive"

  # Public access control
  access_type = var.object_storage_public_access ? "ObjectRead" : "NoPublicAccess"

  # Versioning enabled
  versioning = "Enabled"

  # Auto-Tiering (optional, moves old objects to Archive automatically)
  auto_tiering = var.object_storage_auto_tiering ? "InfrequentAccess" : "Disabled"

  # Tags
  freeform_tags = {
    "Environment" = var.environment
    "ManagedBy"   = "Terraform"
    "Service"     = "ObjectStorage"
  }
}

# MLflow artifacts bucket (private, access via bastion only)
resource "oci_objectstorage_bucket" "mlflow_bucket" {
  compartment_id = var.compartment_id
  namespace      = data.oci_objectstorage_namespace.namespace.namespace
  name           = "mlflow"

  # Storage tier
  storage_tier = "Standard"

  # Private access only (no public access)
  access_type = "NoPublicAccess"

  # Versioning enabled
  versioning = "Enabled"

  # Auto-Tiering disabled (mlflow artifacts are frequently accessed)
  auto_tiering = "Disabled"

  # Tags
  freeform_tags = {
    "Environment" = var.environment
    "ManagedBy"   = "Terraform"
    "Service"     = "MLflow"
  }
}

# ============================================================================
# GENERATIVE AI CONFIGURATION
# ============================================================================

# NOTE: For on-demand models, IAM policies are NOT required if you already have
# valid OCI credentials (which you do, since Terraform works).
#
# IAM policies are only needed for:
# - Dedicated AI Clusters (hosting/fine-tuning)
# - RAG Agents with Knowledge Bases
# - Service-to-service integrations
#
# Uncomment the policy below only if you plan to use those features.

/*
resource "oci_identity_policy" "genai_policy" {
  compartment_id = var.tenancy_ocid
  name           = "genai-service-policy-${var.environment}"
  description    = "Policy to allow usage of OCI Generative AI service"

  statements = [
    # For dedicated clusters and custom models
    "Allow dynamic-group genai-dynamic-group to manage generative-ai-family in compartment id ${var.compartment_id}",

    # For RAG agents with Object Storage knowledge bases
    "Allow service generative-ai to read objectstorage-namespaces in compartment id ${var.compartment_id}",

    # For private endpoints (if needed)
    "Allow service generative-ai to use virtual-network-family in compartment id ${var.compartment_id}"
  ]

  freeform_tags = {
    "Environment" = var.environment
    "ManagedBy"   = "Terraform"
    "Service"     = "GenerativeAI"
  }
}
*/

# ============================================================================
# OUTPUTS
# ============================================================================

# Bastion Host
output "bastion_public_ip" {
  description = "Public IP of Bastion Host"
  value       = oci_core_instance.bastion.public_ip
}

output "bastion_ssh_command" {
  description = "SSH command to connect to Bastion"
  value       = "ssh -i ${local_file.private_key.filename} opc@${oci_core_instance.bastion.public_ip}"
}

# PostgreSQL Database Outputs
output "postgresql_id" {
  description = "PostgreSQL DB System OCID"
  value       = oci_psql_db_system.postgresql.id
}

output "postgresql_instances" {
  description = "PostgreSQL instances information"
  value       = data.oci_psql_db_system.postgresql_details.instances
  sensitive   = false
}

output "postgresql_connection_info" {
  description = "PostgreSQL connection information via Bastion"
  value = {
    db_system_id       = oci_psql_db_system.postgresql.id
    admin_username     = var.postgresql_admin_username
    database_name      = "postgres"
    bastion_ip         = oci_core_instance.bastion.public_ip
    ssh_key            = local_file.private_key.filename
    instructions       = "After deployment, run: terraform output postgresql_instances to get the private IP, then create SSH tunnel"
    tunnel_example     = "ssh -i ${local_file.private_key.filename} -L 5432:<POSTGRESQL_PRIVATE_IP>:5432 opc@${oci_core_instance.bastion.public_ip}"
    psql_command       = "psql -h localhost -p 5432 -U ${var.postgresql_admin_username} -d postgres"
  }
  sensitive = false
}

output "postgresql_admin_password" {
  description = "PostgreSQL administrator password"
  value       = random_password.postgresql_admin_password.result
  sensitive   = true
}

output "postgresql_private_ip" {
  description = "PostgreSQL primary instance private IP"
  value       = data.oci_psql_db_system.postgresql_details.network_details[0].primary_db_endpoint_private_ip
  sensitive   = false
}

# Autonomous Database
output "adb_connection_urls" {
  description = "Autonomous Database connection URLs"
  value       = oci_database_autonomous_database.vector_db.connection_urls
  sensitive   = false
}

output "adb_admin_password" {
  description = "Autonomous Database administrator password"
  value       = random_password.adb_admin_password.result
  sensitive   = true
}

output "adb_ocid" {
  description = "Autonomous Database OCID"
  value       = oci_database_autonomous_database.vector_db.id
}

output "adb_wallet_download_command" {
  description = "Command to download ADB wallet (already auto-downloaded to .data/adb-wallet/)"
  value       = "oci db autonomous-database generate-wallet --autonomous-database-id ${oci_database_autonomous_database.vector_db.id} --file wallet.zip --password 'WalletPassword123#'"
}

output "adb_wallet_location" {
  description = "Location of the extracted ADB wallet"
  value       = "${path.module}/.data/adb-wallet"
  depends_on  = [null_resource.download_adb_wallet]
}

# Object Storage
output "object_storage_namespace" {
  description = "Object Storage namespace"
  value       = data.oci_objectstorage_namespace.namespace.namespace
}

output "object_storage_bucket_name" {
  description = "Object Storage bucket name"
  value       = oci_objectstorage_bucket.s3_compatible_bucket.name
}

output "object_storage_bucket_url" {
  description = "Object Storage bucket URL"
  value       = "https://objectstorage.${var.region}.oraclecloud.com/n/${data.oci_objectstorage_namespace.namespace.namespace}/b/${oci_objectstorage_bucket.s3_compatible_bucket.name}/o/"
}

output "object_storage_s3_endpoint" {
  description = "S3-compatible endpoint"
  value       = "https://${data.oci_objectstorage_namespace.namespace.namespace}.compat.objectstorage.${var.region}.oraclecloud.com"
}

output "object_storage_public_access" {
  description = "Object Storage public access enabled"
  value       = var.object_storage_public_access
}

# S3-Compatible Credentials
output "s3_access_key_id" {
  description = "S3-compatible Access Key ID for Object Storage"
  value       = oci_identity_customer_secret_key.s3_credentials.id
  sensitive   = false
}

output "s3_secret_access_key" {
  description = "S3-compatible Secret Access Key for Object Storage (SAVE THIS - only shown once)"
  value       = oci_identity_customer_secret_key.s3_credentials.key
  sensitive   = true
}

output "s3_credentials_summary" {
  description = "Complete S3-compatible access information"
  value = <<-EOT

========================================
S3-COMPATIBLE ACCESS CREDENTIALS
========================================

ENDPOINT: https://${data.oci_objectstorage_namespace.namespace.namespace}.compat.objectstorage.${var.region}.oraclecloud.com
REGION: ${var.region}
ACCESS KEY ID: ${oci_identity_customer_secret_key.s3_credentials.id}
SECRET ACCESS KEY: Run 'terraform output s3_secret_access_key' to view (sensitive)

CONFIGURATION:
--------------

Environment Variables:
export AWS_ACCESS_KEY_ID="${oci_identity_customer_secret_key.s3_credentials.id}"
export AWS_SECRET_ACCESS_KEY="$(terraform output -raw s3_secret_access_key)"
export AWS_DEFAULT_REGION="${var.region}"

AWS CLI:
aws s3 ls s3://store/ --endpoint-url https://${data.oci_objectstorage_namespace.namespace.namespace}.compat.objectstorage.${var.region}.oraclecloud.com
aws s3 ls s3://mlflow/ --endpoint-url https://${data.oci_objectstorage_namespace.namespace.namespace}.compat.objectstorage.${var.region}.oraclecloud.com

Python (boto3):
import boto3
s3 = boto3.client('s3',
    endpoint_url='https://${data.oci_objectstorage_namespace.namespace.namespace}.compat.objectstorage.${var.region}.oraclecloud.com',
    aws_access_key_id='${oci_identity_customer_secret_key.s3_credentials.id}',
    aws_secret_access_key='<get from: terraform output s3_secret_access_key>',
    region_name='${var.region}'
)

MLflow Configuration:
export MLFLOW_S3_ENDPOINT_URL=https://${data.oci_objectstorage_namespace.namespace.namespace}.compat.objectstorage.${var.region}.oraclecloud.com
export AWS_ACCESS_KEY_ID="${oci_identity_customer_secret_key.s3_credentials.id}"
export AWS_SECRET_ACCESS_KEY="$(terraform output -raw s3_secret_access_key)"

BUCKETS:
--------
- store: s3://store/
- mlflow: s3://mlflow/

========================================
EOT
  sensitive = false
}

# MLflow bucket outputs
output "mlflow_bucket_name" {
  description = "MLflow artifacts bucket name"
  value       = oci_objectstorage_bucket.mlflow_bucket.name
}

output "mlflow_bucket_url" {
  description = "MLflow bucket URL"
  value       = "https://objectstorage.${var.region}.oraclecloud.com/n/${data.oci_objectstorage_namespace.namespace.namespace}/b/${oci_objectstorage_bucket.mlflow_bucket.name}/o/"
}

# SSH Keys
output "ssh_private_key_path" {
  description = "SSH private key path"
  value       = local_file.private_key.filename
}

# SSH Tunnel Command for All Services
output "ssh_tunnel_command" {
  description = "SSH tunnel command to expose all private services locally"
  value = <<-EOT
ssh -i ${local_file.private_key.filename} \
    -L 5432:${data.oci_psql_db_system.postgresql_details.network_details[0].primary_db_endpoint_private_ip}:5432 \
    -L 1522:adb.us-chicago-1.oraclecloud.com:1522 \
    -N opc@${oci_core_instance.bastion.public_ip}

After establishing the tunnel, you can connect to:

1. PostgreSQL (store database):
   psql -h localhost -p 5432 -U admin -d store
   Password: (run 'terraform output postgresql_admin_password')

2. PostgreSQL (mlflow database):
   psql -h localhost -p 5432 -U admin -d mlflow
   Password: (run 'terraform output postgresql_admin_password')

3. Autonomous Database 23ai:
   - Download wallet: ${oci_database_autonomous_database.vector_db.id}
   - Edit tnsnames.ora: Change 'adb.us-chicago-1.oraclecloud.com:1522' to 'localhost:1522'
   - Connect with SQL Developer or SQLcl using the modified wallet
   Password: (run 'terraform output adb_admin_password')

Note: Keep the SSH tunnel running in a separate terminal while working with the databases.
EOT
  sensitive = false
}

# General information
output "vcn_id" {
  description = "VCN OCID"
  value       = oci_core_vcn.vcn.id
}

output "public_subnet_id" {
  description = "Public subnet OCID"
  value       = oci_core_subnet.public_subnet.id
}

output "private_subnet_id" {
  description = "Private subnet OCID"
  value       = oci_core_subnet.private_subnet.id
}

output "deployment_summary" {
  description = "Deployment summary"
  value = <<-EOT

  ========================================
  DEPLOYMENT COMPLETED - PRIVATE CONFIGURATION
  ========================================

  BASTION HOST (TAILSCALE):
  - Public IP: ${oci_core_instance.bastion.public_ip}
  - SSH: ssh -i ${local_file.private_key.filename} opc@${oci_core_instance.bastion.public_ip}
  - Tailscale: Check status with 'sudo tailscale status' after SSH
  - Services: PostgreSQL client, Docker, Tailscale

  POSTGRESQL DATABASE (PRIVATE):
  - Version: PostgreSQL 14.17 OCI Optimized
  - Access: Via bastion only (private subnet)
  - Username: admin
  - Password: Run 'terraform output postgresql_admin_password'
  - Connection: See 'terraform output postgresql_connection_info'

  AUTONOMOUS DATABASE 23AI (PRIVATE WITH VECTOR SEARCH):
  - Database Name: ${var.adb_db_name}
  - Access: Via bastion only (private endpoint)
  - Admin User: ADMIN
  - Password: Run 'terraform output adb_admin_password'
  - Download Wallet: (See output 'adb_wallet_download_command')
  - Features: AI Vector Search, ML Notebooks, APEX

  OBJECT STORAGE (PRIVATE, S3-COMPATIBLE):
  - Bucket: ${oci_objectstorage_bucket.s3_compatible_bucket.name}
  - Access: Via bastion only (no public access)
  - Namespace: ${data.oci_objectstorage_namespace.namespace.namespace}
  - Use OCI CLI from bastion to access

  SECURITY NOTES:
  - All databases are in private subnet (no internet access)
  - Object Storage is private (no public read/write)
  - Access only through bastion with Tailscale VPN
  - SSL/TLS required for all database connections
  - mTLS required for Autonomous Database

  To view sensitive passwords:
  - terraform output postgresql_admin_password
  - terraform output adb_admin_password

  ========================================
  EOT
}

# Generative AI Outputs
output "genai_inference_endpoint" {
  description = "OCI Generative AI inference endpoint URL"
  value       = "https://inference.generativeai.${var.region}.oci.oraclecloud.com"
}

output "genai_compartment_id" {
  description = "Compartment ID for Generative AI service calls"
  value       = var.compartment_id
}

output "genai_model_id" {
  description = "Model ID for xAI Grok 4"
  value       = var.genai_model_id
}

output "genai_configuration_summary" {
  description = "Complete OCI Generative AI configuration for application use"
  value = <<-EOT

========================================
OCI GENERATIVE AI CONFIGURATION
========================================

ENDPOINT: https://inference.generativeai.${var.region}.oci.oraclecloud.com
COMPARTMENT ID: ${var.compartment_id}
MODEL: ${var.genai_model_id}
REGION: ${var.region}

ENVIRONMENT VARIABLES FOR .env:
---------------------------------
OCI_GENAI_ENDPOINT=https://inference.generativeai.${var.region}.oci.oraclecloud.com
OCI_GENAI_COMPARTMENT_ID=${var.compartment_id}
OCI_GENAI_MODEL_ID=${var.genai_model_id}

PYTHON CONFIGURATION (LangChain):
----------------------------------
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI
import oci

config = oci.config.from_file(profile_name="DEFAULT")

llm = ChatOCIGenAI(
    model_id="${var.genai_model_id}",
    service_endpoint="https://inference.generativeai.${var.region}.oci.oraclecloud.com",
    compartment_id="${var.compartment_id}",
    auth_type="API_KEY",
    auth_profile="DEFAULT",
    model_kwargs={
        "temperature": 0.7,
        "max_tokens": 2000,
    }
)

AUTHENTICATION:
---------------
Uses the same OCI config as Terraform (${var.private_key_path})
No additional API keys required

========================================
EOT
  sensitive = false
}
