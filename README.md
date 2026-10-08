# tasukura-skills

Agent skills for [tasukura](https://github.com/mixidota2/tasukura), the local task
management CLI. The [`tk` skill](skills/tk/SKILL.md) covers tasks, progress logs, and
typed records such as decisions, findings, and blockers.

This repository contains the skill instructions. Install the `tasukura` CLI
separately; no task database, user configuration, or CLI implementation is bundled.

## Install

### 1. Install the CLI

Python 3.11 or later is required. This skill targets tasukura 0.1.7 or later.

```bash
uv tool install 'tasukura>=0.1.7'
# Alternatively: pip install 'tasukura>=0.1.7'
tk --help
```

### 2. Clone this repository

```bash
git clone https://github.com/mixidota2/tasukura-skills.git
cd tasukura-skills
```

Keep the checkout at a stable path when using a symlink.

### 3. Install the skill for your agent

Run the appropriate commands from the `tasukura-skills` checkout.

**Claude Code** ([skill locations](https://code.claude.com/docs/en/skills)):

```bash
mkdir -p "$HOME/.claude/skills"
test ! -e "$HOME/.claude/skills/tk" && \
  test ! -L "$HOME/.claude/skills/tk" && \
  ln -s "$PWD/skills/tk" "$HOME/.claude/skills/tk"
```

**Codex** ([skill locations](https://learn.chatgpt.com/docs/build-skills)):

```bash
mkdir -p "$HOME/.agents/skills"
test ! -e "$HOME/.agents/skills/tk" && \
  test ! -L "$HOME/.agents/skills/tk" && \
  ln -s "$PWD/skills/tk" "$HOME/.agents/skills/tk"
```

If the destination already exists, stop and inspect it before installing. For an
existing installation from the CLI repository, follow the migration section below.
If symlinks are unavailable, copy the `skills/tk` directory to the corresponding
agent's skills directory instead. A copied installation needs to be copied again
after an update.

Start a new agent session and select the `tk` skill. In Claude Code it is `/tk`;
in Codex it is `$tk`. The skill can also be discovered automatically for relevant
requests. Separate `/task` and `/progress` commands are not included.

## Migrate an existing installation

An older installation may link `~/.claude/skills/tk` to `tasukura/skills`.
Inspect the current link or directory first:

```bash
ls -ld "$HOME/.claude/skills/tk"
```

Move the existing installation to an unused backup path, then create the new link.
These commands stop if the destination or backup would be overwritten:

```bash
(
  set -eu
  test -f "$PWD/skills/tk/SKILL.md"
  old="$HOME/.claude/skills/tk"
  backup="$HOME/.claude/skill-backups/tk.before-tasukura-skills"
  test -e "$old" || test -L "$old"
  test ! -e "$backup"
  test ! -L "$backup"
  mkdir -p "$(dirname "$backup")"
  if test -L "$old"; then
    target=$(readlink "$old")
    case "$target" in
      /*) ;;
      *) target="$(dirname "$old")/$target" ;;
    esac
    ln -s "$target" "$backup"
    rm "$old"
  else
    mv "$old" "$backup"
  fi
  ln -s "$PWD/skills/tk" "$old"
)
```

Run this from the new checkout. Backups stay outside the agent's active skills
directory, and relative symlinks are rebased so the backup still resolves to the
original target. If the backup already exists, inspect it and choose another unused
backup path. For Codex, substitute `.agents` for `.claude`.
Neither this migration nor installing the skill changes tasukura's database or
configuration. Keep any local skill customizations in the backup until reviewed.

## Update

```bash
git pull --ff-only
```

Symlinked installations follow the checkout automatically. Updating the skill does
not update the CLI; manage the CLI separately with your chosen package installer.

## Development and checks

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Checks cover skill metadata, portable paths, local links, and installation layout.
Changes to CLI commands should also be checked against the corresponding
[tasukura release](https://github.com/mixidota2/tasukura/releases).

## Origin and license

Extracted from [`mixidota2/tasukura`, commit `37ca372`](https://github.com/mixidota2/tasukura/tree/37ca3720b93743c20e264b6b94a4c6a29d0424c5),
originally `skills/SKILL.md`. The task and typed-record workflows are preserved;
installation prerequisites and standalone invocation are clarified for this repository.

[MIT](LICENSE), copyright 2026 mixidota2.
