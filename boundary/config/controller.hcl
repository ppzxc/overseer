# Boundary Controller Configuration - Local AEAD KMS Profile
disable_mlock = true

controller {
  name                = "overseer-controller"
  description         = "Overseer Main Boundary Controller (Local AEAD KMS)"
  public_cluster_addr = "boundary-controller:9201"
  database {
    url = "env://BOUNDARY_POSTGRES_URL"
  }
}

# API Listener (포트 9200)
listener "tcp" {
  address     = "0.0.0.0:9200"
  purpose     = "api"
  tls_disable = true
  cors {
    enabled = true
    allowed_origins = ["*"]
  }
}

# Cluster Listener (포트 9201)
listener "tcp" {
  address     = "0.0.0.0:9201"
  purpose     = "cluster"
  tls_disable = true
}

# KMS AEAD Keys (Loaded via Controller environment)
kms "aead" {
  purpose   = "root"
  aead_type = "aes-gcm"
  key       = "3/yHcWb61ogL58oxRWERZVU34G2ENC+gGV/2+/JxQTA="
  key_id    = "global_root"
}

kms "aead" {
  purpose   = "worker-auth"
  aead_type = "aes-gcm"
  key       = "qZoepE9MFeu5dlx5ZTT+QLw87MYeWm0x2m89/PgxQuE="
  key_id    = "global_worker_auth"
}

kms "aead" {
  purpose   = "recovery"
  aead_type = "aes-gcm"
  key       = "+WIJ10GhCDAH8dfHeHewnLF8pVhX49mP1KQRNW4THbE="
  key_id    = "global_recovery"
}
