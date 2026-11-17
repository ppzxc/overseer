# 접근제어 솔루션 로컬 PoC 요약 (Teleport / Warpgate / JumpServer)

작성일 2026-11-17. 로컬 Docker(`tp-poc` 네트워크)에서 시험했고 운영 서버에는 영향이 없다.
상세 결과와 재현 스크립트는 저장소 밖 `/home/ppzxc/projects/teleport-poc/` 아래에 있다 (`RESULTS.md`, `warpgate/RESULTS-warpgate.md`, `jumpserver/RESULTS-jumpserver.md`).

## 1. 비교

표기: **시험 OK**=로컬 PoC에서 직접 확인, **문서확인**=공식 문서/소스로만 확인(실제 동작 미시험), **미시험**=확인 못 함, **결론 없음**=시험했으나 판단 불가.

| 항목 | Teleport Community 18.11 | Warpgate 0.30.4 | JumpServer CE 5.1.1 |
|---|---|---|---|
| 라이선스 | 직원 100명 미만, 매출 1천만 달러 미만 조건부 | Apache-2.0 | GPLv3 |
| 성숙도 | 높음 | 1.0 이전 | 높음 |
| Google SSO | 불가 (Enterprise) | 문서확인 (google OIDC 제공자, 실연동 미시험) | 문서확인 (코드상 백엔드 존재) |
| CentOS 6 SSH | 시험 OK: 불가 | 시험 OK: 가능 | 시험 OK: 가능 |
| CentOS 7, Rocky 8/9/10 SSH | 시험 OK: 가능 | 시험 OK: 가능 | 시험 OK: 가능 |
| PostgreSQL 16 | 시험 OK: 가능 | 시험 OK: 가능 | 시험 OK: 불가 (scram, md5로 바꾸면 가능) |
| MySQL 8.4 | 시험 OK: 가능 | 시험 OK: 가능 | 시험 OK: 비공식 구버전 magnus로만 |
| MariaDB 5.5 | 시험 OK: 불가 (TLS) | 시험 OK: 가능 | 시험 OK: 비공식 구버전 magnus로만 |
| MariaDB 10.11, 13 | 시험 OK: 가능 | 시험 OK: 가능 | 시험 OK: 비공식 구버전 magnus로만 |
| 개발자 PC 설치 | `tsh` 필요 (시험 OK) | 불필요 (시험 OK) | SSH 불필요, DB는 CE에서 웹 클라이언트 중심 |
| GUI 클라이언트 | 문서확인: DB는 `tsh proxy db --tunnel` 후 연결, MySQL Workbench 절차 있음 | 문서확인: 표준 프로토콜, MySQL은 TLS와 cleartext 허용 필요 | 문서확인: JumpServer Client가 Xshell, SecureCRT, PuTTY, DBeaver 실행 |
| SQL 원문 기록 | 시험 OK: PG, MySQL, MariaDB 10.11+ | 시험 OK: PG, MySQL, MariaDB | 시험 OK: 있음 (웹, 구버전 magnus) |
| SSH 녹화, 명령 기록 | 시험 OK | 시험 OK (키 입력 마스킹 없음) | 시험 OK (녹화 파일은 일부 세션 결론 없음) |
| 접근 제어 (허용, 거부) | 시험 OK | 시험 OK | 시험 OK |
| 명령 필터 | 미시험 (Community는 감사용 BPF 기록만 알려짐) | 미시험 | 시험 OK (`rm -rf`, `drop table` 차단) |
| SCP/SFTP 차단 | 시험 OK (`ssh_file_copy: false`) | 미시험 | 문서확인 (소스: 연결 방식 ACL로 `sftp_client` 비활성화) |
| 동시 세션 제한 | 시험 OK: Enterprise 전용 (`max_sessions` 에러) | 문서확인 (웹 클라이언트의 사용자당 세션 제한만 확인, SSH는 미확인) | 미시험 |
| 접근 승인 | 문서확인: Enterprise (Community는 CLI 미리보기) | 시험 OK | 시험 못 함 |
| 로그인 보호 (IP 차단) | 미시험 | 시험 OK (5회, 30분) | 미시험 |
| 사용자 계정 잠금 | 문서확인 (로컬 계정, 30분 창 내 반복 실패 시 30분 잠금) | 시험 OK (10회, 1시간) | 미시험 |
| MFA | 문서확인 (로컬 계정 MFA, 세션 MFA) | 시험 OK (TOTP, 허용 IP) | 문서확인 (MFA 설정, 강제 옵션) |
| OpenBao 시크릿 연동 | 해당 없음 | 시험 OK (`secret://` 참조) | 미시험 |
| OS 계정 자동 생성 | 시험 OK (에이전트 서버만) | 없음 (공용 계정 중계) | 시험 OK (계정 푸시, 격리 설정 해제 필요) |
| OS 계정 삭제 동기화 | 없음 (`keep`은 남김) | 없음 | 결론 없음 |
| 서버 로그의 개인 식별 | 개인별 인증서로 가능 | 공용 계정이라 불가 | 공용 계정이라 불가 |
| 세션 강제종료 | 문서확인 (`tctl lock`이 기존 연결 종료) | 문서확인 (`POST /sessions/:id/close`, `DELETE /sessions`) | 결론 없음 (API 200, 실제로는 안 끊김) |
| 기록 보관 기본값 | 문서확인 (감사 1년, 변경 가능, 녹화 삭제는 미확인) | 문서확인 (감사 1년, 녹화 7일, 설정 변경) | 미확인 |
| 로그 외부 전송 | 문서확인 (Event Handler 플러그인→Fluentd, Community 가능 여부 미확인) | 문서확인 (`log.send_to` 소켓) | 미시험 |
| 로그 위변조 방지 | 미확인 | 기능 못 찾음 | 미확인 |
| 비밀번호 자동 변경 | 해당 없음 | 없음 | 시험 OK: EE 전용 (403) |
| 보안 주의 | 없음 | 없음 | 공식 compose가 `docker.sock` 마운트, privileged |

