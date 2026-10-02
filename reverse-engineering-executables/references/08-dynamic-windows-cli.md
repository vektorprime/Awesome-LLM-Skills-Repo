# 08 — Dynamic Analysis on Windows (CLI)

Requires completed execution gate from `SKILL.md` + test plan in `checklists/dynamic-test-plan-template.md`. Disposable Windows VM, snapshot, no prod net.

## 1. Debugger launch (CDB / WinDbg)

```bat
cdb -o -logo cdb.log sample.exe arg1 arg2
```

Inside:

```text
.symfix
.reload
lm
x sample!*
bu kernel32!CreateFileW
bu ws2_32!connect
g
k
r
u @rip-20 @rip+40
dq @rsp L20
```

Rules:

- Use `bu` (unresolved) for not-yet-loaded DLLs. `bp` on unloaded module silently misses.
- APIs forward: `kernel32!CreateFileW` → `KernelBase`, `ws2_32!connect` via API sets. Confirm with `x *!connect` + `ln @rip` at hit.
- Dereference Windows strings as UTF-16: `du poi(@rcx)` for arg1 (see `07-...`). `da` gives garbage on wide strings.
- ASLR/relocation: never hardcode absolute VA from static. Compute `runtime = module_base + RVA` after `lm` shows base.

Scripted hits (save as `commands.txt`, preserve with case):

```text
.symfix
.reload
sxe av
bu kernel32!CreateProcessW ".printf \"CreateProcessW hit\\n\"; k; dv; g"
bu ws2_32!connect ".printf \"connect hit\\n\"; k; db @rdx L16; g"
g
```

The `db @rdx L16` dump decodes as `sockaddr`: first 2 bytes = address family (`02 00` = AF_INET), next 2 = port in **network (big-endian) order**, next 4 = IPv4 address. `rdx` is the `sockaddr*` itself — dumping it as a string (`du`) yields garbage.

Run with the installed CDB `-cf commands.txt` variant (check `cdb -h` — options drift). Save log + command file.

## 2. DLL specifics

- `rundll32 sample.dll,Export arg` or `regsvr32 /s sample.dll` for DLL entry. Log exact command line — it changes `DllMain` path.
- Break on `sample!DllMain` first; `DLL_PROCESS_ATTACH` reason is in 2nd arg (`rdx==1` — `DllMain(hinst=rcx, reason=rdx, lpReserved=r8)`).
- No exports on a DLL → loader still calls `DllMain`. Don't conclude "nothing to run".

## 3. ProcMon headless (file/reg/proc truth)

```bat
procmon.exe /BackingFile C:\cases\run-001.pml /Quiet /Minimized
sample.exe arg1
procmon.exe /Terminate
```

Filter to PID + `CreateFile/WriteFile/RegSetValue/Process Create/TCP Connect`. Attempted `NAME NOT FOUND` ≠ successful access. Record return codes.

## 4. Network (simulated only)

Never let sample reach real third parties to "confirm it connects". Use isolated fakeDNS/INetSim/Fiddler on host-only net:

```bat
tcpdump -i eth0 -nn -s 0 -w run-001\traffic.pcap
```

Distinguish 7 levels (each is a different claim): embedded string → DNS attempt → DNS answer → TCP SYN → TCP established → app protocol → authed/encrypted session. Cite pcap frame + simulator log.

## 5. Evidence questions (answer per API)

- Did call occur, or only imported?
- Args after dereference (not raw pointers)?
- Which caller built args (stack trace → static function)?
- Return value checked? (`test eax,eax / jz` nearby?)
- Conditional on env/time/priv/args? Re-run with variants to prove.

Breakpoints answer single hits; for systematic arg/buffer logging, per-run
behavior changes, or hooking the unpacker: `12-hooking-windows.md`. For
crash triage and turning observations into a proof: `13-exploitation-windows.md`.
