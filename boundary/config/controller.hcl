# Boundary Controller Configuration for Overseer Control Plane

disable_mlock = true

controller {
  name        = "overseer-controller"
  description = "Overseer Main Boundary Controller"
  database {
    url = "postgresql://boundary:boundarypassword@postgres:5432/boundary?sslmode=disable"
  }
}

# API Listener (포트 9200)
listener "tcp" {
  address     = "0.0.0.0:9200"
  type        = "api"
  tls_disable = true
  cors {
    enabled = true
    allowed_origins = ["*"]
  }
}

# Cluster Listener (포트 9201)
listener "tcp" {
  address     = "0.0.0.0:9201"
  type        = "cluster"
  tls_disable = true
}

# KMS AEAD Keys (Loaded via Controller environment or fallbacks)
kms "aead" {
  purpose   = "root"
  aead_type = "aes-gcm"
  key       = "env://BOUNDARY_KMS_AEAD_ROOT_KEY"
  key_id    = "global_root"
}

kms "aead" {
  purpose   = "worker-auth"
  aead_type = "aes-gcm"
  key       = "env://BOUNDARY_KMS_AEAD_WORKER_AUTH_KEY"
  key_id    = "global_worker_auth"
}

kms "aead" {
  purpose   = "recovery"
  aead_type = "aes-gcm"
  key       = "env://BOUNDARY_KMS_AEAD_RECOVERY_KEY"
  key_id    = "global_recovery"
}