## 2. OS 사용자 동기화와 계정 연동

PoC에서 직접 시험하지 않은 항목이 많다. 아래는 시험 결과와 문서/소스 확인을 구분해서 적는다.

| 제품 | 개발자 신원 | 대상 서버의 OS 계정 | 동기화 |
|---|---|---|---|
| Teleport | 로컬 계정 또는 GitHub (Community) | 개발자별 OS 계정은 서버에 미리 있어야 함. 에이전트의 host user creation 기능으로 접속 시 자동 생성하는 방법이 문서에 있으나 이 PoC에서는 미시험. CentOS 6, 에이전트리스 노드는 에이전트가 없어 해당 없음 | 서버 쪽 계정 동기화는 없음. 짧은 수명의 인증서로 접속하므로 서버에 개인키를 둘 필요는 없음 |
| Warpgate | 로컬, OTP, SSO (google 등) | 대상마다 Warpgate가 저장한 하나의 계정(PoC에서는 root)으로 접속. 개발자별 OS 계정과 연결되지 않음 | OS 계정 동기화 기능 없음. 접속 기록은 Warpgate 사용자 기준으로만 남고 서버 쪽 로그에는 공용 계정으로 보임 |
| JumpServer | 로컬, LDAP, OIDC, SAML 등 | 자산별 계정(account)을 등록해 연결. 계정 푸시/자동 변경 기능은 있으나 비밀번호 자동 변경은 CE에서 403 확인(EE 전용). 푸시 기능의 CE 동작은 미시험 | 계정 자동 변경은 EE 필요 |

### 의미
- 세 제품 모두 "IdP의 사용자를 서버 OS 계정으로 자동 동기화"하는 기능을 이 PoC에서 확인하지 못했다.
- Warpgate와 JumpServer는 공용 계정(root 등)을 대상에 저장해 두고 중계하는 방식이라, 서버 로그만으로는 개인을 구분할 수 없다. 개인 식별은 접근제어 솔루션의 감사 로그에 의존한다. ISMS 심사에서 계정 공유 지적 가능성이 있어 심사 기준 확인이 필요하다.
- OS 계정 관리는 기존 방식(Ansible `node-provisioner` 등)으로 계속 관리하고 접근제어 솔루션에서는 사용자와 대상의 매핑만 맡기는 구성이 현실적이다. 이 부분은 결정이 필요하다.

