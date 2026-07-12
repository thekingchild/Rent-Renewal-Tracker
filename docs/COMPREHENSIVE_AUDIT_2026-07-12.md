# Rent Renewal Tracker Comprehensive Audit

> Remediation status: resolved by the security and production-hardening change set validated on 2026-07-12. The findings below are retained as the original audit trail; see the repository history and v0.3 upgrade patch for implemented controls.

Date: 2026-07-12
Audited app: `/home/erpnext/frappe-bench/apps/rent_renewal_tracker`
Bench: `/home/erpnext/frappe-bench`
Installed site: `site2.local` (`rent_renewal_tracker` 0.2.0)

## Executive verdict

The app is structurally complete and installed, but it is **not production-ready**. No DocType is wholly missing or syntactically broken. However, the core records share a release-blocking authorization design gap: roles grant broad access with no department/officer/confidentiality row filtering. Lease Document also contains a private-file ownership bypass. Production release should be blocked until those issues are fixed and role-based integration tests pass.

Severity totals: **2 Critical, 5 High, 10 Medium, 7 Low/UX**. The findings affect every one of the 14 DocTypes, either directly or through its parent/security model.

## Validation evidence

- App validator: passed (69 Python files, 14 DocTypes, 7 reports, 1 Workspace, 2 patches).
- Installed health contract: all checks passed (DocTypes, roles, workflow, reminders, reports, cards, charts, workspace).
- Python compilation: passed.
- JavaScript syntax checks: passed.
- Standalone reminder-rule tests: 6/6 passed.
- Bench runtime: scheduler active; two workers online.
- Full Frappe integration tests: **not run**, because `allow_tests` is disabled on `site2.local`. The audit did not modify site configuration.
- Visual/browser audit: **not performed** because no supported browser capture surface was available. UI/UX items below are code/schema-derived and are not claims based on screenshots or full WCAG testing.

## Release-blocking findings

### SEC-01 — Critical — Confidentiality and ownership are labels, not access controls

Affected: Lease, Lease Document, Rent Schedule, Renewal Request, Renewal Decision, Lease Contact, Property, Landlord, Reminder Log, reports, dashboard cards.

The app defines `confidentiality_classification`, `confidentiality`, responsible officer, and department fields, but hooks contain no `permission_query_conditions` or document `has_permission` handlers. Broad role permissions therefore allow a Lease Viewer, approver, auditor, or responsible officer to see every record granted to that role, including financial values, contact PII, restricted lease documents, and workflow comments. Public number cards/charts increase the likelihood of cross-scope aggregate disclosure.

Required fix: implement a single server-side authorization policy for Lease and all dependent records; enforce department/officer assignments, User Permissions, and confidentiality levels in list queries, document reads, reports, dashboard methods, exports, print/email/share, and File access. Add negative tests for every role and classification.

### SEC-02 — Critical — Lease Document can adopt an unauthorized private File

Affected: Lease Document and the File records it references.

`get_file_record()` looks up File by URL through `frappe.db.get_value`, bypassing permission checks. `can_use_file()` returns `True` for any unattached file and for any non-existent temporary Lease Document attachment. A user who can create Lease Documents and knows or obtains a private file URL can claim that file without proving File read/ownership permission. The later `db.set_value` reattaches it.

Evidence: `lease_document.py` lines 40–48, 81–100, 102–122.

Required fix: resolve the File by name/URL, require `frappe.has_permission("File", "read", file.name)`, validate uploader/owner for unattached and temporary uploads, require permission on the target Lease, use a cryptographically bound temporary-upload token/name, and test hostile cross-user adoption.

## High-priority findings

### AUTH-03 — High — Workflow role checks are not resource-scoped

Affected: Renewal Request, Renewal Decision, Lease.

Department/finance/legal/management roles can read or edit all renewal requests. `current_approver_role` identifies only a role, not a user or department. Draft is configured with `allow_edit: All`. Self-approval protection checks requester identity, but does not ensure the approver belongs to the lease's department or an explicit assignment.

Required fix: assign approvers explicitly or resolve them from department policy; restrict Draft editing to owner/responsible officer/administrator; enforce authorization in controller logic as defense in depth.

### DATA-04 — High — Successor lease creation bypasses permissions and is not transactionally isolated

Affected: Renewal Request, Lease, Lease Contact.

