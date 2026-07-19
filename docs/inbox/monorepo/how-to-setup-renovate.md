# How to setup renovate

Self-hosted Renovate for this monorepo's Python dependencies, running as a
GitHub Action. Every update lands as a PR for a human to merge — Renovate never
commits to `master` and never automerges.

This is both a setup guide and a record of what went wrong getting there. The
debugging section is the useful half: most of the config is one line of "what"
and ten lines of "why", and the why is only obvious once you've hit the failure.

---

## 1. The moving parts

Three files, plus GitHub-side configuration that isn't in the repo.

| File | Role |
| --- | --- |
| `.github/workflows/renovate.yml` | When it runs, and with what secret |
| `.github/renovate-global.js` | Self-hosted (runner) config — settings a repo config isn't allowed to set |
| `.github/renovate.json5` | Repository config — what to update, how to group, when |

The global/repository split matters. Renovate's precedence, lowest to highest:

```
repository config  <  environment variables  <  global `force` block
```

Anything under `force:` in the global config overrides the committed repo
config. That's the only lever that beats `renovate.json5`, which is why
per-run overrides have to travel that way rather than as a plain env var.

### GitHub side (not in the repo)

**A fine-grained PAT**, stored as `RENOVATE_TOKEN` in a GitHub Actions
environment named `renovate`.

| Permission | Level | Needed for |
| --- | --- | --- |
| Contents | Read and write | Pushing the branch |
| Pull requests | Read and write | Opening the PR |
| Issues | Read and write | The dependency dashboard issue |
| Commit statuses | Read and write | Branch status checks — see §4.6 |
| Metadata | Read | Automatic, mandatory |

Because the secret lives in an environment, **the job must declare
`environment: renovate`**. Without it the secret silently resolves to an empty
string and Renovate fails to authenticate.

---

## 2. Running it

The workflow fires on a daily cron (`0 18 * * *` UTC = 03:00 Asia/Tokyo) plus
manual dispatch. That cron is *not* the update cadence — `schedule` in
`renovate.json5` restricts actual work to **Monday 00:00–06:00 Asia/Tokyo**.
The daily run is just a chance to notice the window; on other days Renovate
wakes, sees it's out of schedule, and does nothing.

Manual dispatch takes two inputs:

- **`dryRun`** — logs what would happen, opens nothing. Maps to
  `RENOVATE_DRY_RUN: full`; unchecked passes the string `null`, which Renovate
  reads as "run for real".
- **`logLevel`** — `info` or `debug`. Reach for `debug` the moment a failure
  stops making sense (see §4.6).

Dispatch ignores the repo `schedule`, so it's the way to test outside Monday.

---

## 3. Design decisions

### Poetry only

```json5
enabledManagers: ["poetry"],
```

Load-bearing. Without the allowlist, Renovate's `pip_requirements` manager
parses `requirements.txt` — 4348 lines of pinned, hashed, fully-resolved
transitive deps — and raises a PR per entry. Verify it's working by checking
the extraction line in the log:

```
{"poetry": {"fileCount": 1, "depCount": 84}}
```

One file, ~84 deps. If you see thousands, the allowlist isn't taking effect.

### requirements.txt is generated, never a source of truth

`MODULE.bazel:31` feeds `requirements.txt` to `pip.parse`, so it has to stay in
sync with `pyproject.toml` or `check_requirements_txt.sh` fails on every PR.
Renovate updates the manifest and lock but knows nothing about the export, so
`postUpgradeTasks` regenerates it:

```json5
postUpgradeTasks: {
  commands: [
    "poetry self add poetry-plugin-export",
    "poetry export -f requirements.txt -o requirements.txt",
  ],
  fileFilters: ["requirements.txt"],
  executionMode: "branch",
},
```

Two things to keep right:

- The export command **mirrors `update_requirements_txt.sh` exactly** (no
  `--without-hashes`), or the diff won't match what the check script expects.