### 문서·소스로 추가 확인한 것 (2026-11-17, 실제 시험은 아님)
- Teleport: 역할의 `create_host_user_mode: keep`(또는 `insecure-drop`)과 `host_groups`, `host_sudoers`로 접속 시 OS 계정을 자동 생성한다. 문서에서 Enterprise 전용으로 표시된 옵션(`max_connections`, `pin_source_ip` 등)에는 포함되지 않았다. 다만 Teleport SSH Service(에이전트)가 만드는 방식이라 CentOS 6과 에이전트리스 OpenSSH 노드에는 적용되지 않는다. 사용자 삭제는 동기화되지 않는다(`keep`은 계정을 남기고, `insecure-drop`은 UID 재사용 위험이 문서에 경고됨).
- JumpServer: 소스에 계정 푸시(`PushAccountManager`)가 있다. 특권 계정(privileged)으로 로그인해 Ansible으로 대상 서버에 계정을 만들거나 비밀번호를 설정한다. 푸시가 CE에서 라이선스 검사에 걸리는지는 확인하지 못했다(비밀번호 자동 변경은 CE에서 403이었음).

### Teleport host user creation 실제 시험 (Community 18.11.10, CentOS 7 / Rocky 8, 9, 10 에이전트)
역할 `auto-users`(`create_host_user_mode: keep`, `host_groups`, `host_sudoers`, 로그인 `devx`)로 서버에 없던 OS 계정을 접속 시 자동 생성했다. Community에서 동작한다. 재현 파일은 `teleport-poc/conf/role-auto-users.yaml`이다.

- **4개 OS 모두 성공**: 계정 `devx` 생성, 그룹 `devgrp` 추가, `/etc/sudoers.d` 항목 작성(`sudo -n /usr/bin/id` 성공). 그룹 `teleport-keep`도 자동으로 붙는다.
- **함정 1, 에이전트 재시작 필요**: 노드에 `useradd`와 `visudo`(sudo 패키지)가 에이전트 시작 시점에 있어야 한다. 이미지에 sudo가 없었을 때는 에러 없이 `unknown user`로만 실패했고, sudo 설치 후 **에이전트를 재시작**해야 동작했다.
- **함정 2, 역할 결합은 AND**: 사용자의 역할 중 하나라도 `create_host_user_mode`를 지정하지 않으면(예: 기본 `access` 역할) 계정과 sudoers가 만들어지지 않았다(이미 있는 계정으로만 접속, sudo는 비밀번호 요구). 자동 생성을 쓰려면 사용자에게 붙는 모든 역할이 이 옵션을 지정해야 한다. 이 PoC에서는 `auto-users` 단독 역할 사용자(`poc2`)로 성공했다.
- 계정 삭제는 동기화되지 않는다(`keep`은 남김). 퇴사자 계정 정리는 별도 절차가 필요하다.
- CentOS 6과 에이전트리스 OpenSSH 노드에는 적용되지 않는다.

### JumpServer 계정 푸시 실제 시험 (CE v5.1.1, Rocky 9)
Community에서 동작한다. 특권 계정(root)으로 로그인해 서버에 없던 `pocuser`를 만들고 비밀번호를 설정했고, 해당 비밀번호로 SSH 로그인까지 확인했다(`Account push successful, new credentials verified`).
- API: `POST /accounts/push-account-automations/`(자산, 계정명, 비밀번호 지정, `is_periodic:false` 필수), 실행은 `POST /accounts/push-account-executions/`. 주기 실행도 설정 가능.
- 함정 1: 기본 설정은 Ansible 실행을 `jumpserver/ansible-executor` 이미지로 격리하는데 이미지를 받지 못해 실패했다. 이 PoC에서는 환경변수 `ANSIBLE_DOCKER_ENABLED=false`로 core, celery를 재생성해 해결했다(격리 해제 보안 영향은 검토 필요).
- 함정 2: 대상에 sudo가 없으면 `/etc/sudoers does not exist`로 실패한다(계정은 만들어진 뒤).
- 푸시는 계정 생성과 비밀번호 설정이다. 삭제 동기화는 확인하지 못했다. 비밀번호 자동 변경은 CE 403(EE 전용)이다.