Completing a renewal creates an Active successor with `ignore_permissions=True`. This is appropriate only if the transition authorization is airtight, which it currently is not resource-scoped. Repeated update hooks, concurrent completion attempts, and partial failures rely on a unique predecessor field and ad hoc lookup rather than an explicit idempotent service boundary.

Evidence: `renewal_request.py` lines 187–250.

Required fix: move completion into an idempotent domain service, recheck transition and target permissions, lock the renewal/predecessor row, create successor and status updates in one transaction, and log the privileged action.

### OPS-05 — High — Reminder retries block a short worker and can duplicate sends

Affected: Reminder Log, Reminder Policy, Reminder Recipient, Reminder Threshold, Rent Renewal Settings, Lease.

Delivery performs immediate mail (`now=True`) inside an in-process retry loop on the `short` queue. A transport timeout can send successfully but throw before the log is finalized, causing a duplicate on retry. Existing queued logs are re-enqueued daily, which can also race with an already-running job. Retry count semantics record the zero-based loop index rather than clearly recording attempts.

Required fix: one attempt per queued job, exponential backoff, job-level deduplication, atomic Queued→Sending claim, provider idempotency/message correlation, stale-job recovery, and explicit attempts count.

### DATA-06 — High — Payment state is manually asserted without accounting evidence

Affected: Rent Schedule.

`payment_status` can be changed directly, including Paid/Waived, with no paid amount, payment date, waiver reason/approver, or link to Payment Entry/Journal Entry. Responsible Officers can create/write schedules, while Finance has read/export only. This is not an auditable financial control.

Required fix: derive payment status from immutable payment/waiver transactions, add partial-paid amount and reconciliation, require finance approval for waivers, and prohibit direct status edits after submission.

### SEC-07 — High — File validation trusts extensions and permits legacy active content

Affected: Lease Document.

The allowlist includes `.doc` and `.xls`; validation uses only the filename extension. There is no MIME/content signature validation, malware scan, quarantine state, or download security header policy.

Required fix: verify MIME and magic bytes, scan uploads before availability, quarantine pending files, prefer non-macro formats, and define retention/download logging.

## DocType readiness matrix

| DocType | Verdict | Main issues / required work |
|---|---|---|
| Lease | Block release | SEC-01; lifecycle and financial fields are broadly visible; operational statuses can be manually set through allowed-on-submit fields; next action uses the earliest date even if already past; needs a guided form and role-scoped actions. |
| Renewal Request | Block release | SEC-01, AUTH-03, DATA-04; large form exposes all proposed/current terms at once; approver is a role rather than assignment; concurrent sequence calculation is not locked. |
| Lease Document | Block release | SEC-01, SEC-02, SEC-07; confidentiality has no enforcement; needs upload progress, scan state, preview, and clear private-file guidance. |
| Rent Schedule | Not production-ready | SEC-01, DATA-06; no overlap/duplicate-period validation, due date need not relate to period, and no accounting integration; needs payment timeline and reconciliation UX. |
| Reminder Log | Refactor | SEC-01, OPS-05; immutable record protection is good, but there is no Sending state, retry schedule, duration/provider response, or safe manual retry action. Recipient and error fields may expose PII/secrets to broad auditor/admin roles. |
| Reminder Policy | Refactor | OPS-05; role recipient rules notify every enabled user with a role across the site, not a lease scope; templates are not validated/previewed; enabling system notifications with Email-only recipients can silently produce no system notification. |
| Reminder Recipient | Refactor (child) | Parent-driven security; a generic Data value is error-prone. Replace with dynamic Link/Select controls, show resolved-recipient preview/count, and warn on broad Role recipients. |
| Reminder Threshold | Minor refactor (child) | Parent validation is sound for enabled thresholds, but disabled duplicates/negative values can remain; UX needs ordering, timeline preview, and explanation of overdue cadence. |
| Rent Renewal Settings | Not production-ready | Settings read access exposes recipient addresses/config to auditor/admin roles; sender is unvalidated as an Email Account; comma/newline text areas are poor recipient controls; add readiness tests for outbound mail and scheduler. |
| Property | Refactor | SEC-01; controller has no coordinate bounds, active/disabled link filtering, department validity, or duplicate normalization. Add map/address UX and prevent inactive properties from new leases. |
| Landlord | Refactor | SEC-01; registration/tax identifier and contact PII are broadly readable; only compliance notes use permlevel 1. Add data masking, normalization, duplicate detection, contact/address models, and inactive-link controls. |
| Lease Department | Minor refactor | SEC-01; disabled departments can still be selected unless link queries are filtered; name-based autoname makes renames operationally risky; add manager/approver assignments and immutable code identity. |
| Lease Contact | Refactor (child) | SEC-01; contact PII inherits broad Lease visibility; no validation requiring email when reminders are enabled, no normalization/deduplication, and no consent/preference trail. |
| Renewal Decision | Refactor (child) | SEC-01/AUTH-03; read-only UI is useful but child rows are not cryptographically immutable and rely on parent workflow hooks. Add transition ID, source IP/session metadata where policy permits, and append-only server enforcement/tests. |