- `executionMode: "branch"` runs it once per branch after all updates are
  applied. The default (`update`) would re-export once per bumped dependency —
  wrong and slow for a grouped PR.

Post-upgrade commands are refused unless they match `allowedCommands` in the
**global** config. Renovate makes this global-only by design so a repo config
can never grant itself arbitrary command execution.

### Grouping

- Minor + patch → one weekly PR, `groupName: "python deps (non-major)"`.
- Majors → individual PRs, so they stay readable and revertable alone.
- The langchain family + `openai` → their own group, majors and minors
  together, rule placed **last** so it overrides the two above.

`groupSlug` is set on every group. Without it the branch for the non-major
group is literally `renovate/python-deps-(non-major)` — parens are legal in a
ref but need shell quoting on every single checkout.

### Python is pinned, and Renovate must not touch it

```json5
ignoreDeps: ["python"],
constraints: { python: "3.13.13" },
```

`[tool.poetry.dependencies] python` is just another dependency to the poetry
manager, and `3.13 → 3.14` reads as a *minor* update — so it quietly landed in
the grouped non-major PR and broke the lock step. The interpreter is pinned in
three places Renovate can't see (`.tool-versions`, `MODULE.bazel:24`,
`MODULE.bazel:31`), so bumping it here alone desyncs the Bazel toolchain.
Python upgrades stay a deliberate, coordinated, human change.

`constraints.python` is separate and still required: Renovate provisions its
own interpreter (`binarySource=install`) and has to be told which one, or
poetry aborts with *"the currently activated Python version is not supported by
the project"*.

---

## 4. Everything that went wrong

In order. Several of these cost real time, and two of them I diagnosed wrong
before getting there.

### 4.1 No PR on the first run

Run happened Sunday 00:12 JST; `schedule` was `* 0-6 * * 1` — Monday only.
Working exactly as configured. Use `workflow_dispatch` to test off-schedule.

### 4.2 Commits marked "Unverified"

Renovate's default author is `renovate@whitesourcesoftware.com`, a Mend-owned
address with Vigilant Mode on, so every commit lands unverified. Fixed by
setting `gitAuthor` to an identity tied to this account. Trade-off: bumps now
read as authored by you rather than a bot.

### 4.3 `403: Permission to jack06215/monorepo.git denied`

PAT was missing `Contents: Read and write`.

### 4.4 Python 3.14 in the lock step

```
The currently activated Python version 3.13.13 is not supported by the project (3.14.6)
```

Renovate bumping the `python` dep itself. Fixed with `ignoreDeps` — see above.

### 4.5 The `minimumReleaseAge` dead end

Added a 10-day release-age gate to blunt supply-chain attacks. It doesn't work
with caret ranges under poetry:

```
Artifact update for colorlog resolved to version 6.11.0, which is a pending
version that has not yet passed the Minimum Release Age
```

