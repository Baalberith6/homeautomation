# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## The knowledge base is next door

This repo is one half of a pair. The other half is [`../kb`](../kb) — the knowledge base that holds the spec, the architecture, the device knowledge, and the decisions behind this code.

| Repo | Holds | Your role here |
| --- | --- | --- |
| `.` (this one) | Python services, tests, deploy script, Telegraf and Grafana config | Write and maintain |
| [`../kb`](../kb) | Ideas, plans, specs, architecture, devices, decisions, runbooks | **Read freely. Write only the build records of the change that you implement** (see below). It maintains its own indexes and log |

**`../kb` holds the thinking. This repo holds the typing.**

Start from [`../kb/index.md`](../kb/index.md) when a task needs to know *why* something works the way it does. The rules that control logic must obey — battery SOC floors, comfort limits, tariff rules — live in `../kb/requirements/`. A threshold's reason lives in `../kb/decisions.md`. This file tells you what the code does; `../kb` tells you what it is supposed to do.

### Before the first edit, find the change

Every edit to this repo is a change, also a small fix. A change is worked out in `../kb` first, under `../kb/work/NNN-<slug>/`, on one of two paths ([`../kb/work/README.md`](../kb/work/README.md)):

- **The full path** — `intent.md`, `spec.md`, `plan.md` and `test.md`. Implement only when `plan.md` and `test.md` are `status: approved`.
- **The small path** — one file, `change.md`. Implement only when it is `status: approved`.

There is no third path.

- **If the user names a change** — read every file in its folder and implement it. Its acceptance checks are the definition of done.
- **If the user asks for an edit with no approved change** — stop and say so. The change is opened in `../kb` with `/small` or `/intent`. Do not build first.
- **A bug fix is a change.** It starts with a test that fails. Record the failure, commit, then fix.
- **On the small path, watch the four criteria.** If the work needs a new or changed topic, limit, setpoint or device write, a decision, a credential, or a second pull request, stop and tell the user. The change moves to the full path.

During the build, write only these records in `../kb`: `plan.md` when the work departs from it, and the Results section of `test.md`. On the small path, write the Departures and Results sections of `change.md`.

[`../kb/work/CHANGES.md`](../kb/work/CHANGES.md) is the pipeline and the backlog. There is no backlog in this repo.

### When the code contradicts the knowledge base

This happens, and finding it is valuable. The code is what actually runs; the knowledge base is what someone decided. Either can be the wrong one.

**Say so the moment you notice.** Quote both sides:

> **⚠ Contradiction — `<short title>`**
> - **Spec:** <what `../kb` says> — [link]
> - **Code:** <what the code does> — `file.py:line`

Never silently make the code match the document, and never assume the document is stale. Tell the user, and let them decide. If they want it recorded, that is a job for a session in `../kb` — say so rather than writing there yourself.

### Reporting back

When a change is merged and deployed, tell the user in one line what `../kb` now needs: which change, and which pages it affects. A session there moves the ledger row to `merged`, folds the change into the wiki, and moves the row to `folded`. Do not do it from here.

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

CI runs on every push via `.github/workflows/test.yaml` (Python 3.11, the minor version of the production venv on `192.168.1.51`; flake8 + pytest). The ruleset `main` requires the check `build (3.11)` before a merge and blocks force pushes; do not rename the job.

## Review (change 032)

### The PR body

The owner reads the PR body in a few seconds. Write the change line, then five fields. Each field is its own paragraph with a bold label, and has one or two short sentences, 240 characters at most:

```
**Change NNN** (<full or small path>) · `../kb/work/NNN-<slug>/<file>` · approved <date>

**Owner must do:** <the action before the merge or the deploy, or "nothing">

**What:** <what the PR changes>

**Tested:** <the counts and the commits>. Results: <the file and the section in ../kb>

**Not covered:** <what the tests do not see, or "nothing">

**Revert:** <one line>
```

- Keep the bold labels and the blank line between two fields. GitHub shows plain lines with no blank line as one block of text.
- `Owner must do` is the first field: it is the line that the owner needs. A step before the merge (a ruleset, a token) or before the deploy (an install on `.51`) goes there, not into another paragraph.
- No table, no code block, and no more than 12 lines of text. The evidence is in the Results of the change folder; the body points to it.
- Write the body to a file. `python3 -m review.body <file>` must print `PR body: ok`. Then `gh pr create --body-file <file>`. The review agent runs the same check; a problem is a finding that stops the merge.

### The review

After `gh pr create`, start the subagent `pr-reviewer` with the PR number. It follows [`review/reviewer.md`](review/reviewer.md): it sets the risk (`review/risk.py`), reviews the code, compares the diff with the intent of the change, takes before and after screenshots of a dashboard change on temporary boards (`review/preview.py`), and writes one PR comment (`review/report.py`). The comment starts with the decision and the commit. Then it has one line for each gate: Approval, Drift, Findings, Checks, Tests. A gate that waits for the owner or fails is open. The agent returns a decision. It never merges, pushes a dashboard or deploys. You do that, by the decision:

| Decision | What you do |
|---|---|
| `auto-merge` | If the PR changes `spec/grafana/prdikov.json`: `GRAFANA_TOKEN=... python3 spec/grafana/push_prdikov.py --push` on the PR branch; for `ai.json`: `push_ai_dashboard.py --push`. Commit the sync-back and push it. Run `python3 -m review.risk --base <merge base> --head <new head>`: it must say `low`. Then `gh pr merge <n> --auto --merge`. After the merge, `./deploy.sh <unit>` for each changed service |
| `wait-owner` | Stop. Tell the owner the PR, the commit of the comment, and the `Owner must do` line. When the owner says "merge" in the chat, do the same steps and `gh pr merge <n> --merge --match-head-commit <sha>` (the command is in the Approval gate) |
| `fix-findings` | Fix the findings or the failed tests, push, and start `pr-reviewer` again. After three rounds with open findings, stop and ask the owner about the approach. You count the rounds; the tool does not |
| `refuse` | Nothing: the PR is not from the owner or comes from a fork |

- **The word of the owner is for one commit.** `<sha>` is the head that the comment names. If the head changes after the owner said "merge", run `pr-reviewer` again and ask again. One exception: the sync-back commit of a dashboard. If `git diff --name-only <sha> HEAD` lists only `spec/grafana/prdikov.json` or `spec/grafana/ai.json`, merge with the new head and tell the owner.
- A low-risk PR also waits for the owner in four cases: the `Owner must do` line of the PR body is not "nothing"; the diff does something that the intent does not name; the PR has a change folder and the agent did not measure the drift; the agent wrote a row of `drift.json` that the tool cannot read. The Approval gate names the case.
- A file of the review that is missing or broken (`findings.json`, `pr.json`, `drift.json`, `preview.json`) is a finding, never "nothing found". Start `pr-reviewer` again.
- In the Results of the change folder, give each acceptance check a row in a table whose first header cell is `Check`. The last cell is the verdict: `pass`, `fail`, or `open until <date or run>`. The review tool reads only these rows and shows them in the Checks gate. They do not decide the merge: only the findings of the agent, the test run of the review, the drift and the PR body do.
- After auto-merge is on, push no commit to the branch. If you must, run `gh pr merge <n> --disable-auto` first.
- **Private data stays out of the images (change 042).** Private data is the data of the family wiki and of the cars. `review/preview.py` classes each panel from the measurements and fields that its queries read. A panel that is private, or that the rule does not know, is a tile "Private data: not shown" in every uploaded image. If such a panel changed, its before and after images are in the folder `private/` of `~/homeautomation/review-out/pr<n>/` on the Mac and are never uploaded; tell the owner the path. A panel that reads a new measurement is held until the measurement is in `PUBLIC_DATA` or `PARTLY_PRIVATE` in `review/preview.py`; add it in the PR that adds the panel.
- If CI fails after a live push, push the backup back: `push_prdikov.py --push --file <backup>` (the path is in its output).
- The agent needs the LAN, `secret.py` with `grafanaServiceAccountToken` and `influxPreviewToken`, `~/homeautomation/review-venv` (see `review/requirements.txt`), `uv` and `node`. The dashboard tests run panel JavaScript in `node` and skip without it. With `uv` the agent makes the test environment `~/homeautomation/review-test-venv` (Python 3.11, as CI) and installs the `requirements.txt` of the PR head into it in each run (`review/reviewer.md`, step 6).

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

**Grafana workflow:** Push Prdikov with `GRAFANA_TOKEN=... python3 spec/grafana/push_prdikov.py --push` (`--dry-run` first). It saves the live JSON to `~/homeautomation/grafana-backups/`, stops if the setpoint definitions (the template variables without their values) differ from live, pushes with the **live** setpoint values (the owner's latest) and `"overwrite": false`, and syncs the live JSON back into `prdikov.json`; commit the sync-back. After deploying dashboard changes via API, always fetch the live JSON back and update `spec/grafana/prdikov.json` so the local copy stays in sync. Start from `prdikov.json` when making further changes — never build from scratch. **Always update `spec/grafana/grafana-spec.md`** to reflect any changes made to the dashboard.

`spec/grafana/grafana-spec.md` is the build reference for `spec/grafana/build_dashboard.py`, which generates `spec/grafana/prdikov.json`.
`spec/grafana/prdikov.json` is the generated artefact and the sync-back target after a deploy.

Panel map and field reference: `../kb/architecture/grafana.md`

**The AI dashboard** (UID `ai`, change 028) is `spec/grafana/ai.json`, built-in panels only, Flux on the InfluxDB bucket `ai` that the librarian of `../ai` writes. `spec/grafana/ai.json` is the source: edit it (or the dashboard in the UI), push with `GRAFANA_TOKEN=... python3 spec/grafana/push_ai_dashboard.py --push`, which saves the live JSON to `~/homeautomation/grafana-backups/` first and syncs the live JSON back into `ai.json` after the push; commit the sync-back. After an edit in the UI, run `--fetch` and commit. The script never touches Prdikov or the alert rules.