### 아직 확인이 필요한 것
- JumpServer 푸시로 만든 계정의 삭제/비활성 동기화, 사용자별 계정 매핑
- Warpgate OpenBao 연동의 운영 환경 검증(네임스페이스 `infra/prod/host`, SSH 인증서 서명). 로컬 dev 모드 OpenBao에서는 시험 OK
- 운영 DB 종류와 버전 (MariaDB 5.x, Oracle 등 포함 여부)

## 3. ISMS 관점 (초안, 통제 번호와 법령 내용은 원문 확인 필요)

| 쟁점 | Teleport | Warpgate | JumpServer |
|---|---|---|---|
| 레거시(CentOS 6, MariaDB 5.5) 통제 | 통제 불가 | 통제 가능 | SSH 가능, DB는 EE 또는 비공식 |
| 접속 기록 보관 | 설정 미시험 | 감사 1년, 녹화 기본 7일 (늘려야 함) | 미확인 |
| 개인 식별 | 개인별 인증서 | 공용 계정 중계 | 공용 계정 중계 |
| 위변조 방지, 정기 검토 증적 | 미확인 | 미확인 | 미확인 |

## 4. 잠정 판단
- 레거시 서버(CentOS 6)와 GWS SSO가 요구사항이면 Warpgate가 맞다. 단점은 1.0 이전 버전과 공용 계정 중계다.
- Teleport는 현대 OS와 DB만 대상으로 하면 기능이 가장 풍부하지만 GWS SSO는 Enterprise 계약이 필요하다.
- JumpServer는 DB 네이티브 접속과 비밀번호 자동 변경이 EE 전용이라 CE만으로는 요구를 채우기 어렵다. 공식 compose는 `docker.sock` 마운트와 privileged 컨테이너를 쓴다.

## 5. 미검증
GUI DB 클라이언트(DBeaver 등), SSO와 MFA 실연동, 승인 워크플로, HA, 로그 위변조 방지, 세션 강제종료, 공식 가격표.

## 6. 임직원 변동 자동 동기화 (GWS → Semaphore) 검토 — 문서 조사, 미시험

요구: 임직원 변동 시 Semaphore로 웹훅 한 번 보내 OS 계정 등 필요한 리소스를 자동 동기화.

