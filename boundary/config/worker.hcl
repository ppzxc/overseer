# Boundary Worker Configuration - Local AEAD KMS Profile
disable_mlock = true

worker {
  name        = "overseer-worker"
  description = "Overseer IDC In-Cluster Boundary Worker"
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
  purpose     = "proxy"
  tls_disable = true
}

# Worker Auth KMS (Controller와 동일한 키 사용)
kms "aead" {
  purpose   = "worker-auth"
  aead_type = "aes-gcm"
  key       = "qZoepE9MFeu5dlx5ZTT+QLw87MYeWm0x2m89/PgxQuE="
  key_id    = "global_worker_auth"
}
