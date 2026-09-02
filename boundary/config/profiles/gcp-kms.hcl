# Boundary Controller Configuration - GCP Cloud KMS Profile
disable_mlock = true

controller {
  name        = "overseer-controller"
  description = "Overseer Main Boundary Controller (GCP Cloud KMS)"
  database {
    url = "env://BOUNDARY_POSTGRES_URL"
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

# GCP Cloud KMS Integration
kms "gcpckms" {
  purpose    = "root"
  project    = "${GCP_PROJECT}"
  region     = "${GCP_REGION}"
  key_ring   = "${GCP_KEY_RING}"
  crypto_key = "${GCP_BOUNDARY_ROOT_KEY}"
  key_id     = "global_root"
}

kms "gcpckms" {
  purpose    = "worker-auth"
  project    = "${GCP_PROJECT}"
  region     = "${GCP_REGION}"
  key_ring   = "${GCP_KEY_RING}"
  crypto_key = "${GCP_BOUNDARY_WORKER_AUTH_KEY}"
  key_id     = "global_worker_auth"
}

kms "gcpckms" {
  purpose    = "recovery"
  project    = "${GCP_PROJECT}"
  region     = "${GCP_REGION}"
  key_ring   = "${GCP_KEY_RING}"
  crypto_key = "${GCP_BOUNDARY_RECOVERY_KEY}"
  key_id     = "global_recovery"
}