## Additional medium findings

1. Lease: `lease_status` and `renewal_status` are writable operational fields despite being partly derived. Make them controller/workflow-owned and expose intentional actions instead of raw state editing.
2. Lease: `next_action_date` selects the minimum of all dates, including dates already passed, so it may remain permanently stale and obscure the next future deadline. Track overdue action and next future action separately.
3. Lease: rent calculations only normalize Monthly basis. Annual, per-area, fixed-term, and payment frequency lack explicit calculation semantics; reports may compare incomparable annual values.
4. Renewal Request: renewal sequence uses read-then-increment without a unique `(lease, renewal_sequence)` constraint/lock. Concurrent inserts can duplicate sequence numbers.
5. Renewal Request: completion checks for any Lease Document of the category, not a document tied specifically to this renewal request/version or execution state.
6. Rent Schedule: overlapping periods, duplicate due lines, due dates outside the period/lease, and partial-payment consistency are not validated.
7. Property/Landlord/Department: `active`/`disabled` flags are descriptive; link fields do not show filters preventing selection on new transactions.
8. Reminder Policy: template rendering errors are discovered only during delivery. Validate Jinja syntax and allowed context at save time; provide preview/test-send.
9. Scheduled tasks update derived data with direct `db.set_value`, bypassing validation/version history; failures are per-batch rather than isolated per record.
10. Dashboard cards/charts are `is_public=1`. Even where underlying `get_list` applies permissions, public aggregate definitions plus absent row scoping can leak portfolio totals to any app role.

## UI/UX and accessibility risks (code-derived only)

1. **Lease creation — needs improvement:** 50+ fields are presented in one form with limited conditional disclosure. Add a summary header, staged sections, defaults from Property/Settings, inline deadline explanation, and clear Submit/Activate actions.
2. **Renewal review — needs improvement:** current and proposed terms should be a side-by-side difference view with changed values highlighted; raw sequential fields increase approval errors. Keep decision history visible and require comments in the action dialog.
3. **Document upload — needs improvement:** show accepted formats/size before upload, private/scan status, version and category guidance, and an accessible error summary tied to the file input.
4. **Rent schedule — needs improvement:** provide schedule generation, totals, overlap warnings, reconciliation status, and bulk import validation rather than repeated manual line entry.
5. **Reminder configuration — needs improvement:** replace generic recipient values and raw template editors with type-aware controls, live resolution preview, template preview, and test delivery.
6. **Lists/reports — needs improvement:** add confidentiality/status badges with text (not color alone), saved role-specific views, actionable empty states, consistent date/currency formatting, and responsive column prioritization.
7. **Accessibility verification required:** keyboard order, focus visibility, action-dialog focus trapping, error announcements, table semantics, contrast, target size, zoom/reflow, and screen-reader names could not be confirmed without live screenshots and browser/assistive-technology testing.

## Recommended release plan

1. Block release and fix SEC-01 and SEC-02 first.
2. Add role/department/confidentiality permission-query and document-permission tests, including File download and report/card leakage tests.
3. Fix workflow assignment/privileged successor creation and payment controls.
4. Redesign reminder delivery around atomic claims and asynchronous retry.
5. Enable tests on a disposable/staging site and run the complete Frappe integration suite; never enable tests first on production.
6. Run a screenshot-based desktop/mobile UX and keyboard/accessibility audit for the main flows before acceptance.

## Audit limits

This was a source, schema, metadata, installed-health, scheduler, and non-destructive runtime audit. It did not alter application code or site configuration. It did not run dynamic penetration testing, malware scanning, load testing, email delivery, disaster recovery, database migration, the disabled integration suite, or a live browser flow. Findings should therefore be treated as the minimum remediation set, not a certification of all unmentioned behavior.
