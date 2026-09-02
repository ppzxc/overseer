# OpenBao Server Configuration - GCP Cloud KMS Auto-Unseal Profile
ui = true
disable_mlock = true

storage "raft" {
  path    = "/openbao/data"
  node_id = "overseer-openbao-1"
}

# TCP 리스너 설정
listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable   = 1
}

# API 및 클러스터 주소
api_addr     = "http://127.0.0.1:8200"
cluster_addr = "http://127.0.0.1:8201"

default_lease_ttl = "168h"
max_lease_ttl     = "720h"

# GCP Cloud KMS Auto-Unseal configuration
# Credentials will be read from GOOGLE_APPLICATION_CREDENTIALS or gcp metadata
seal "gcpckms" {
  project     = "${GCP_PROJECT}"
  region      = "${GCP_REGION}"
  key_ring    = "${GCP_KEY_RING}"
  crypto_key  = "${GCP_OPENBAO_KEY}"
}
