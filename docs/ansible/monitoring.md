# Monitoring Role Task Specification

`monitoring` 역할은 Prometheus 생태계의 호스트 메트릭 수집기인 Node Exporter의 배포, 시스템 계정 격리, 그리고 Systemd 서비스 자동화를 수행합니다.

---

## 1. 개요 및 구현 기능 (What)

- **전용 격리 시스템 계정 생성**: 권한 탈취 위험을 최소화하기 위해 비로그인 셸(`/sbin/nologin` 또는 `/bin/false`)을 사용하는 `node_exporter` 및 `otelcol-contrib` 시스템 계정 및 그룹 생성.
- **Node Exporter 바이너리 배포**: 시스템 아키텍처(amd64 / arm64)를 자동 감지하여 GitHub 공식 릴리스 tarball을 다운로드하고 `/usr/local/bin/node_exporter`로 압축 해제 및 설치.
- **OpenTelemetry Collector Contrib 배포**: `otelcol-contrib` 바이너리 배포 및 OpenObserve OTLP 아웃바운드 스트리밍 파이프라인(로컬 `127.0.0.1:9100` 스크랩 + ISMS/ISMS-P 기준 OS 보안/감사 로그 수집 ➔ 중앙 OpenObserve로 OTLP Outbound 푸시) 구성.
- **Systemd 서비스 유닛 파일 등록**: `node_exporter.service` (`127.0.0.1:9100` 로컬 바인딩), `otelcol-contrib.service` 유닛 파일을 생성하여 부팅 시 자동 시작 및 프로세스 모니터링 보장.
- **네트워크 포트 아키텍처**: Node Exporter는 로컬 루프백(`127.0.0.1:9100`)에서만 리슨하며, Otel Collector가 중앙으로 **아웃바운드(Outbound)** 전송하므로 **외부 인바운드 방화벽 포트 오픈이 불필요**합니다.

---

## 2. 왜 구현해야 하는가? (Why)

1. **온프레미스 인프라의 다차원 가시성(Observability) 및 ISMS/ISMS-P 컴플라이언스 확보**:
   - 하드웨어 및 OS 리소스 고갈(디스크 풀, 메모리 OOM, CPU 스파이크)을 조기에 발견하고 알림(Alerting)을 발생시키기 위해 실시간 메트릭 수집이 필수적입니다.
   - 시스템 장애 분석 및 보안 감사를 위해 커널 로그(`/var/log/messages`, `syslog`), 인증 보안 로그(`/var/log/secure`, `auth.log`), 관리자 권한 상승 로그(`/var/log/sudo.log`), 커널 감사 로그(`/var/log/audit/audit.log`), 예약 작업 로그(`/var/log/cron*`), 침입 차단 로그(`/var/log/fail2ban.log`), 패키지 설치 이력(`/var/log/dnf.log`, `yum.log`, `dpkg.log`), 방화벽 로그(`/var/log/firewalld`)를 OpenTelemetry 파이프라인을 통해 중앙 OpenObserve로 단일화하여 수집합니다.
2. **최소 권한 원칙 & 포트 노출 제로(Zero Port Exposure)**:
   - 모니터링 데몬을 `root` 권한이 아닌 전용 비특권 `node_exporter` 및 `otelcol-contrib` 사용자로 실행하여 호스트 장악을 방어합니다.
   - Node Exporter 포트(`9100`)를 외부에 개방하지 않고 로컬 루프백으로 한정하여 공격 표면을 제거합니다.
3. **OpenObserve 중앙 통합 관제 연동**:
   - 로컬 Node Exporter 메트릭과 OS 로그를 단일 OTLP 스트림으로 결합하여 중앙 OpenObserve 백엔드로 실시간 전송합니다.

---

## 3. 무엇을 변경하는가? (What Changes)

- 📁 **설정 파일 및 바이너리**:
  - `/usr/local/bin/node_exporter` : Node Exporter 바이너리
  - `/usr/local/bin/otelcol-contrib` : OpenTelemetry Collector Contrib 바이너리
  - `/etc/otelcol-contrib.yaml` : OpenObserve 연동 OTLP 파이프라인 설정
  - `/etc/systemd/system/node_exporter.service` : Node Exporter 서비스 정의 (`--web.listen-address=127.0.0.1:9100`)
  - `/etc/systemd/system/otelcol-contrib.service` : OpenTelemetry Collector 서비스 정의
- ⚙️ **데몬 및 서비스**:
  - `node_exporter`, `otelcol-contrib` : 서비스 기동(`started`) 및 부팅 시 자동 실행(`enabled`)
- 👤 **사용자 및 그룹**:
  - `node_exporter`, `otelcol-contrib` 시스템 계정 및 그룹
- 🌐 **네트워크 포트**:
  - `127.0.0.1:9100/TCP` : 로컬 루프백 전용 바인딩 (외부 방화벽 개방 불필요)

---

## 4. 태스크 매트릭스 (Task Matrix)

| Spec ID | 태스크 명칭 (Task Name) | Ansible 모듈 | 지원 OS | 멱등성 보장 방식 |
|---|---|---|---|---|
| `MON-001` | `Create node_exporter system group` | `ansible.builtin.group` | All | 그룹 존재 시 `ok` |
| `MON-002` | `Create node_exporter system user` | `ansible.builtin.user` | All | 유저 존재 시 `ok` |
| `MON-003` | `Download and install Node Exporter binary` | `ansible.builtin.unarchive` | All (amd64, arm64) | `creates: /usr/local/bin/node_exporter` |
| `MON-004` | `Create systemd service for node_exporter` | `ansible.builtin.copy` | All (Systemd OS) | 파일 내용 일치 시 `ok` |
| `MON-005` | `Ensure node_exporter service is started and enabled` | `ansible.builtin.systemd` | All (Systemd OS) | 서비스 기동 상태면 `ok` |
| `MON-006` | `Create otelcol system group` | `ansible.builtin.group` | All | 그룹 존재 시 `ok` |
| `MON-007` | `Create otelcol system user` | `ansible.builtin.user` | All | 유저 존재 시 `ok` |
| `MON-008` | `Download and install OpenTelemetry Collector Contrib binary` | `ansible.builtin.unarchive` | RHEL 7+, Debian | `creates: /usr/local/bin/otelcol-contrib` |
| `MON-009` | `Deploy OpenTelemetry Collector Contrib configuration (OpenObserve OTLP pipeline)` | `ansible.builtin.template` | RHEL 7+, Debian | Checksum 비교 (`otelcol-contrib.yaml.j2`) |
| `MON-010` | `Create systemd service for otelcol-contrib` | `ansible.builtin.copy` | Systemd OS | 파일 내용 일치 시 `ok` |
| `MON-011` | `Ensure otelcol-contrib service is started and enabled` | `ansible.builtin.systemd` | Systemd OS | 서비스 기동 상태면 `ok` |

