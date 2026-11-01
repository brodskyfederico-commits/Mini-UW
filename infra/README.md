# VPS infrastructure record — partial inventory

Observed in this session: user `miniuw`, hostname `ubuntu-dallas-2gb`, Codex CLI `0.166.0`; current chat workspace under `/home/miniuw/Documents/Codex/2026-11-01/use-the-mini-uw-vps-ssh`.

The handoff reports Ubuntu 24.04 LTS, approximately 1 vCPU/2 GB RAM/60 GB SSD, Node/npm and an earlier root project. These capacity/software claims have not all been independently checked in this milestone. The expected `/home/miniuw/projects/Mini-UW` is absent; `/root/projects/Mini-UW` is not readable by this account. Do not copy root credentials or Codex authentication.

GitHub stores reviewed infrastructure definitions and runbooks. No infrastructure-as-code, server provisioning, deployment pipeline, service restart, automatic push, database backup or disaster recovery restore has been configured or verified. Inventory running services and storage before proposing any migration. Store secret values in a separately managed credential system, never Git.

Document reader used only for this review: pypdf 6.21.4, downloaded as a wheel from PyPI and checked against its published SHA-256, unpacked into the chat's work/vendor directory. No system installation or production dependency change. DOCX/XLSX were read with standard-library ZIP/XML without executing macros, formulas or supplied scripts. Workspace tools and package binaries are excluded from the milestone.
