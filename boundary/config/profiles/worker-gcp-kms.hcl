# Boundary Worker Configuration - GCP Cloud KMS Profile
disable_mlock = true

worker {
  name        = "overseer-worker"
  description = "Overseer IDC In-Cluster Boundary Worker (GCP Cloud KMS)"
  controllers = [
    "boundary-controller:9201"
  ]
  public_addr = "127.0.0.1:9202"
  tags {
    type = ["idc", "production"]
    env  = ["production"]
  }
}

# Proxy Listener (포트 9202)
listener "tcp" {
  address     = "0.0.0.0:9202"
  type        = "proxy"
  tls_disable = true
}

# Worker Auth KMS (GCP Cloud KMS)
kms "gcpckms" {
  purpose    = "worker-auth"
  project    = "${GCP_PROJECT}"
  region     = "${GCP_REGION}"
  key_ring   = "${GCP_KEY_RING}"
  crypto_key = "${GCP_BOUNDARY_WORKER_AUTH_KEY}"
  key_id     = "global_worker_auth"
}
