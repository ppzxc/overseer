# ADR-0008: Service Compose Folders and Persistent Data Layout

- **Status**: Accepted
- **Date**: 2026-11-13
- **Deciders**: Overseer Engineering Team & User

## Context

The control plane shares a Docker Compose project name with Forgejo. Keeping service definitions under one provisioning directory couples service lifecycle files to operational scripts and makes service-specific backups harder to inspect.

## Decision

Each production service directory contains only its Compose file:

- `/opt/services/openbao/compose.yml`
- `/opt/services/semaphore/compose.yml`

Operational scripts and the environment file remain in the existing Overseer operational directory selected by `TARGET_DIR`. The service Compose directories are selected through `OPENBAO_COMPOSE_DIR` and `SEMAPHORE_COMPOSE_DIR` in that environment file.

Persistent settings and data live outside the Compose directories:

| Service content | Host path | Container path |
|---|---|---|
| OpenBao configuration and profiles | `/data/openbao/config` | `/openbao/config` |
| OpenBao Raft database and CA public key | `/data/openbao/data` | `/openbao/data` |
| Semaphore configuration, including `requirements.txt` | `/data/semaphore/config` | `/etc/semaphore/requirements.txt` |
| Semaphore SQLite database | `/data/semaphore/data` | `/var/lib/semaphore` |
| Semaphore repositories and task work files | `/data/semaphore/work` | `/tmp/semaphore` |

The Semaphore database and work directory remain separate. OpenBao's data directory is mounted read-only into Semaphore for CA public-key access.

## Consequences

- `production-sync` copies one `compose.yml` into each service directory and stores service configuration under `/data`.
- Moving existing state to the new paths requires stopping the relevant service, preserving a backup, copying data with ownership intact, and verifying the database or OpenBao state before starting the new Compose service.
- Compose project name `app`, the external `backend` network, and the Forgejo-compatible log rotation settings remain unchanged.
