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
  key       = "l74Pm6L+aNN3tDQTfiv7K0FAdVP+VBsQGBxsdMMfI9Q="
  key_id    = "global_root"
}

kms "aead" {
  purpose   = "worker-auth"
  aead_type = "aes-gcm"
  key       = "JuC3bK4TqlJMaoq7U8/+wh4hRswogVF1ORq5LrbtKZA="
  key_id    = "global_worker_auth"
}

kms "aead" {
  purpose   = "recovery"
  aead_type = "aes-gcm"
  key       = "wnma1r8ID7ZJVDq8piSvugKxytQMABMIQDyJWUbc9p8="
  key_id    = "global_recovery"
}
