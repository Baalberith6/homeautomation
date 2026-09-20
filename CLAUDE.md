# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## The knowledge base is next door

This repo is one half of a pair. The other half is [`../kb`](../kb) — the knowledge base that holds the spec, the architecture, the device knowledge, and the decisions behind this code.

| Repo | Holds | Your role here |
| --- | --- | --- |
| `.` (this one) | Python services, tests, deploy script, Telegraf and Grafana config | Write and maintain |
| [`../kb`](../kb) | Ideas, plans, specs, architecture, devices, decisions, runbooks | **Read freely. Do not write.** It maintains its own indexes and log |

**`../kb` holds the thinking. This repo holds the typing.**

Start from [`../kb/index.md`](../kb/index.md) when a task needs to know *why* something works the way it does. The rules that control logic must obey — battery SOC floors, comfort limits, tariff rules — live in `../kb/requirements/`. A threshold's reason lives in `../kb/decisions.md`. This file tells you what the code does; `../kb` tells you what it is supposed to do.

### Before implementing a change, look for its spec

A non-trivial change is worked out in `../kb` first, as idea, then plan, then spec, under `../kb/work/NNN-<slug>/`. A finished `spec.md` names the behaviour, the MQTT topics, the limits, the failure modes, and the acceptance checks. It is written to be implemented without further context.

- **If the user names a spec** — read it and implement it. Treat its acceptance list as the definition of done.
- **If the user asks for a non-trivial change with no spec** — say so, and offer to work it out in `../kb` first. Do not refuse to proceed; if they want it built now, build it, and say that the knowledge base will be behind until it is told.
- **A bug fix needs no spec.** The lifecycle is for a change in behaviour, not for every edit.

[`../kb/work/CHANGES.md`](../kb/work/CHANGES.md) is the pipeline and the backlog. There is no backlog in this repo.

### When the code contradicts the knowledge base

This happens, and finding it is valuable. The code is what actually runs; the knowledge base is what someone decided. Either can be the wrong one.

**Say so the moment you notice.** Quote both sides:

> **⚠ Contradiction — `<short title>`**
> - **Spec:** <what `../kb` says> — [link]
> - **Code:** <what the code does> — `file.py:line`

Never silently make the code match the document, and never assume the document is stale. Tell the user, and let them decide. If they want it recorded, that is a job for a session in `../kb` — say so rather than writing there yourself.

### Reporting back

When a change ships, tell the user in one line what `../kb` now needs to be told: which change shipped, and which pages it affects. A session there folds the spec into the wiki and marks the change `shipped`. Do not do it from here.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run linting
flake8

# Run tests
pytest tests/

# Run a single test file
pytest tests/estia_optimizer_unit_test.py

# Run an individual service (example)
python3 inverter.py
python3 wallbox.py

# Run a service locally in debug mode (safe alongside prod)
DEBUG=1 python3 inverter.py
```

`DEBUG=1` enables verbose output and appends `-dev` to the MQTT client ID so the local instance doesn't disconnect the production one. Netatmo token files also use a `.dev.token` suffix to avoid overwriting prod tokens. **Caution:** services that control devices (`wallbox.py`, `inverter_setter.py`, `estia_optimizer.py`) will still send real commands — avoid running them locally while prod is active.

CI runs on every push via `.github/workflows/test.yaml` (Python 3.9, flake8 + pytest).

## Where the architecture lives

Services, hosts, and topics: `../kb/architecture/services.md`, `topology.md`, `mqtt-topics.md`

The energy loop: `../kb/architecture/data-flows.md`

**State management:** MQTT-based services use module-level global variables to persist state between messages (e.g., `soc`, `amp` in `wallbox.py`). Services rely on an external supervisor (systemd/supervisord) for restart-on-failure.

**OAuth tokens:** Netatmo tokens are persisted to `netatmo.token` and `netatmo_optimizer.token` on disk and refreshed every 2 hours at runtime.

**Config structure:** `config.py` holds all device IPs, MQTT/InfluxDB endpoints, device IDs, and polling intervals. `secret.py` holds all API keys and credentials (not in git).

## Grafana

- Grafana instance: `http://192.168.1.50:3000/` (configured in `config.py` as `grafanaConfig`)
- API token for reading dashboard variables: `grafanaApiKey` in `secret.py`
- Service account token for dashboard management: `grafanaServiceAccountToken` in `secret.py`
- `grafana_setter.py` reads dashboard template variables and publishes them to MQTT

**Grafana workflow:** After deploying dashboard changes via API, always fetch the live JSON back and update `spec/grafana/prdikov.json` so the local copy stays in sync. Start from `prdikov.json` when making further changes — never build from scratch. **Always update `spec/grafana/grafana-spec.md`** to reflect any changes made to the dashboard.

`spec/grafana/grafana-spec.md` is the build reference for `spec/grafana/build_dashboard.py`, which generates `spec/grafana/prdikov.json`.
`spec/grafana/prdikov.json` is the generated artefact and the sync-back target after a deploy.

Panel map and field reference: `../kb/architecture/grafana.md`
