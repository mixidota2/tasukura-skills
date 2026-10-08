---
name: tk
description: >
  Local task management (tasukura). Two-layer memory model: progress_logs (raw timeseries)
  and typed records (extracted knowledge). Use for task operations and progress logging.
  Refer to this skill before recording progress, decisions, findings, or blockers.
---

# tk - Local Task Management

Local SQLite-based task management CLI designed for AI coding agents. Two-layer memory
model: `progress_logs` (raw timeseries) + typed `records` (extracted knowledge).

## Prerequisite

Requires [tasukura](https://github.com/mixidota2/tasukura) 0.1.7 or later, installed
separately with `uv tool install "tasukura>=0.1.7"` or `pip install "tasukura>=0.1.7"`.
Confirm `tk --help` works before operating on tasks. The skill does not bundle the CLI
or a task database.

## Execution (Strict)

Always execute the `tk` command directly. `tk` is registered in PATH; do NOT use
`uv run tk`, `python -m tasukura`, etc.

## Commands

| Command | Description |
|---------|-------------|
| `tk add "Title" --description "..." [--source-id ID] [--source TYPE] [--parent ID] [--next-action "..."] [--top] [--after ID]` | Add a task (description required) |
| `tk list [--status todo,in_progress] [--source TYPE] [--flat]` | List tasks (tree by default) |
| `tk update <id> [--title "..."] [--source-id ID] [--source TYPE]` | Update title or external source linkage. For `next_action` / `description`, use `tk log` |
| `tk delete <id>` | Delete task (fails cleanly if records exist) |
| `tk status <id> <new_status>` | Change status (todo/in_progress/in_review/done) |
| `tk log <id> --summary "..." [--details "..."] [--remaining "..."] [--next-action "..."] [--description "..."]` | Record progress. `--next-action` updates task and is persisted as `next_action_set` on the log (history). `--description` updates task only |
| `tk log-update <log_id> [--summary "..."] [--details "..."] [--remaining "..."]` | Edit a log (empty string clears) |
| `tk log-delete <log_id>` | Delete a log (fails cleanly if a record references it) |
| `tk record add <task_id> --kind <decision\|finding\|blocker\|question\|hypothesis> --log-id <log_id> --summary "..." [--details "..."] [--supersedes <record_id>]` | Add a typed record extracted from a log |
| `tk record list <task_id> [--kind X] [--all]` | List records (active by default) |
| `tk record show <record_id> [--with-log]` | Show record; `--with-log` dereferences source log |
| `tk record update <record_id> [--summary "..."] [--details "..."]` | Typo / wording fix only |
| `tk record resolve <blocker_id>` | Mark blocker resolved |
| `tk record obsolete <id>` | Retire a record without replacement |
| `tk record verify <id>` | Update `last_verified_at` (re-confirmed valid) |
| `tk record delete <id>` | Permanently delete a mistaken record. For valid records, prefer `obsolete` |
| `tk rank <id> [--after ID]` | Reorder |
| `tk board [--status ...]` | Kanban view |
| `tk show <id> [--full] [--kind X] [--logs N]` | Active context view |

IDs accept prefix matches (12-char short IDs displayed).

## Two-Layer Memory Model

```
progress_logs   <- raw timeseries trace (process, investigation, discussion, alternatives)
   |
   | extract & summarize (promote with --log-id)
   v
records         <- typed memory (conclusion, rationale, scope only)
   |
   | automatic narrowing (status / freshness / threshold)
   v
tk show         <- active context (read by the LLM every turn)
```

**Cardinality rule of thumb:** Most logs do **not** become records. Records are for facts
an agent should re-read in future sessions.

## When to Use What

### `tk log` (always write)

- On every commit
- At every meaningful progress milestone
- When verbalizing a design discussion as "the process"
- When a blocker appears or is resolved
- For failed attempts — do NOT promote these to records
- Put the full process into `--details`. This becomes the raw evidence for any future record.

### `tk record add` (only when promoting)

| kind | When to use |
|------|-------------|
| `decision` | A design choice, policy, or constraint has been finalized |
| `finding` | An investigation or experiment confirmed a **fact** |
| `blocker` | A blocker that future work may need to reference |
| `question` | An open issue you want to track **explicitly** even though unresolved |
| `hypothesis` | A "probably X" assumption you're operating on but haven't verified |

**Procedure:**

1. `tk record list <task_id> --kind <X>` to see existing active records (dedup responsibility)
2. If a duplicate exists, supersede it: `tk record add ... --supersedes <old_id>` (old is auto-marked superseded)
3. Otherwise just `tk record add ... --log-id <log_id>`

`--log-id` is **required**. This enforces the promotion gate (raw → typed) and prevents
"orphan records" whose root cause cannot be traced.

### Record content guideline (extract, do not copy)

Following the research literature (Memori semantic triples, "From Storage to Experience"
trajectory abstraction): a record is not a copy of the raw log — it is the **conclusion
extracted** from it.

| Field | Put here | Do not put here |
|-------|----------|-----------------|
| `record.summary` | The conclusion in one line ("we adopted X", "X is broken", "X happened") | Process, alternatives considered |
| `record.details` | Essential rationale, scope, constraints, reconsideration triggers | Process, investigation steps, rejected alternatives |
| `log.summary` | One line summarizing the activity | — |
| `log.details` | Process, investigation, discussion, alternatives (raw evidence) | — |

**Bad (record is a copy of the log):**

```
log.details   = "Compared OIDC / Auth0 / self-hosted. OIDC: standards-compliant, medium maintenance.
                 Auth0: SaaS, expensive. Self-hosted: high learning cost. Conclusion: OIDC."
record.details = "Compared OIDC / Auth0 / self-hosted. OIDC: standards-compliant ..."
                     ^^^^ verbatim copy of the log
```

**Good (record extracts the conclusion):**

```
log.details   = "<same process as above>"
record.summary = "Adopt OIDC for authentication"
record.details = "Driving criteria: balance of maintenance cost and standardization;
                  avoid vendor lock-in.
                  Scope: all authentication-related modules.
                  Reconsideration trigger: when migrating to a managed SaaS."
```

To see the process later, use `tk record show R-xxx --with-log` to dereference the source log.

## Lifecycle

```
add (--supersedes <old>)
  └─ Old record's status is auto-flipped to 'superseded'
update (typo / wording fix only)
  └─ For semantic changes, always use 'add --supersedes' instead
resolve (blocker only)
  └─ status=resolved, resolved_at=now
obsolete (retire without replacement)
  └─ status=obsolete
verify (no content change)
  └─ last_verified_at=now (clears the [stale] marker)
delete (mistaken record only)
  └─ row removed entirely. Use 'obsolete' for valid records you want to keep in history.
```

## How to Read `tk show`

Default output:

```
Active Decisions (N):
  R-xxxx  <summary> [stale]?
  ...

Active Blockers (N):  ...
Open Findings (N):    ...
Open Questions (N):   ...
Open Hypotheses (N):  ...

Recent logs (5):
  L-xxxx  [date] <summary>

⚠ Active <kind>s (N) exceed threshold (K) — consider obsolete/supersede
```

- Read **ID + summary** only. Dereference details only when needed via `tk record show R-xxx`.
- `[stale]` marker = `last_verified_at` (or `created_at` if never verified) is older than
  `stale_after_days`. Resolve by `tk record verify` or `tk record obsolete`.
- Warning = active set is growing. Clean up via `obsolete` / `supersede`.

Options: `--full` (include inactive records and all logs), `--kind <X>` (filter), `--logs N`
(change log count).

## Operation Flows

### Task operations

User intent → command mapping:

- "Add a task" → `tk add` (confirm description with the user)
- "Start working on X" → `tk status <id> in_progress`
- "X is ready for review" → `tk status <id> in_review`
- "Update next action" → `tk log <id> --summary "..." --next-action "..."` (history is preserved)
- "Update description" → `tk log <id> --summary "..." --description "..."`
- "Move X to the top" → `tk rank <id>`

#### When to use `in_review`

PR submitted / waiting on user / waiting on another team — i.e., no agent action needed.

#### Adding tasks from external sources

When creating a task from an external ticket, **always include the source content verbatim**
in the description (do not summarize). Reason: the Storage layer in the research literature
mandates preserving the raw form.

```
1. Fetch the description from the external source (JIRA, GitHub, ...)
2. Include structure, lists, and links verbatim in --description
3. Put the first step in --next-action
```

### Progress logging

1. `tk list --status in_progress` to find active tasks
2. `tk log <id> --summary "..." --details "..."`
3. If state changes, follow up with `tk status` / `tk log --next-action`

### Proactive logging

When to write without an explicit user instruction:

| Trigger | log | record |
|---------|-----|--------|
| On commit | ✅ `tk log` | ❌ (unless this commit is a milestone) |
| Design decision finalized | ✅ process in `--details` | ✅ `tk record add --kind decision --log-id <log>` |
| Investigation confirmed | ✅ process | ✅ `--kind finding` |
| Blocker appears | ✅ situation | ✅ (if future reference is likely) `--kind blocker` |
| Blocker resolved | ✅ resolution process | ✅ `tk record resolve <blocker_id>` |
| Failed attempt | ✅ | ❌ (attempts do not get promoted to records) |

**Decision order**: always write the log first → ask "is this worth re-reading next session?"
→ if yes, promote it to a record.

### Final record audit

Before the final response after any tk-tracked work, explicitly check whether this
turn created or changed durable typed memory:

1. Did this turn create, finalize, or materially change a design decision, policy,
   or constraint?
2. Did an investigation confirm a reusable fact that future sessions should know?
3. Did a blocker appear, resolve, or materially change?
4. Did this turn leave an explicit open question or operating hypothesis that future
   work should track?
5. Did any existing active record become outdated, need verification, or require a
   semantic replacement?

If yes to any item:

1. Ensure the relevant raw evidence exists in `tk log`.
2. Run `tk record list <task_id> --kind <X>` for the relevant kind before adding or
   changing typed memory.
3. Use `tk record add ... --log-id <log_id>` for new durable memory.
4. Use `tk record add ... --supersedes <old_id> --log-id <log_id>` for semantic
   replacements.
5. Use `tk record resolve`, `tk record obsolete`, or `tk record verify` when the
   existing record's lifecycle changed without new replacement content.

If no record action is needed after writing a meaningful `tk log`, internally note
the reason using the cardinality rule: most logs do not become records.

### Handling `[stale]`

When you see a `[stale]` marker:

1. `tk record show R-xxx` to inspect (add `--with-log` for the original process if needed)
2. **Still valid** → `tk record verify R-xxx`
3. **Outdated, no replacement** → `tk record obsolete R-xxx`
4. **Replacing with a new decision** → `tk log` for the process → `tk record add --supersedes R-xxx ...`

Do not destroy typed memory through continuous updates (research: "useful memories become
faulty when continuously updated"). For semantic changes, always use supersede.

## Configuration

`~/.config/tk/config.toml`:

```toml
db_path = "~/.local/share/tk/tasks.db"

[board]
done_retention_days = 14

[record]
stale_after_days = 30          # default

[record.active_warn]
decision = 10                  # default
blocker = 3                    # default
finding = 10                   # default
question = 10                  # default
hypothesis = 10                # default
```

Environment overrides: `TK_DB_PATH` (database path), `TK_CONFIG_PATH` (config file path).
