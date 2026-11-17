# Warpgate (접근 통제 · 세션 기록 bastion)

SSH/MySQL/MariaDB/PostgreSQL 접속을 Warpgate 한 곳으로 모아 접근 통제와 세션 기록을 남긴다. 에이전트 설치 없이 개발자 PC의 일반 클라이언트를 그대로 쓴다. 비교·시험 결과는 `docs/poc/bastion-poc-summary.md` 참고.

## 배치 (ns0266 기존 구성에 맞춤)
| 항목 | 경로/값 |
|---|---|
| Compose | `/opt/services/warpgate/compose.yml` (project `app`, 네트워크 `backend`) |
| 환경 파일 | `/data/warpgate/config/.env` |
| 데이터(DB·녹화·TLS 키) | `/data/warpgate/data` |
| 웹 UI/API | 컨테이너 8888 → 호스트 `127.0.0.1:18888` (ns0266의 `127.0.0.1:8888`은 이미 사용 중이라 피함) |
| SSH·DB 프록시 | 호스트 `${WARPGATE_BIND_ADDR}`의 `2222`(SSH, 호스트 sshd는 22), `33306`(MySQL), `55432`(PostgreSQL). 주소 하나로 함께 열리므로 DB를 닫으려면 compose의 해당 포트 줄을 지운다 |

외부에서 웹 UI를 쓰려면 ingress-caddy(`/opt/services/caddy/runtime/Caddyfile`)에 `reverse_proxy https://warpgate:8888`(자체 서명 인증서면 `transport http { tls_insecure_skip_verify }`)를 추가한다. 이 모듈은 Caddy를 수정하지 않는다.

## 시작
```sh
cp .env.example /data/warpgate/config/.env   # WARPGATE_EXTERNAL_HOST, WARPGATE_ADMIN_PASSWORD, WARPGATE_BIND_ADDR 설정
docker compose --env-file /data/warpgate/config/.env up -d      # warpgate-init(최초 1회, 설정 있으면 skip) → warpgate
```
- `DATA_DIR/warpgate/data`가 비어 있으면 `unattended-setup`이 설정·자체 서명 TLS·SSH 호스트 키·admin을 만든다. 이미 있으면 건드리지 않는다.
- **`/data/warpgate/data`는 백업 대상이다** (SSH 호스트 키를 잃으면 모든 클라이언트가 호스트 키 경고를 받는다).
- 이미지는 `0.30.4`로 고정(`WARPGATE_VERSION`). 1.0 이전 버전이라 올릴 때는 PoC처럼 먼저 확인한다.

## 대상·역할·사용자 반영 (`scripts/sync-warpgate.py`)
```sh
cp targets.example.json targets.json    # 실제 값은 커밋하지 않는다
WARPGATE_ADMIN_PASSWORD=... WARPGATE_URL=https://127.0.0.1:18888 WARPGATE_INSECURE_TLS=true \
  WARPGATE_HOST_HEADER=<WARPGATE_EXTERNAL_HOST> scripts/sync-warpgate.py --dry-run
```
- 표준 라이브러리만 쓰는 멱등 스크립트다. `--dry-run`은 이미 있는 항목 기준의 계획만 보여 준다(새로 만들 항목의 연결은 표시되지 않음). 없는 대상·역할·사용자는 만들고, 달라진 옵션은 갱신하고, 설정에 있는 역할·대상 범위의 연결만 맞춘다. 대상·역할·사용자 자체는 삭제하지 않지만, **설정에 이름이 있는 역할의 연결은 설정에 없으면 해제한다**(수동으로 만든 연결도 해제됨). 먼저 `--dry-run`으로 확인한다. 공개키는 라벨 기준으로 추가만 하며, 키 교체·퇴사자 키 회수는 하지 않으므로 UI/API로 직접 지운다.
- 세션이 Host 헤더에 묶여 있어서 IP로 접속할 때는 `WARPGATE_HOST_HEADER`가 필요하다. FQDN으로 접속하면 필요 없다.
- 대상 비밀번호는 평문 대신 OpenBao 참조 `secret://백엔드/마운트/경로#필드`를 쓴다 (Warpgate에 시크릿 백엔드 `openbao`를 먼저 등록해야 한다. PoC에서 시험 OK). 이 스크립트는 시크릿 백엔드 등록을 하지 않는다.
- 개인 OS 계정과 1:1로 맞추려면 사람×서버마다 대상을 만든다(`ns0266--ppzxc` 형식). Warpgate는 대상 하나에 계정 하나다.
- Semaphore 작업으로 돌리는 것도 가능하다(GWS 인원 변동 → 이 스크립트). 아직 연결하지 않았다.

## 운영 시 확인할 것
- 녹화·일반 로그 기본 보관 7일(`log.retention`), 감사 로그 1년. ISMS 기준에 맞게 `warpgate.yaml`에서 조정한다.
- 로그인 보호: 같은 IP에서 5회 실패하면 30분 차단(정상 사용자도 막힘). 필요하면 `/parameters`로 조정한다.
- 녹화는 디스크에 평문으로 저장되고 변조 방지가 없다. 외부 전송(`log.send_to`)이나 별도 보관을 검토한다.
- DB 대상은 TLS `Required` 권장.
