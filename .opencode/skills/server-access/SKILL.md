---
name: server-access
description: Use when accessing, deploying to, or operating the Lyla/Taskbot AWS EC2 production server over SSH. Triggers include "ssh to server", "deploy to server", "restart the service", "run alembic on server", "pull on server", or any remote operation on the EC2 host.
---

# Server Access (Lyla / Taskbot AWS EC2)

Operational skill for reaching the production server over SSH and running
deploys. Connection details and the private key live OUTSIDE this file in
the gitignored folder `.secrets/ssh/`.

## Where the secrets are

- Guide: `.secrets/ssh/SERVER_ACCESS.md` (full connection facts, deploy steps)
- Private key: `.secrets/ssh/layla-home.pem` (user supplies this manually)
- Both are gitignored. NEVER move them into a tracked file. NEVER print
  the key contents.

Read `.secrets/ssh/SERVER_ACCESS.md` first for the authoritative,
up-to-date connection facts.

## Connection (quick reference)

- Host (public DNS): `ec2-108-137-21-18.ap-southeast-3.compute.amazonaws.com`
- User: `ubuntu`
- Key: `.secrets/ssh/layla-home.pem`
- App dir: `/srv/lyla/app`

Single-command, non-interactive form (the only form the agent should use):

```powershell
ssh -i ".secrets\ssh\layla-home.pem" -o BatchMode=yes -o StrictHostKeyChecking=accept-new ubuntu@ec2-108-137-21-18.ap-southeast-3.compute.amazonaws.com "<remote bash command>"
```

The LOCAL shell is Windows PowerShell. The REMOTE shell is bash, so `&&`,
`||`, and `source` are valid inside the quoted remote command only.

## Before doing anything: discover the environment

Server facts that are NOT assumptions-safe:
- `python` is not on PATH — use `python3` or the project venv.
- `lyla-agent.service` does not exist — the real unit name is unknown.

Discover first:

```bash
ls -la /srv/lyla /srv/lyla/app
which alembic python3
find /srv/lyla -name activate 2>/dev/null
systemctl list-units --type=service | grep -iE "lyla|uvicorn|gunicorn|taskbot|fastapi"
```

Record the venv path and service name back into
`.secrets/ssh/SERVER_ACCESS.md` under "Verified environment".

## Standard deploy (run remotely, in order)

```bash
cd /srv/lyla/app
git checkout -- frontend/tsconfig.tsbuildinfo 2>/dev/null || true
git pull origin main
source <venv-path>/bin/activate
python -m alembic upgrade head
sudo systemctl restart <service-name>
curl -s http://127.0.0.1:8765/health
```

`alembic upgrade head` MUST succeed before restart, otherwise the agent
endpoint 500s on missing reminder columns (Phase 14/14b).

## Safety rules (production)

- Treat the host as PRODUCTION. Confirm before destructive actions
  (DB drops, `git reset --hard`, force ops, file deletion).
- Never `git push --force` to `main` from the server.
- Never echo `.pem`, `.env`, or secret values. Reference by name only.
- Prefer non-interactive single commands; do not open long interactive
  sessions.
- Stop and report on first failed step; do not continue blindly.

## Session scope

This skill is intended for the current working setup. Connection facts may
change (instance restart can rotate the public DNS). Re-read
`.secrets/ssh/SERVER_ACCESS.md` if SSH fails to resolve the host.
