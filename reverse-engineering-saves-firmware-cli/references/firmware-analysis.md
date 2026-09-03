# Firmware Analysis Tasks — Manifests, Boot Map, Secrets, Version Diffs

## 1. Manifests, integrity, signatures (three separate claims)

Packages carry: product/HW compat, min/max version, anti-rollback counter,
partition names + targets, sizes + hashes, compressor, build IDs, cert chain
/ key IDs, signatures.

```bash
jq -S . manifest.json > manifest.normalized.json 2>/dev/null || true
xmllint --format manifest.xml > manifest.normalized.xml 2>/dev/null || true
sha256sum payload-*.bin
# compare each declared hash against the carved payload bytes
```

Keep three verdicts apart:

1. **Hash matches payload** — content integrity vs manifest.
2. **Signature structure present** — signed container appears to exist.
3. **Signature valid + trusted** — needs canonicalization + algorithm + chain
   + trust decision actually verified.

Never collapse to "firmware is signed". Extraction success proves nothing
about (3).

## 2. Boot-chain map (data-only, no code analysis)

```text
boot ROM assumptions -> 1st-stage loader -> bootloader container
  -> selected config -> kernel + DTB + initramfs/rootfs -> config/NVRAM
```

Sources: partition names/offsets, FIT configs, DT `chosen` + partition
nodes, boot configs, `/boot`, `/etc/inittab`, init scripts, service units,
manifest targets, duplicate/recovery partitions. Inventory startup config as
text/metadata — do not execute:

```bash
grep -RInE '(^|[[:space:]])(init|rcS|systemd|procd|telnetd|dropbear|sshd|httpd|mount|ubiattach)' extracted-root/etc 2>/dev/null
```

Service-behavior interpretation needs code analysis — out of scope. Report
only what config directly states, then hand off executables by hash.

## 3. Configuration, credentials, keys, certificates

Authorized-review targets: default users/passwords + hashes, API tokens,
Wi-Fi keys, private keys, certs/trust stores, cloud/update endpoints, debug
flags, console settings, device-unique material in generic images.

```bash
grep -RInaE 'password|passwd|secret|token|api[_-]?key|private[_-]?key|BEGIN .*PRIVATE KEY|debug|telnet|dropbear|update|https?://' extracted-root 2>/dev/null > sensitive-string-leads.txt
find extracted-root -type f \( -iname '*.pem' -o -iname '*.crt' -o -iname '*.cer' -o -iname '*.key' \) -print
openssl x509 -in certificate.pem -noout -subject -issuer -serial -dates -fingerprint -sha256
```

Leads + false positives + live secrets — restrict access, verify context,
never paste private-key material into general reports (location +
fingerprint + scope + handling only).

## 4. Version-to-version diffing (four layers)

Raw byte diffs drown in recompression, timestamps, allocation, signatures,
padding. Diff per layer:

L1 outer: sizes, hashes, `binwalk` listings diffed.
L2 container: names, offsets, stored/raw lens, compressors, hashes, version
metadata.
L3 trees: structured manifest, not bare `sha256sum` lines from different
roots:

```bash
python3 scripts/tree_manifest.py old-root > old.manifest.jsonl
python3 scripts/tree_manifest.py new-root > new.manifest.jsonl
diff -u old.manifest.jsonl new.manifest.jsonl > files.diff || true
```

L4 content: sort JSON keys, pretty XML, ordered SQL dumps, archive member
lists; quarantine generated files/logs/caches/timestamps.

Report buckets: added/removed partitions; moved/resized partitions; files
added/removed/modified; config changes; cert/key changes; signing/compressor
changes; repacking noise; unknowns for specialist tracks.
