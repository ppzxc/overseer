# Boundary Worker Configuration for Overseer Control Plane

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
  type        = "proxy"
  tls_disable = true
}

# Worker Auth KMS (Controller와 동일한 키 사용)
kms "aead" {
  purpose   = "worker-auth"
  aead_type = "aes-gcm"
  key       = "8pv7uU8g58aN8y1n8PqR8G3z7rW+V8eY9nQ2x3Z1v4U="
  key_id    = "global_worker_auth"
}
