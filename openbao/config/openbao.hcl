# OpenBao Server Configuration - Local Shamir Seal Profile
ui = true

storage "raft" {
  path    = "/openbao/data"
  node_id = "overseer-openbao-1"
}

# TCP 리스너 설정
listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable   = 1

  # Caddy(고정 IP) 뒤에서 실제 클라이언트 공인 IP로 AppRole CIDR을 검사한다(Spec #511 후속).
  # 허용된 프록시의 X-Forwarded-For만 믿고, 그 밖의 주소가 헤더를 보내면 거부한다. 헤더 없는 직접 접속(러너)은 컨테이너 IP로 본다.
  x_forwarded_for_authorized_addrs      = "172.22.10.2/32"
  x_forwarded_for_reject_not_authorized = true
  x_forwarded_for_reject_not_present    = false
}

# API 및 클러스터 주소
api_addr     = "http://127.0.0.1:8200"
cluster_addr = "http://127.0.0.1:8201"

default_lease_ttl = "168h"
max_lease_ttl     = "720h"
