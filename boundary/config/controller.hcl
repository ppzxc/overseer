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

# KMS AEAD Keys (Lab / On-Premise Dev Default)
kms "aead" {
  purpose   = "root"
  aead_type = "aes-gcm"
  key       = "sP191WKGvgcuEmhdREQBPBG5nhAAda4e+bQQnFRinCU="
  key_id    = "global_root"
}

kms "aead" {
  purpose   = "worker-auth"
  aead_type = "aes-gcm"
  key       = "8pv7uU8g58aN8y1n8PqR8G3z7rW+V8eY9nQ2x3Z1v4U="
  key_id    = "global_worker_auth"
}

kms "aead" {
  purpose   = "recovery"
  aead_type = "aes-gcm"
  key       = "uK382WKGvgcuEmhdREQBPBG5nhAAda4e+bQQnFRinCU="
  key_id    = "global_recovery"
}
