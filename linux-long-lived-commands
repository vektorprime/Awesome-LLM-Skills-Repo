---
name: linux-long-lived-commands
description: Use for running, managing, and inspecting Linux shell commands, especially commands that may take more than 2 seconds or keep running
---

Use Linux shell commands for file inspection, searching, process management, networking, compression, backups, package operations, and other command-line work.

Prefer direct shell commands for quick one-off tasks. Use `tmux` sessions for commands that are long-running, persistent, expensive, or likely to take more than a couple seconds.

Examples of long-running commands include recursive searches, large archive creation, backups, checksums over large files, package builds, log streaming, disk scans, data imports, and file synchronization.

## General shell usage

Run commands from the correct directory:

```bash
cd /path/to/project && make test
```

Check where you are before changing files:

```bash
pwd
ls -la
```

Inspect files without opening an interactive editor:

```bash
sed -n '1,160p' /etc/nginx/nginx.conf
head -n 80 /var/log/syslog
tail -n 100 /var/log/auth.log
```

Search files and directories efficiently:

```bash
grep -R "PermitRootLogin" /etc/ssh
find /var/log -type f -name "*.log" -mtime -7
```

Prefer commands that fail clearly. Do not hide errors unless there is a specific reason:

```bash
set -e
cd /repo
make build
make test
```

Use non-interactive flags when available:

```bash
apt-get update -y
rsync -a --delete /source/ /backup/source/
```

Avoid commands that require manual input, TTY attachment, curses interfaces, or interactive prompts unless the environment explicitly supports them.

## Long-running commands

Use `tmux` for commands that may take more than a couple seconds, keep running, or need to be inspected later.

Each long-running task should be a named `tmux` **session** that the agent can start, inspect, and stop from the shell.

Always use long, descriptive session names so other agents can understand what the task is for.

Before starting a new background session, always check whether an appropriate session already exists:

```bash
tmux ls
```

You can assume sessions without descriptive names were not started by you or other agents, so you can ignore them.

Start a long-running backup without blocking:

```bash
tmux new-session -d -s home-directory-rsync-backup-to-external-drive 'rsync -aHAX --info=progress2 /home/user/ /mnt/backup/home-user/'
```

Start a large archive creation task:

```bash
tmux new-session -d -s var-log-compression-gzip-archive 'tar -czf /tmp/var-log-backup.tar.gz /var/log'
```

Start a checksum over a large disk image:

```bash
tmux new-session -d -s ubuntu-image-sha256-checksum 'sha256sum /data/images/ubuntu-large-image.img'
```

Start a large recursive text search:

```bash
tmux new-session -d -s etc-recursive-ssh-config-search 'grep -R "PasswordAuthentication" /etc /usr/local/etc'
```

Start a filesystem usage scan:

```bash
tmux new-session -d -s filesystem-disk-usage-scan 'du -ah /var | sort -h | tail -n 200'
```

Start a long file synchronization job:

```bash
tmux new-session -d -s media-library-rsync-to-nas 'rsync -avh --progress /media/library/ nas:/backups/media-library/'
```

Start a package build:

```bash
tmux new-session -d -s linux-kernel-local-make-build 'cd /usr/src/linux && make -j$(nproc)'
```

Start a log-following task:

```bash
tmux new-session -d -s system-auth-log-follow 'tail -f /var/log/auth.log'
```

Do not attach to a session. The environment may be a non-TTY terminal. Inspect logs instead.

Fetch recent output from a task:

```bash
tmux capture-pane -t home-directory-rsync-backup-to-external-drive:0 -S -100 -p
```

Fetch more output when needed:

```bash
tmux capture-pane -t linux-kernel-local-make-build:0 -S -300 -p
```

List all background tasks:

```bash
tmux ls
```

Stop a background task when it is no longer needed:

```bash
tmux kill-session -t system-auth-log-follow
```

## Recommended agent workflow

1. Check the current directory and relevant files:

   ```bash
   pwd
   ls -la
   find . -maxdepth 2 -type f | head -n 100
   ```

2. Run quick commands directly:

   ```bash
   df -h
   free -h
   uname -a
   ```

3. Check for existing background sessions before starting a long-running command:

   ```bash
   tmux ls
   ```

4. Start long-running commands in descriptive `tmux` sessions:

   ```bash
   tmux new-session -d -s project-source-large-tar-backup 'tar -czf /tmp/project-source.tar.gz /repo/project'
   ```

5. Poll logs without attaching:

   ```bash
   tmux capture-pane -t project-source-large-tar-backup:0 -S -120 -p
   ```

6. Clean up sessions that are finished or no longer needed:

   ```bash
   tmux kill-session -t project-source-large-tar-backup
   ```

## Rules

- Use normal Linux shell commands for quick, one-shot tasks.
- Use `tmux` for long-running, persistent, expensive, or watch-mode tasks.
- Always check existing sessions before creating a new one.
- Always use descriptive session names.
- Never attach to a `tmux` session.
- Inspect `tmux` output with `capture-pane`.
- Clean up background sessions when they are no longer needed.
- Avoid interactive commands unless they are explicitly required and supported by the environment.
- Prefer explicit paths and clear working directories.
- Avoid destructive commands like `rm -rf`, `mkfs`, `dd`, or `shred` unless the user explicitly requests them and the target path has been verified.
