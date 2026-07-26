---
title: Git CLI Operations
description: Read this before working on anything git related. Complete operational reference for safely managing local and remote Git repositories hosted on github.com via git and gh CLI.

---

## Table of Contents

1. [Prerequisites & Setup](#1-prerequisites--setup)
2. [Safety Rules (Read First)](#2-safety-rules-read-first)
3. [Repository Cloning & Initialization](#3-repository-cloning--initialization)
4. [State Inspection (Always Do This First)](#4-state-inspection-always-do-this-first)
5. [Branching Operations](#5-branching-operations)
6. [Staging & Committing](#6-staging--committing)
7. [Pushing & Pulling](#7-pushing--pulling)
8. [Rebasing & History Rewriting](#8-rebasing--history-rewriting)
9. [Merge Conflict Resolution](#9-merge-conflict-resolution)
10. [Stashing](#10-stashing)
11. [Worktrees (Parallel Branch Work)](#11-worktrees-parallel-branch-work)
12. [Tags & Releases](#12-tags--releases)
13. [Remote Management](#13-remote-management)
14. [Pull Requests via gh CLI](#14-pull-requests-via-gh-cli)
15. [Issues via gh CLI](#15-issues-via-gh-cli)
16. [Recovery & Undo Operations](#16-recovery--undo-operations)
17. [Submodules](#17-submodules)
18. [Sparse Checkout & Partial Clone](#18-sparse-checkout--partial-clone)
19. [GitHub Actions & CI](#19-github-actions--ci)
20. [Common Pitfalls & LLM Guardrails](#20-common-pitfalls--llm-guardrails)
21. [Quick Reference: Decision Trees](#21-quick-reference-decision-trees)

---

## 1. Prerequisites & Setup

### Required Tools

| Tool | Check Version | Minimum |
|------|--------------|---------|
| `git` | `git --version` | 2.30+ |
| `gh` | `gh --version` | 2.0+ |

### Authentication

```bash
# Interactive login (browser-based OAuth)
gh auth login

# Token-based (CI/automation)
echo "$GITHUB_TOKEN" | gh auth login --with-token

# Verify auth status
gh auth status

# Configure git to use gh for credential handling
gh auth setup-git
```

### Essential Git Configuration

```bash
# Identity (REQUIRED before committing)
git config --global user.name "Your Name"
git config --global user.email "you@example.com"

# Safety defaults
git config --global init.defaultBranch main
git config --global pull.rebase false        # explicit merge on pull
git config --global push.autoSetupRemote true # auto-set upstream on first push
git config --global core.editor "nano"       # or preferred editor
git config --global rerere.enabled true      # remember conflict resolutions

# Useful aliases
git config --global alias.st "status -sb"
git config --global alias.lg "log --oneline --graph --decorate --all -20"
git config --global alias.last "log -1 HEAD --stat"
git config --global alias.unstage "reset HEAD --"
```

---

## 2. Safety Rules (Read First)

### 🔴 NEVER Do These Without Explicit Confirmation

| Action | Why It's Dangerous |
|--------|-------------------|
| `git push --force` / `git push -f` | Overwrites remote history; can destroy teammates' work |
| `git reset --hard` (on shared branches) | Discards uncommitted changes permanently |
| `git rebase` (on shared/public branches) | Rewrites history others may be based on |
| `git clean -fdx` | Deletes ALL untracked files including `.env`, build artifacts |
| `git branch -D` | Force-deletes branch even if unmerged |
| `git checkout -- .` | Discards ALL working directory changes |
| `git push origin --delete <branch>` | Deletes remote branch |
| `gh pr merge --admin` | Bypasses required checks |
| `git filter-branch` / `git filter-repo` | Rewrites entire repo history |

### 🟡 Always Do Before Destructive Operations

1. **Check status:** `git status`
2. **Check what branch you're on:** `git branch --show-current`
3. **Check for uncommitted changes:** `git diff --stat` and `git diff --cached --stat`
4. **Verify remote state:** `git fetch --dry-run`
5. **Confirm the branch is not shared:** `git log --oneline origin/<branch>..HEAD`

### 🟢 Safe Defaults for LLMs

- **Always use `--force-with-lease` instead of `--force`** when pushing rebased branches.
- **Always create a backup branch** before rebasing: `git branch backup/<branch-name>`.
- **Never rebase a branch that others are working on.**
- **Prefer `git revert` over `git reset`** on shared branches.
- **Use `git stash` instead of discarding** when unsure.
- **Commit early, commit often** — small commits are easier to undo.

---

## 3. Repository Cloning & Initialization

### Clone from GitHub

```bash
# HTTPS (recommended with gh auth)
gh repo clone owner/repo

# Or explicit git
git clone https://github.com/owner/repo.git

# SSH
git clone git@github.com:owner/repo.git

# Shallow clone (latest history only — good for CI or quick inspection)
git clone --depth 1 https://github.com/owner/repo.git

# Clone specific branch
git clone --branch feature/x --single-branch https://github.com/owner/repo.git

# Clone with submodules
git clone --recurse-submodules https://github.com/owner/repo.git

# Bare clone (for worktree-based workflows)
git clone --bare https://github.com/owner/repo.git repo.git
```

### Initialize New Repository

```bash
mkdir my-project && cd my-project
git init -b main
git remote add origin https://github.com/owner/repo.git

# Or create on GitHub and clone
gh repo create owner/repo --private --clone
```

### Fork Workflow

```bash
# Fork and clone in one step
gh repo fork owner/repo --clone --remote

# This gives you:
#   origin    → your fork
#   upstream  → original repo
```

---

## 4. State Inspection (Always Do This First)

### Before ANY operation, run these:

```bash
# Where am I? What's the state?
git status

# What branch am I on?
git branch --show-current

# What's changed (unstaged)?
git diff --stat

# What's staged?
git diff --cached --stat

# Recent history
git log --oneline -10

# Relationship to remote
git rev-list --left-right --count origin/main...HEAD
# Output: <behind>\t<ahead>

# All branches (local + remote)
git branch -a

# Remotes
git remote -v
```

### Understanding `git status` Output

```
On branch feature/auth
Your branch is ahead of 'origin/feature/auth' by 2 commits.

Changes to be committed:        ← STAGED (will be in next commit)
  modified:   src/auth.ts

Changes not staged for commit:  ← MODIFIED but not staged
  modified:   src/utils.ts

Untracked files:                ← NEW files, not yet tracked
  src/newfile.ts
```

---

## 5. Branching Operations

### List Branches

```bash
git branch                    # local branches
git branch -r                 # remote-tracking branches
git branch -a                 # all branches
git branch -v                 # with last commit
git branch --merged main      # branches already merged into main
git branch --no-merged main   # branches NOT yet merged
```

### Create Branches

```bash
# From current HEAD
git branch feature/new-thing

# From a specific base
git branch feature/new-thing origin/main

# Create AND switch
git checkout -b feature/new-thing origin/main
# Or (modern):
git switch -c feature/new-thing origin/main

# Orphan branch (no history — for gh-pages, etc.)
git checkout --orphan gh-pages
git rm -rf .
```

### Switch Branches

```bash
git switch main               # modern (preferred)
git checkout main             # classic

# Switch and discard local changes (DANGEROUS)
git checkout -f main

# Detached HEAD at specific commit
git checkout abc1234
# Or:
git switch --detach abc1234
```

### Delete Branches

```bash
# Safe delete (refuses if unmerged)
git branch -d feature/done

# Force delete (DANGEROUS — loses unmerged commits)
git branch -D feature/abandoned

# Delete remote branch
git push origin --delete feature/done
# Or:
gh api -X DELETE repos/owner/repo/git/refs/heads/feature/done
```

### Rename Branch

```bash
# Rename current branch
git branch -m new-name

# Rename specific branch
git branch -m old-name new-name

# Update remote after rename
git push origin --delete old-name
git push origin -u new-name
```

### Branch Naming Conventions

```
feature/<ticket-id>-<short-description>
bugfix/<ticket-id>-<short-description>
hotfix/<version>-<description>
release/<version>
chore/<description>
docs/<description>
experiment/<description>
```

---

## 6. Staging & Committing

### Staging

```bash
# Stage specific file
git add src/auth.ts

# Stage directory
git add src/

# Stage all changes (tracked files)
git add -u

# Stage everything (including untracked)
git add -A

# Interactive staging (hunk-by-hunk)
git add -p

# Unstage (keep changes in working dir)
git restore --staged src/auth.ts
# Or:
git reset HEAD src/auth.ts
```

### Committing

```bash
# Standard commit
git commit -m "feat(auth): add JWT token refresh"

# Commit with body
git commit -m "fix(api): handle null response" -m "The upstream API can return
null when the user has no profile. This adds a guard clause."

# Amend last commit (ONLY if not pushed)
git commit --amend -m "feat(auth): add JWT token refresh (correct message)"

# Amend without changing message
git commit --amend --no-edit

# Commit all tracked changes (skip staging)
git commit -am "chore: update dependencies"

# Empty commit (for triggering CI)
git commit --allow-empty -m "ci: trigger rebuild"
```

### Commit Message Convention (Conventional Commits)

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

### Viewing History

```bash
# Compact log
git log --oneline -20

# Graph view
git log --oneline --graph --decorate --all -30

# Specific file history
git log --follow -p -- src/auth.ts

# Who changed what
git blame src/auth.ts

# Search commit messages
git log --grep="auth" --oneline

# Commits by author
git log --author="jane" --oneline

# Commits between dates
git log --since="2024-01-01" --until="2024-02-01" --oneline

# What changed between two refs
git log v1.0..v2.0 --oneline

# Diff between commits
git diff abc1234..def5678 --stat
```

---

## 7. Pushing & Pulling

### Pushing

```bash
# Push current branch (with upstream tracking)
git push -u origin feature/auth

# Subsequent pushes (upstream already set)
git push

# Push specific branch
git push origin feature/auth

# Push tags
git push origin v1.0.0
git push origin --tags

# Safe force push (respects others' pushes)
git push --force-with-lease origin feature/auth

# DANGEROUS: absolute force push
git push --force origin feature/auth

# Dry run (see what would happen)
git push --dry-run origin feature/auth
```

### Pulling

```bash
# Pull with merge (default)
git pull origin main

# Pull with rebase (cleaner history)
git pull --rebase origin main

# Fetch only (no merge — safest)
git fetch origin
git merge origin/main    # then merge manually

# Fetch all remotes
git fetch --all --prune

# Pull specific branch
git pull origin feature/auth
```

### Fetch vs Pull

| Command | What It Does |
|---------|-------------|
| `git fetch` | Downloads remote changes, updates remote-tracking branches. **Does NOT modify working tree.** |
| `git pull` | `fetch` + `merge` (or `fetch` + `rebase` with `--rebase`). **Modifies working tree.** |

**LLM Rule:** Prefer `git fetch` + inspect + `git merge` over blind `git pull`.

---

## 8. Rebasing & History Rewriting

### ⚠️ Golden Rule of Rebasing

> **Never rebase a branch that has been pushed and is being used by others.**
> Rebase rewrites commit hashes. Anyone based on the old commits will have conflicts.

### Interactive Rebase

```bash
# Rebase last 5 commits
git rebase -i HEAD~5

# Rebase onto main
git rebase -i origin/main

# Rebase specific range
git rebase -i abc1234..def5678
```

### Rebase Actions (in editor)

| Action | Effect |
|--------|--------|
| `pick` | Keep commit as-is |
| `reword` | Keep commit, edit message |
| `edit` | Pause to amend commit |
| `squash` | Merge into previous, combine messages |
| `fixup` | Merge into previous, discard message |
| `drop` | Remove commit entirely |
| `exec` | Run shell command |

### Safe Rebase Workflow

```bash
# 1. Create backup
git branch backup/feature-auth

# 2. Fetch latest
git fetch origin

# 3. Rebase
git rebase origin/main

# 4. If conflicts, resolve them (see §9)

# 5. Force push with lease
git push --force-with-lease origin feature/auth

# 6. If something went wrong, restore backup
git rebase --abort          # if still in progress
git reset --hard backup/feature-auth  # if completed badly
```

### Rebase vs Merge Decision

| Scenario | Use |
|----------|-----|
| Updating feature branch with latest main | `git rebase origin/main` |
| Integrating feature into main | `git merge --no-ff feature/x` (or PR) |
| Shared/collaborative branch | `git merge` (never rebase) |
| Cleaning up local commits before PR | `git rebase -i` |

---

## 9. Merge Conflict Resolution

### When Conflicts Occur

```bash
# Attempt merge
git merge feature/auth

# Git reports:
# CONFLICT (content): Merge conflict in src/auth.ts
# Automatic merge failed; fix conflicts and then commit the result.
```

### Resolution Workflow

```bash
# 1. See conflicted files
git status
# or:
git diff --name-only --diff-filter=U

# 2. Open conflicted file — look for markers:
# <<<<<<< HEAD
# your current code
# =======
# incoming code from feature branch
# >>>>>>> feature/auth

# 3. Edit file to resolve (remove markers, keep correct code)

# 4. Stage resolved file
git add src/auth.ts

# 5. Continue merge
git commit
# Or for rebase:
git rebase --continue

# Abort entirely if needed
git merge --abort
git rebase --abort
```

### Conflict Resolution Strategies

```bash
# Accept all changes from "ours" (current branch)
git checkout --ours src/auth.ts
git add src/auth.ts

# Accept all changes from "theirs" (incoming)
git checkout --theirs src/auth.ts
git add src/auth.ts

# Use a merge tool
git mergetool

# See the three versions (base, ours, theirs)
git show :1:src/auth.ts  # base
git show :2:src/auth.ts  # ours
git show :3:src/auth.ts  # theirs
```

### Preventing Conflicts

```bash
# Enable rerere (reuse recorded resolution)
git config --global rerere.enabled true

# Before merging, check what will conflict
git merge --no-commit --no-ff feature/auth
git diff --cached
git merge --abort
```

---

## 10. Stashing

### Basic Operations

```bash
# Stash all changes (tracked files)
git stash push -m "WIP: auth refactor"

# Stash including untracked files
git stash push -u -m "WIP: new files too"

# Stash everything (including ignored)
git stash push -a -m "WIP: all changes"

# Stash specific files
git stash push -m "partial" -- src/auth.ts src/utils.ts

# List stashes
git stash list

# View stash contents
git stash show -p stash@{0}

# Apply stash (keep in list)
git stash apply stash@{0}

# Pop stash (apply and remove from list)
git stash pop stash@{0}

# Drop a stash
git stash drop stash@{0}

# Clear all stashes
git stash clear
```

### Stash Workflow for Context Switching

```bash
# Interrupted by urgent fix:
git stash push -m "WIP: feature/auth - token refresh"
git switch -c hotfix/login-crash origin/main
# ... fix, commit, push, PR ...
git switch feature/auth
git stash pop
```

### ⚠️ Stash Pitfalls

- Stashes are **not** branch-specific — they apply to any branch.
- `git stash pop` can fail with conflicts — use `apply` first to test.
- Stashes don't survive `git clone` — they're local only.
- In worktrees, stashes are **shared** across all worktrees of the same repo.

---

## 11. Worktrees (Parallel Branch Work)

### Why Worktrees?

Worktrees let you check out multiple branches simultaneously in separate directories,
sharing one `.git` database. No stashing, no cloning, no context loss.

### Core Commands

```bash
# Create worktree for existing branch
git worktree add ../project-hotfix hotfix/login

# Create worktree with NEW branch
git worktree add -b feature/new-api ../project-new-api origin/main

# Detached HEAD worktree (for inspection/testing)
git worktree add --detach ../project-review abc1234

# List all worktrees
git worktree list

# Remove worktree (must be clean)
git worktree remove ../project-hotfix

# Force remove (discards changes)
git worktree remove --force ../project-hotfix

# Prune stale worktree metadata
git worktree prune

# Lock worktree (prevent pruning on removable media)
git worktree lock ../project-usb --reason "external drive"

# Unlock
git worktree unlock ../project-usb

# Move worktree
git worktree move ../old-path ../new-path

# Repair after manual moves
git worktree repair
```

### Worktree Workflow: Hotfix During Feature Work

```bash
# You're deep in feature/auth with 20 changed files
# Production bug reported!

# Create hotfix worktree from main
git worktree add -b hotfix/critical ../project-hotfix origin/main

# Work in the hotfix directory
cd ../project-hotfix
# ... fix, test, commit, push ...
git push -u origin hotfix/critical
gh pr create --title "Hotfix: critical login bug" --body "..."

# Return to feature work (untouched!)
cd ../project
# All your feature work is exactly as you left it

# Cleanup after hotfix merged
git worktree remove ../project-hotfix
git branch -d hotfix/critical
```

### Worktree Rules

- A branch can only be checked out in **one** worktree at a time.
- The main worktree cannot be removed.
- Each worktree has its own index (staging area) but shares refs and objects.
- Stashes are shared across worktrees.
- Git hooks are shared (they live in the main `.git/hooks`).

### Directory Layout Convention

```
~/projects/
├── my-app/              ← main worktree (feature branch)
├── my-app-hotfix/       ← hotfix worktree
├── my-app-review/       ← PR review worktree
└── my-app-release/      ← release branch worktree
```

---

## 12. Tags & Releases

### Tags

```bash
# List tags
git tag
git tag -l "v1.*"

# Create annotated tag
git tag -a v1.2.0 -m "Release version 1.2.0"

# Create lightweight tag
git tag v1.2.0

# Tag a specific commit
git tag -a v1.1.0 -m "Release 1.1.0" abc1234

# Push tag
git push origin v1.2.0
git push origin --tags

# Delete tag
git tag -d v1.2.0                    # local
git push origin --delete v1.2.0      # remote

# View tag details
git show v1.2.0
```

### Releases (via gh)

```bash
# Create release from tag
gh release create v1.2.0 \
  --title "Release 1.2.0" \
  --notes "## Changes\n- Feature A\n- Bug fix B"

# Create release with auto-generated notes
gh release create v1.2.0 --generate-notes

# Create draft release
gh release create v1.2.0 --draft --title "Upcoming Release"

# Upload assets
gh release create v1.2.0 ./dist/app-linux.tar.gz ./dist/app-macos.zip

# List releases
gh release list

# View release
gh release view v1.2.0

# Download release assets
gh release download v1.2.0

# Delete release
gh release delete v1.2.0 --yes
```

---

## 13. Remote Management

### Viewing Remotes

```bash
git remote -v
# origin    https://github.com/owner/repo.git (fetch)
# origin    https://github.com/owner/repo.git (push)
# upstream  https://github.com/original/repo.git (fetch)
# upstream  https://github.com/original/repo.git (push)
```

### Adding/Modifying Remotes

```bash
# Add remote
git remote add upstream https://github.com/original/repo.git

# Rename remote
git remote rename origin old-origin

# Change remote URL
git remote set-url origin https://github.com/owner/new-repo.git

# Remove remote
git remote remove upstream

# Set upstream for current branch
git branch --set-upstream-to=origin/feature/auth
```

### Fork Sync Workflow

```bash
# Add upstream (if not already)
git remote add upstream https://github.com/original/repo.git

# Sync your fork's main with upstream
git fetch upstream
git checkout main
git merge upstream/main
git push origin main

# Or use gh:
gh repo sync owner/repo --source original/repo
```

---

## 14. Pull Requests via gh CLI

### Creating PRs

```bash
# Interactive creation
gh pr create

# Non-interactive
gh pr create \
  --title "feat(auth): add JWT refresh" \
  --body "Implements token refresh flow.\n\nCloses #42" \
  --base main \
  --head feature/auth \
  --reviewer jane,team-backend \
  --label "enhancement" \
  --assignee "@me"

# Draft PR
gh pr create --draft --title "WIP: new API" --body "Not ready for review"

# Fill from commits
gh pr create --fill

# From file
gh pr create --body-file ./pr-description.md
```

### Managing PRs

```bash
# List open PRs
gh pr list

# View PR
gh pr view 42
gh pr view 42 --web

# Check out PR locally
gh pr checkout 42

# View PR diff
gh pr diff 42

# Check CI status
gh pr checks 42
gh pr checks 42 --watch

# Edit PR
gh pr edit 42 --title "New title" --add-label "priority"

# Mark ready for review
gh pr ready 42

# Convert back to draft
gh pr ready 42 --undo
```

### Reviewing PRs

```bash
# Approve
gh pr review 42 --approve --body "LGTM!"

# Request changes
gh pr review 42 --request-changes --body "Please fix the null check on line 42"

# Comment
gh pr review 42 --comment --body "Have you considered using a mutex here?"
```

### Merging PRs

```bash
# Squash merge (most common)
gh pr merge 42 --squash --delete-branch

# Merge commit
gh pr merge 42 --merge --delete-branch

# Rebase merge
gh pr merge 42 --rebase --delete-branch

# Auto-merge when checks pass
gh pr merge 42 --squash --auto

# Disable auto-merge
gh pr merge 42 --disable-auto
```

### PR Maintenance

```bash
# Update PR branch with latest base
gh pr update-branch 42
gh pr update-branch 42 --rebase

# Close PR
gh pr close 42 --comment "Superseded by #50" --delete-branch

# Reopen PR
gh pr reopen 42
```

---

## 15. Issues via gh CLI

```bash
# Create issue
gh issue create --title "Bug: login fails" --body "Steps to reproduce..." \
  --label "bug" --assignee "@me"

# List issues
gh issue list --label "bug" --state open

# View issue
gh issue view 42

# Close issue
gh issue close 42 --comment "Fixed in abc1234" --reason completed

# Comment on issue
gh issue comment 42 --body "I can reproduce this on v2.1"

# Develop (create linked branch)
gh issue develop 42 --checkout
```

---

## 16. Recovery & Undo Operations

### Undo Last Commit (Keep Changes)

```bash
# Soft reset — changes stay staged
git reset --soft HEAD~1

# Mixed reset (default) — changes stay in working dir, unstaged
git reset HEAD~1

# Hard reset — DISCARDS changes (DANGEROUS)
git reset --hard HEAD~1
```

### Undo a Pushed Commit (Safe)

```bash
# Revert creates a NEW commit that undoes the changes
git revert abc1234
git push origin main

# Revert a merge commit
git revert -m 1 <merge-commit-sha>
```

### Recover Lost Commits

```bash
# Find lost commits via reflog
git reflog
# Look for the SHA of the lost commit

# Restore to a branch
git branch recovered-branch abc1234

# Or reset to it
git reset --hard abc1234
```

### Undo a Merge

```bash
# If merge not yet pushed:
git reset --hard ORIG_HEAD

# If merge already pushed:
git revert -m 1 <merge-commit>

# If in the middle of a conflicted merge:
git merge --abort
```

### Undo a Rebase

```bash
# If rebase in progress:
git rebase --abort

# If rebase completed:
git reflog
# Find the pre-rebase SHA
git reset --hard <pre-rebase-sha>

# Or use backup branch (if you made one):
git reset --hard backup/feature-auth
```

### Recover Deleted Branch

```bash
# Find the tip commit via reflog
git reflog
# Or:
git log --all --oneline

# Recreate branch
git branch recovered-branch <sha>
```

### Recover Dropped Stash

```bash
# Stashes are commits — find them:
git fsck --no-reflog | grep commit
git log --oneline --no-walk <sha>

# Apply recovered stash
git stash apply <sha>
```

### Nuclear Option: Fix Corrupted Repo

```bash
# Verify integrity
git fsck --full

# Re-clone if truly broken
git clone https://github.com/owner/repo.git repo-fresh
```

---

## 17. Submodules

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/owner/repo.git

# Initialize submodules after clone
git submodule update --init --recursive

# Update submodules to latest
git submodule update --remote --recursive

# Add submodule
git submodule add https://github.com/lib/dependency.git libs/dependency

# Remove submodule
git submodule deinit libs/dependency
git rm libs/dependency
rm -rf .git/modules/libs/dependency

# Check submodule status
git submodule status

# Commit submodule pointer change
cd libs/dependency
git checkout main && git pull
cd ../..
git add libs/dependency
git commit -m "chore: update dependency submodule"
```

---

## 18. Sparse Checkout & Partial Clone

### Partial Clone (Blobless)

```bash
# Clone without file contents (downloads on demand)
git clone --filter=blob:none https://github.com/owner/repo.git

# Treeless clone (even more minimal)
git clone --filter=tree:0 https://github.com/owner/repo.git
```

### Sparse Checkout

```bash
# Enable sparse checkout
git sparse-checkout init --cone

# Only check out specific directories
git sparse-checkout set src/auth src/api

# Add more directories
git sparse-checkout add docs/

# View current sparse patterns
git sparse-checkout list

# Disable sparse checkout
git sparse-checkout disable
```

---

## 19. GitHub Actions & CI

### Viewing Workflow Runs

```bash
# List recent runs
gh run list --limit 10

# View specific run
gh run view 12345

# View failed run logs
gh run view 12345 --log-failed

# Watch run in progress
gh run watch 12345

# List workflows
gh workflow list

# Trigger workflow manually
gh workflow run deploy.yml --ref main -f environment=staging

# Re-run failed jobs
gh run rerun 12345 --failed

# Cancel a run
gh run cancel 12345
```

### Check PR CI Status

```bash
gh pr checks 42
gh pr checks 42 --watch --fail-fast
```

---

## 20. Common Pitfalls & LLM Guardrails

### Pitfall: Detached HEAD

```bash
# Symptom: "You are in 'detached HEAD' state"
# Cause: Checked out a commit/tag instead of a branch

# Fix: Create a branch from current position
git switch -c feature/from-detached

# Or go back:
git switch main
```

### Pitfall: Push Rejected (Non-Fast-Forward)

```bash
# Error: "Updates were rejected because the tip of your current branch is behind"

# SAFE fix:
git fetch origin
git rebase origin/main
git push --force-with-lease

# OR (if you prefer merge):
git pull --rebase origin main
git push
```

### Pitfall: Accidentally Committed to Wrong Branch

```bash
# Move last commit to correct branch:
git reset --soft HEAD~1
git stash
git switch correct-branch
git stash pop
git add -A
git commit -m "original message"
```

### Pitfall: Large Files in History

```bash
# Check for large files
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  sort -k3 -n -r | head -20

# Remove from history (use git-filter-repo, not filter-branch)
pip install git-filter-repo
git filter-repo --strip-blobs-bigger-than 10M
```

### Pitfall: Line Ending Issues (Windows/Mac/Linux)

```bash
# Check current setting
git config core.autocrlf

# Recommended settings:
# Linux/Mac:
git config --global core.autocrlf input
# Windows:
git config --global core.autocrlf true

# Fix existing files
git rm --cached -r .
git reset --hard
```

### LLM-Specific Guardrails

| Rule | Rationale |
|------|-----------|
| Always run `git status` before any mutation | Know your starting state |
| Never `git push --force` without `--force-with-lease` | Protects against overwriting others' work |
| Create backup branch before rebase | `git branch backup/x` is free insurance |
| Prefer `git revert` on shared branches | Non-destructive undo |
| Use `git fetch` + inspect before `git merge` | Avoid surprise conflicts |
| Never `git clean -fdx` without checking `.gitignore` | May delete `.env`, credentials |
| Commit before switching branches | Prevents lost work |
| Use `--no-edit` flags in automation | Avoids hanging on editor prompts |
| Set `GIT_TERMINAL_PROMPT=0` in scripts | Prevents interactive hangs |
| Check `git branch --show-current` before push | Push to wrong branch = disaster |

### Environment Variables for Automation

```bash
export GIT_TERMINAL_PROMPT=0        # Never prompt interactively
export GIT_MERGE_AUTOEDIT=no        # Don't open editor for merge messages
export GIT_EDITOR=true              # Auto-accept editor prompts
export GH_PROMPT_DISABLED=true      # Disable gh interactive prompts
```

---

## 21. Quick Reference: Decision Trees

### "I need to update my feature branch with latest main"

```
Is the branch shared with others?
├── YES → git fetch origin && git merge origin/main
└── NO  → git fetch origin && git rebase origin/main
           └── Conflicts? → Resolve → git rebase --continue
           └── Done? → git push --force-with-lease
```

### "I made a mistake in my last commit"

```
Is it pushed to a shared branch?
├── YES → git revert HEAD && git push
└── NO  → Is it just the message?
          ├── YES → git commit --amend -m "new message"
          └── NO  → git reset --soft HEAD~1
                     └── Fix files → git add → git commit
```

### "I need to work on something urgent"

```
Do you have uncommitted changes?
├── YES → Is it quick (< 5 min)?
│         ├── YES → git stash push -m "WIP" → fix → git stash pop
│         └── NO  → git worktree add -b hotfix ../hotfix origin/main
│                    └── cd ../hotfix → fix → commit → push → PR
│                    └── cd back → git worktree remove ../hotfix
└── NO  → git switch -c hotfix origin/main → fix → push → PR
```

### "I need to undo something"

```
What happened?
├── Bad commit (not pushed)     → git reset --soft HEAD~1
├── Bad commit (pushed, shared) → git revert <sha>
├── Bad merge (not pushed)      → git reset --hard ORIG_HEAD
├── Bad merge (pushed)          → git revert -m 1 <merge-sha>
├── Bad rebase                  → git reflog → git reset --hard <pre-rebase>
├── Deleted branch              → git reflog → git branch recovered <sha>
├── Lost changes (never committed) → UNRECOVERABLE (check editor backups)
└── In-progress conflict        → git merge --abort / git rebase --abort
```

### "I need to review a PR locally"

```bash
gh pr checkout 42
# Or without gh:
git fetch origin pull/42/head:pr-42
git switch pr-42

# For worktree-based review (don't disturb current work):
git fetch origin pull/42/head:pr-42
git worktree add ../review-pr-42 pr-42
cd ../review-pr-42
# ... review, test ...
cd -
git worktree remove ../review-pr-42
git branch -d pr-42
```

---

## Appendix A: Useful One-Liners

```bash
# Current branch name
git branch --show-current

# Is working tree clean?
git status --porcelain | wc -l  # 0 = clean

# Commits ahead/behind remote
git rev-list --left-right --count origin/main...HEAD

# Last commit SHA
git rev-parse HEAD

# Last commit short SHA
git rev-parse --short HEAD

# Repo root directory
git rev-parse --show-toplevel

# Default branch name
git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'

# All files changed in last commit
git diff-tree --no-commit-id --name-only -r HEAD

# Undo all uncommitted changes (DANGEROUS)
git checkout -- .
git clean -fd

# Size of .git directory
du -sh .git

# Find which commit introduced a string
git log -S "function_name" --oneline

# Cherry-pick a commit
git cherry-pick abc1234

# Cherry-pick without committing
git cherry-pick --no-commit abc1234

# See what a merge would do (without merging)
git merge --no-commit --no-ff feature/x && git diff --cached && git merge --abort
```

## Appendix B: gh CLI JSON Output (for Scripting)

```bash
# Get PR info as JSON
gh pr view 42 --json title,state,headRefName,baseRefName,mergeable

# List PRs as JSON
gh pr list --json number,title,author --jq '.[] | "\(.number) \(.title)"'

# Get repo default branch
gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'

# Get latest release tag
gh release view --json tagName --jq '.tagName'

# Check if PR is mergeable
gh pr view 42 --json mergeable --jq '.mergeable'
# Returns: MERGEABLE | CONFLICTING | UNKNOWN
```

## Appendix C: Emergency Cheat Sheet

| Situation | Command |
|-----------|---------|
| Everything is on fire, abort current operation | `git merge --abort` or `git rebase --abort` or `git cherry-pick --abort` |
| I don't know what state I'm in | `git status && git log --oneline -5 && git branch -vv` |
| I lost a commit | `git reflog` → find SHA → `git branch recovery <sha>` |
| I committed to wrong branch | `git reset --soft HEAD~1` → `git stash` → switch → `git stash pop` |
| Remote is ahead of me | `git fetch origin` → `git rebase origin/main` |
| I accidentally deleted a branch | `git reflog` → `git branch <name> <sha>` |
| Merge conflict and I'm stuck | `git merge --abort` (start over) |
| I need to completely start fresh | `git fetch origin && git reset --hard origin/main` (DESTRUCTIVE) |
| Push rejected after rebase | `git push --force-with-lease` |
| I need to undo the last push | `git revert HEAD && git push` (safe) |

---