- GWS 관리 콘솔에는 "변동 시 지정 URL 호출" 설정이 없다. API 푸시 알림만 있다.
  - Directory API `users.watch`: 사용자 변경 알림. 확인한 이벤트는 `add`뿐이고 `update`/`delete`는 미확인 ([문서](https://developers.google.com/workspace/admin/directory/v1/guides/push)).
  - Reports API `activities.watch`: 관리자 활동 로그 푸시, scope `admin.reports.audit.readonly`. 사용자 생성/삭제 이벤트 이름은 미확인 ([문서](https://developers.google.com/workspace/admin/reports/v1/guides/push)).
  - 수신 주소는 유효한 인증서의 HTTPS 필수(자체 서명 거부), 채널은 자동 갱신 안 됨, 서비스 계정과 도메인 전체 위임 필요.
  - Business Starter 에디션에서 쓸 수 있는지는 미확인. 실제 채널 등록 시험이 필요하다.
- Semaphore Integrations: `/api/integrations/<alias>`로 GET/POST 수신 시 템플릿 실행. 인증은 Token, HMAC(SHA-256/512), GitHub, 무인증. extractor로 본문/헤더 값을 환경변수나 task 파라미터로 전달 ([문서](https://github.com/semaphoreui/semaphore-docs/blob/main/docs/user-guide/integrations.md)).
- 구성안: `GWS 푸시 → 중계 서버(HTTPS, 채널 갱신) → Semaphore Integration(HMAC) → Ansible 전체 대조(reconcile)`.
  - 웹훅은 알림 신호로만 쓰고, 신호를 받으면 활성 사용자 목록을 읽어 서버 상태와 대조한다(푸시 유실, 채널 만료 대비). 야간 정기 실행을 안전망으로 둔다.
  - 6명 규모면 웹훅 없이 5~15분 주기 Semaphore 스케줄만으로도 충분할 수 있다.
  - 퇴사 처리(계정 삭제/잠금)는 Teleport 자동 생성이 지워주지 않으므로 Ansible 책임. 허용 목록과 dry-run으로 오삭제를 방지.
- 시험 계획: (1) 정기 실행 플레이북, (2) 서비스 계정으로 푸시 채널 등록 가능 여부 (GWS 슈퍼 관리자 설정 필요).

## 7. 추가 시험 결과 (2026-11-17, 2차)

### Teleport Community
- 역할 옵션으로 **SCP/SFTP 차단 시험 OK**: `ssh_file_copy: false` 역할 사용자는 `file copying via SCP or SFTP is not permitted`로 거부되고 파일이 만들어지지 않는다. 일반 SSH 명령은 허용된다. 재현 파일 `teleport-poc/conf/role-restrict.yaml`.
- `max_sessions`(동시 세션 제한)는 **Enterprise 전용**. 역할 생성 시 `role option max_sessions is only available in enterprise subscriptions` 에러. `max_connections`도 문서상 Enterprise 전용.
- 접근 요청: Just-in-time Access Requests는 Enterprise 기능이고 Community는 CLI 미리보기만 제공([문서](https://goteleport.com/docs/identity-governance/access-requests/oss-role-requests.md)). 시험에서는 요청 가능한 역할을 정의하지 않아 `can not request role` 거부만 확인했고 승인 흐름은 미시험.
- 세션 MFA: `require_session_mfa`(역할 또는 `cluster_auth_preference`)로 설정([문서](https://goteleport.com/docs/zero-trust-access/authentication/per-session-mfa.md)). MFA 장치가 필요해 비대화형 환경에서 미시험.
- 세션 참관(`join_sessions`, 참관/중재자 모드): 문서에 역할 예시가 있다([문서](https://goteleport.com/docs/zero-trust-access/authentication/joining-sessions.md)). 대화형 PTY가 필요해 미시험. 중재자(moderated) 모드는 Enterprise로 알려져 있으나 이번에 확인하지 못함.
- 감사 로그 보관: 문서상 기본 8766시간(1년), 스토리지 URI의 `retention_period`로 변경([문서](https://goteleport.com/docs/reference/deployment/backends.md)). 세션 녹화의 자동 삭제는 확인하지 못함.
- 포트 포워딩 차단: 시험했으나 대조군과 구분되지 않아(대상 포트 문제로 추정) 결론 없음.

### Warpgate
- **사용자 계정 잠금 시험 OK**: 같은 사용자로 10회 실패 시 `Exceeded 10 failed login attempts`로 1시간 잠금되고 올바른 비밀번호도 거부됨. 다른 사용자(ops)는 영향 없음. `DELETE /login-protection/locked-users/{username}`로 해제. 주의: IP 차단(기본 5회)이 먼저 걸리면 같은 IP의 추가 실패는 집계되지 않아, 단일 IP에서는 IP 차단이 사용자 잠금보다 먼저 작동한다(시험 시 IP 임계값을 임시로 올림, 시험 후 원복).
- 로그 보관/전송은 설정 파일 `log` 절 기준(문서·설정 확인, 미시험): `retention`(녹화 포함, 기본 7일), `audit_retention`(기본 1년), `send_to`(소켓 엔드포인트로 로그 전달), `format`(text/json). 녹화는 디스크 파일(`data/recordings`)이며 키 입력(stdin)이 마스킹 없이 그대로 기록된다. 위변조 방지(해시 체인, 서명) 기능은 찾지 못했다.

### JumpServer CE
- 계정 삭제 동기화: 서버 계정 삭제 작업(`POST /accounts/accounts/tasks/`, `action: remove`)이 존재한다. 이 API는 현재 사용자 비밀번호 재확인(`user_confirm_required`)을 요구하며, 재확인 API(`/authentication/confirm/`)가 오류를 반환해 삭제 시험은 완료하지 못했다.
- 삭제 시험 보강: 셸에서 `remove_accounts_task`를 직접 호출했으나 조직(org) 컨텍스트 문제로 `Please select an organization before saving` 에러 또는 대상 0건이 되어 완료하지 못했다. 삭제 동기화는 결론 없음.
- 세션 강제종료: 진행 중 SSH 세션 목록 조회(`/terminal/sessions/?is_finished=false`)는 되고, 명령 기록(`/terminal/commands/`)에 `sleep 90; echo END`가 남았다. 종료 요청 `POST /terminal/tasks/`(`kill_session`)은 200을 반환했지만 세션이 91초 후 자연 종료될 때까지 끊기지 않았다(요청 형식이 맞지 않았을 가능성, 결론 없음). UI의 종료 버튼은 미시험.
- 녹화 재생: 종료 직후 `/replay/`가 404(`Not found REPLAY file`)였다. 업로드 지연인지 저장 문제인지 미확인.
- 미시험: 접근 승인(ticket), 사용자·자산 수 제한, 웹 클라이언트 DB 접속.

### 데스크(문서) 조사로 확인한 항목
- SSH/DB GUI 클라이언트 지원 여부: 시험 없이 공식 문서로만 확인 (위 비교표의 GUI 행 참조).
- Teleport 접근 요청, 세션 참관, 감사 로그 보관기간, Warpgate 로그 보관/전송 설정.

### 문서확인으로 전환한 항목 (2차 데스크 조사, 2026-11-17)
- Teleport: 로컬 계정 잠금([문서](https://goteleport.com/docs/reference/access-controls/authentication.md)), `tctl lock`으로 기존 연결 종료([문서](https://goteleport.com/docs/identity-governance/locking.md)), Event Handler 플러그인으로 Fluentd 전달([문서](https://goteleport.com/docs/reference/deployment/monitoring/event-handler.md)), 세션 MFA, 감사 로그 보관.
- Warpgate: 관리 API로 세션 종료(`POST /sessions/:id/close`, 권한 `SessionsTerminate`), 로그 전송/보관 설정, google SSO.
- JumpServer: 연결 방식 ACL로 SFTP 비활성화 가능(소스), MFA 설정.
- 여전히 미시험으로 남은 것: 명령 필터(Teleport, Warpgate), 로그인 보호/계정 잠금(JumpServer), OpenBao 연동(JumpServer), 로그 위변조 방지.

### Warpgate 개인 OS 계정 1:1 매핑 (시험 OK, 2026-11-17)
- Warpgate 대상(target)은 접속 계정(`username`)과 인증(비밀번호, 공개키, 또는 `secret://` OpenBao 참조)을 **대상마다 하나** 가진다. 접속한 Warpgate 사용자명을 대상 OS 계정으로 넘기는 설정(템플릿, 통과)은 문서와 스키마에서 찾지 못했다.
- 따라서 1:1 매핑은 **사람×서버마다 대상을 하나씩 만드는 방식**으로 가능하다. 시험: 서버에 OS 계정 `dev1os` 생성 → 대상 `t-rocky9--dev1`(username `dev1os`) 생성 → 역할 `dev1-only`를 그 대상과 사용자 `dev1`에만 연결.
  - dev1은 `t-rocky9--dev1`로 접속하면 서버에서 `dev1os`로 실행됨 (`id -un`).
  - 다른 사용자(ops)는 같은 대상에 `Permission denied`.
  - dev1의 공용 root 대상 권한을 제거하면 root 대상은 거부됨.
- 한계: 대상 수가 사람×서버로 늘어난다(6명×서버 N대). 관리 API로 생성할 수 있으므로 Semaphore 플레이북으로 GWS 사용자 목록 기준 자동 생성·삭제를 설계해야 한다. 서버에는 개인 계정이 먼저 있어야 한다(Ansible). 인증은 계정별 비밀번호를 OpenBao에 두고 `secret://` 참조로 연결하는 방식을 권장하며, SSH 인증서(OpenBao 서명) 방식은 미시험.
