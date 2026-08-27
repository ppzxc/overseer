# OpenBao Server Configuration for Overseer Control Plane

ui = true
disable_mlock = true

storage "file" {
  path = "/openbao/data"
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
