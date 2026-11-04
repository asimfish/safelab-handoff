# Evidence publication storage policy

Repository evidence over 200,000 bytes must be archived as unchanged public-read objects before removing its Git copy. Both upload verification and an independent anonymous full GET must match original bytes and SHA256.

- Evidence JSON/figures over 200,000 bytes belongs in `zenith-a02012413/liyufeng/safelab-public/reports-v1/<task>/…`, per-object public-read. Bucket policy/CORS stays unchanged.
- Keep HTML, small archive indexes, frontend data.json and required same-origin `media/frame_logs/`. Ordinary download links do not depend on CORS. Frozen evidence JSON bytes must remain unchanged on TOS.
- The 21-object migration plan is `docs/evidence-migration-plan.json`: 16,352,251 bytes. Combined PR54/main snapshot 50,103,791 bytes becomes approximately 33,751,540 bytes before small indexes/tooling, below 35MB.
- Use the official HTTPS API2 (`https://zenith.bza.edu.cn/pt/api2`) via the authorized 5090 SSH route (`ZENITH_API_SSH_TARGET=bj.wznln.com`, port 4009). API credentials and returned STS stay in process memory; the uploader enforces the exact plan key allowlist. It does not claim the platform bucket STS itself is restricted to those keys.

On an authorized node with the exact reviewed checkout, `tos==2.9.3` and environment `ZENITH_API_TOKEN`:

```sh
python3 scripts/upload-evidence-archives.py . docs/evidence-migration-plan.json /project_a02012413/public/liyufeng/migration-receipt.json
python3 scripts/apply-evidence-archives.py docs/evidence-migration-plan.json /project_a02012413/public/liyufeng/migration-receipt.json
node --test tests/*.test.js
node scripts/check-media-budget.cjs
```

The uploader checks capabilities, obtains 900s STS for source `k32181r1qe5gh73u8yvqyur5e`, refuses different existing content/overwrites and only sets ACL on the exact 21 planned keys. It stores no credentials, changes no bucket policy and deletes no object. Each upload is anonymously downloaded and verified against original bytes/SHA. The apply step independently repeats anonymous GET/SHA before replacing living page links, writing a small archive index and removing verified repository copies. Git history retains originals. It leaves frozen small evidence JSON and same-origin frame logs unchanged.

Before publication: verify all relative link replacements, keep frozen historical evidence references unchanged and resolve archived paths through reports/archive-index.json, and enforce the 200KB rule in CI. Notify agents after migration is published. CI rejects tracked reports/ files over 200,000 bytes; the publication snapshot retains its 50,000,000-byte ceiling. The cleanup target is below 35,000,000 bytes.