Renovate proposes `6.10.1`, rewrites the range to `^6.10.1`, then poetry
resolves that range to the newest match — `6.11.0` — which is still inside the
age window. Renovate has no way to hand poetry an exact target to enforce
against ([renovatebot/renovate#41624][issue]).

The only workaround was `rangeStrategy: "pin"`, collapsing every range to an
exact version. That worked, but it makes `pyproject.toml` stop reading as
human-authored intent and erases hand-placed upper bounds (`pytest <8.2.0`,
`pandas-stubs <2.2.4`, `pytz ~2024.2`), which then have to be restated as
`allowedVersions` packageRules.

**Resolution: dropped the age gate, reverted to `rangeStrategy: "bump"`.**
Keeping an unenforceable gate is worse than not having one — it's a false sense
of protection. `bump` moves the range floor forward (`^6.9.0 → ^6.10.1`) so the
manifest diff still shows the change per PR; `requirements.txt` remains the
fully pinned, hashed artifact Bazel actually consumes. Revisit if #41624 closes.

[issue]: https://github.com/renovatebot/renovate/issues/41624

### 4.6 "Repository has changed during renovation - aborting"

The expensive one. Renovate pushed a branch, then aborted before opening the
PR, with only that line at `info` level. **I guessed twice and was wrong both
times** — first calling it transient, then blaming previously-closed PRs and
adding `recreateWhen: "always"`, which changed the symptoms just enough to look
plausible without fixing anything.

`logLevel: debug` named it immediately:

```
DEBUG: Updating renovate/stability-days status check state to yellow
DEBUG: POST .../statuses/00e3b7e8... = (statusCode=403)
DEBUG: Caught error setting branch status - aborting
  "message": "Resource not accessible by personal access token"
  "x-accepted-github-permissions": "statuses=write"
DEBUG: Passing repository-changed error up
 INFO: Repository has changed during renovation - aborting
```

The PAT lacked **`Commit statuses: Read and write`**. Renovate catches the 403
and rethrows it as `repository-changed`, which is why the surface message
points nowhere near the cause. GitHub names the exact permission it wanted in
the `x-accepted-github-permissions` header.

What made it hard to pin down:

- It only started after `minimumReleaseAge` was added — that setting is what
  creates the `renovate/stability-days` check in the first place.
- **Dry runs never reproduced it.** A dry run logs `Would update ... status
  check` and makes no API call, so it can't hit the 403. Every dry run looked
  perfect while every real run aborted.
- Earlier real runs *had* opened PRs fine — before the age gate existed.

Two lessons worth keeping: **go to `debug` on the second unexplained failure,
not the fifth**, and **a clean dry run does not mean a clean run** — dry mode
skips exactly the mutating calls most likely to be denied.

The age gate is gone now, so the stability-days check isn't published and this
permission is no longer strictly required. Leave it granted anyway; the cost is
nothing and the failure mode is this misleading.

### 4.7 `version solving failed` on the langchain group

PR #13 broke because `langchain-openai`'s own *minor* releases can require a
newer `openai` **major** (1.3.5 needs `openai>=2.45.0,<3.0.0`). The
langchain bump landed in the non-major group while openai's major bump sat in a
separate, not-yet-opened PR, so poetry couldn't resolve either branch.

Fixed by grouping the whole family — `langchain`, `langchain-community`,
`langchain-ollama`, `langchain-openai`, `langgraph`, `openai` — into one branch
with **no `matchUpdateTypes` filter**, so majors and minors travel together.

Generalisable: any set of packages that release in lockstep upstream must be
grouped without an update-type filter, or Renovate will split a
mutually-dependent bump across two branches that each fail alone.

---

## 5. Known limitations

- **`lockFileMaintenance` is unguarded.** It re-resolves the whole transitive
  tree; nothing constrains what poetry picks.
- **The github-actions manager is disabled**, so
  `renovatebot/github-action@v46.1.19` and `actions/checkout@v6` in the
  workflow must be bumped by hand. Worth a calendar reminder.
- **GitHub disables scheduled workflows after 60 days of repo inactivity.** If
  Renovate goes quiet for months, check this before debugging config.
- **The plugin manifests are excluded** via `ignorePaths`
  (`packages/llm_cli/plugins/`). They're PEP 621 (`[project]`, no
  `[tool.poetry]`) so they're skipped today regardless; the exclusion keeps
  that true if either ever gains a `[tool.poetry]` section.

---

## 6. Checklist for a fresh setup

1. Commit the three config files.
2. Create the fine-grained PAT with all five permissions from §1 — including
   **Commit statuses**.
3. Create a GitHub Actions environment named `renovate`, store the PAT as
   `RENOVATE_TOKEN`.
4. Confirm the workflow job declares `environment: renovate`.
5. Dispatch with `dryRun: true`, confirm the extraction line reads
   `{"poetry": {"fileCount": 1, ...}}` and not thousands of deps.
6. Dispatch for real. Expect a branch, a `requirements.txt` diff alongside
   `pyproject.toml` + `poetry.lock`, and a PR.
7. If anything aborts unexplained, go straight to `logLevel: debug`.
