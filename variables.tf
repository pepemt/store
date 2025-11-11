# ============================================================================
# OCI AUTHENTICATION VARIABLES
# ============================================================================

variable "user_ocid" {
  description = "User OCID for Oracle Cloud Infrastructure"
  type        = string
}

variable "fingerprint" {
  description = "Public Key Fingerprint for Oracle Cloud Infrastructure"
  type        = string
}

variable "private_key_path" {
  description = "Path to the Private Key used for Oracle Cloud Infrastructure"
  type        = string
}

variable "tenancy_ocid" {
  description = "Tenancy OCID for Oracle Cloud Infrastructure"
  type        = string
}

variable "region" {
  description = "Region for Oracle Cloud Infrastructure"
  type        = string
}

variable "compartment_id" {
  description = "Compartment OCID for Oracle Cloud Infrastructure"
  type        = string
}

# ============================================================================
# GENERAL VARIABLES
# ============================================================================

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# ============================================================================
# POSTGRESQL DATABASE VARIABLES
# ============================================================================

variable "postgresql_db_name" {
  description = "Display name for PostgreSQL Database System"
  type        = string
  default     = "postgresql-db"
}

variable "postgresql_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "14"

  validation {
    condition     = contains(["14", "15", "16"], var.postgresql_version)
    error_message = "PostgreSQL version must be 14, 15, or 16."
  }
}

variable "postgresql_shape" {
  description = "Shape for PostgreSQL Database System"
  type        = string
  default     = "PostgreSQL.VM.Standard.E4.Flex.2.32GB"
}

variable "postgresql_instance_count" {
  description = "Number of PostgreSQL instances (1 primary + replicas)"
  type        = number
  default     = 1

  validation {
    condition     = var.postgresql_instance_count >= 1 && var.postgresql_instance_count <= 3
    error_message = "Instance count must be between 1 and 3."
  }
}

variable "postgresql_admin_username" {
  description = "Admin username for PostgreSQL"
  type        = string
  default     = "postgres"
}

variable "postgresql_backup_retention_days" {
  description = "Number of days to retain PostgreSQL backups"
  type        = number
  default     = 7

  validation {
    condition     = var.postgresql_backup_retention_days >= 1 && var.postgresql_backup_retention_days <= 35
    error_message = "Backup retention days must be between 1 and 35."
  }
}

# ============================================================================
# AUTONOMOUS DATABASE (23AI) VARIABLES
# ============================================================================

variable "adb_display_name" {
  description = "Display name for Autonomous Database"
  type        = string
  default     = "vector-search-db"
}

variable "adb_db_name" {
  description = "Database name for Autonomous Database (alphanumeric only, max 14 chars)"
  type        = string
  default     = "VECTORDB"

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9]{0,13}$", var.adb_db_name))
    error_message = "Database name must start with a letter, contain only alphanumeric characters, and be max 14 characters."
  }
}

variable "adb_is_free_tier" {
  description = "Whether to use Always Free tier for Autonomous Database"
  type        = bool
  default     = false
}

variable "adb_cpu_core_count" {
  description = "Number of OCPU cores for Autonomous Database"
  type        = number
  default     = 1

  validation {
    condition     = var.adb_cpu_core_count >= 1
    error_message = "CPU core count must be at least 1."
  }
}

variable "adb_storage_size_in_tbs" {
  description = "Storage size in terabytes for Autonomous Database"
  type        = number
  default     = 1

  validation {
    condition     = var.adb_storage_size_in_tbs >= 1
    error_message = "Storage size must be at least 1 TB."
  }
}

# NOTE: Access Control List (ACL) is NOT supported for Autonomous Database 23ai
# The database will be publicly accessible by default
# For production environments, consider using a private endpoint instead
# by configuring subnet_id and nsg_ids in the autonomous database resource

# ============================================================================
# OBJECT STORAGE VARIABLES
# ============================================================================

variable "object_storage_bucket_name" {
  description = "Name for Object Storage bucket"
  type        = string
  default     = "s3-compatible-storage"
}

variable "object_storage_public_access" {
  description = "Whether to allow public access to Object Storage bucket"
  type        = bool
  default     = true

  # NOTE: In production, consider setting this to false
  # and use pre-authenticated requests or Customer Secret Keys
}

variable "object_storage_auto_tiering" {
  description = "Enable auto-tiering to move infrequently accessed objects to lower-cost storage"
  type        = bool
  default     = false
}

# ============================================================================
# TAILSCALE CONFIGURATION
# ============================================================================

variable "tailscale_auth_key" {
  description = "Tailscale authentication key for bastion host"
  type        = string
  sensitive   = true
}

# ============================================================================
# GENERATIVE AI VARIABLES
# ============================================================================

variable "genai_model_id" {
  description = "Model ID for OCI Generative AI service"
  type        = string
  default     = "cohere.command-r-plus"

  validation {
    condition = contains([
      "cohere.command-r-plus",
      "cohere.command-r-16k",
      "cohere.command",
      "meta.llama-3.1-70b-instruct",
      "meta.llama-3.1-405b-instruct",
      "meta.llama-3.3-70b-instruct"
    ], var.genai_model_id)
    error_message = "Model ID must be a valid OCI Generative AI model supported by LangChain ChatOCIGenAI."
  }
}
