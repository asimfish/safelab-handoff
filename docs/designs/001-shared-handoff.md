# ADR-001: task/version-first handoff and shared edits

Status: Accepted for this user-authorized dashboard revision.

The first dashboard mixed datasets, cameras, checkpoint steps, historical evaluation
conditions and agent logs. Users need to hand off individual trained weights, see
which need evaluation, and add a new weight from another computer.

Candidates:
1. GitHub file editor + static JSON: durable and versioned, but requires editing
   a large JSON document and deployment before each update.
2. A separate authenticated database/API: offers in-page writes, but no backend,
   auth application or service credentials are configured for this Pages site.
3. GitHub Issues as shared editable records, read by the static dashboard: uses
   GitHub login/permissions, requires no browser credential, and updates without
   rebuilding the site. Chosen for this deployment.

The canonical imported data stays in data.json. UI hierarchy is task → exact
training dataset version → input camera → method/run/checkpoint. A checkpoint can
have historical results and a pending retest simultaneously. Different protocols
are never pooled. Completed five-seed runs can be aggregated only within the same
record/step/horizon/protocol family.

Shared writes use a web form which prepares a bounded JSON record in a GitHub
issue. The user confirms Submit new issue on GitHub; subsequent edits use GitHub's
issue body editor. The dashboard reads all states, with bounded pagination and
visible sync errors; this is not a localStorage database. Only OWNER, MEMBER,
COLLABORATOR authors or maintainer-approved labels enter the official board.
Other submissions are visible as awaiting confirmation, never overwriting source
results. Newer updates to the same target win; the original evidence remains in
details. Reported results remain explicitly team-reported, not original verified
scores. Closing an issue does not delete a handoff; a safelab-archived label does.

Trust boundaries: public unauthenticated JSON/GitHub API → strict schema → escaped
HTML/text. There is no credential entry, server write proxy, HTML interpretation,
arbitrary URL fetch, or code execution from issue data. URLs open only fixed
GitHub issue paths or validated HTTPS links. External accounts need repository
collaborator membership or maintainer approval. GitHub is the audit/edit authority.
Rate-limit/offline errors retain the imported snapshot and clearly identify the
missing shared feed; no claim of successful save before GitHub confirmation.

## Presentation revision: single editable table

The user explicitly replaced the multi-page information architecture with one
flat table. Task, exact dataset version/camera, method, weight, training/delivery,
evaluation state and rates are direct columns. Filters narrow the same table;
historical evidence is a row dialog, not a separate dashboard. Shared storage and
GitHub authorization remain unchanged. Identity edits preserve the original row
and create a new weight entry; training placeholders can be completed in place.
