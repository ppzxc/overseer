# ADR 0007: OpenBao and Semaphore with SQLite

**Status:** accepted

Boundary Community Edition is archived and has no planned security fixes, so Overseer no longer includes Boundary. The control plane is OpenBao for SSH CA and secrets plus Semaphore UI for Ansible GitOps. Semaphore uses a persistent SQLite file for the single-instance default, avoiding a separate database service. Existing PostgreSQL data is not imported or deleted by this change; a database-engine migration must be handled separately before switching a live Semaphore installation.
