# Evidence publication capacity plan

Migration is pending verified public TOS copies. This draft does not claim that the objects have been uploaded. Do not remove repository originals until both upload verification and independent anonymous GET pass.

- Evidence JSON/figures over200,000bytes belongs in `zenith-a02012413/liyufeng/safelab-public/reports-v1/<task>/…`, per-object public-read. Bucket policy/CORS stays unchanged.
- Keep HTML, small archive indexes, frontend data.json and required same-origin `media/frame_logs/`. Ordinary download links do not depend on CORS. Frozen evidence JSON bytes must remain unchanged on TOS.
- The21-object migration plan is `docs/evidence-migration-plan.json`:16,352,251bytes. Combined PR54/main snapshot50,103,791bytes becomes approximately33,751,540bytes before small indexes/tooling, below35MB.
- On an authorized node with the exact reviewed checkout, `tos==2.9.3` and environment `ZENITH_API_TOKEN`:

```sh
python3 scripts/upload-evidence-archives.py . docs/evidence-migration-plan.json /project_a02012413/public/liyufeng/migration-receipt.json
python3 scripts/apply-evidence-archives.py docs/evidence-migration-plan.json /project_a02012413/public/liyufeng/migration-receipt.json
node --test tests/*.test.js
node scripts/check-media-budget.cjs
```

The uploader checks capabilities, obtains900s scoped STS for source `k32181r1qe5gh73u8yvqyur5e`, refuses different existing content/overwrites and only sets ACL on the exact21planned keys. It stores no credentials, changes no bucket policy and deletes no object. Each upload is anonymously downloaded and verified against original bytes/SHA. The apply step independently repeats anonymous GET/SHA before replacing living page links, writing a small archive index and removing verified repository copies. Git history retains originals. It leaves frozen small evidence JSON and same-origin frame logs unchanged.

Before publication: verify all relative link replacements, add archived-asset URL metadata to frozen manifests if needed, confirm all remaining evidence references resolve through the archive index, and enforce the200KB rule in CI. Notify agents after migration is published. This draft is not a completed storage cleanup.
