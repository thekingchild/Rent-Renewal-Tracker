# Rent Renewal Tracker - Frappe App Development Plan

**Proposed app name:** `rent_renewal_tracker`  
**Target platform:** Frappe Framework v16.x  
**Deployment model:** Standalone Frappe Bench app; ERPNext is not required  
**Plan status:** Draft for stakeholder validation  
**Prepared:** 10 July 2026

## 1. Executive summary

This plan translates the attached Microsoft 365 solution into a standalone Frappe Framework application. The app will provide one controlled system for property leases, agreements, rent schedules, renewal approvals, reminders, reports, and management oversight.

The first production release will deliver:

- A centralized lease and property register.
- Private lease document storage linked directly to each lease.
- Automatic reminders 90, 60, 30, 14, and 7 days before expiry, plus overdue escalation.
- A configurable, sequential renewal approval process.
- Role-based access for lease administrators, responsible officers, department heads, Finance, Legal, Management, auditors, and system administrators.
- Workspace shortcuts, operational lists, calendar views, dashboards, and exportable reports.
- Version history, timeline activity, notification history, and an auditable renewal decision trail.
- Import tools, automated tests, deployment instructions, administrator guidance, and user training materials.

The recommended baseline is Frappe v16. A separate compatibility branch should only be added if an existing Bench must remain on Frappe v15.

## 2. Business objectives and success measures

### Objectives

1. Eliminate fragmented spreadsheets, folders, and email follow-up.
2. Prevent missed lease expiries and late renewal decisions.
3. Make ownership and approval responsibility explicit.
4. Give Finance, Legal, Administration, and Management a common source of truth.
5. Preserve the evidence behind every approval, rejection, reminder, and lease amendment.
6. Provide management with current rent exposure and renewal risk.

### Proposed success measures

- 100% of active leases have an assigned responsible officer, department, end date, and notice period.
- 100% of active leases have a calculated next action date.
- At least 99% of scheduled reminder jobs complete without error each month.
- No duplicate reminder is sent for the same lease, threshold, recipient, and renewal cycle.
- 100% of renewal decisions have an actor, timestamp, workflow state, and comment trail.
- Management dashboard totals reconcile to the lease register and rent schedules.
- At least 95% of users complete role-based acceptance tests before go-live.

## 3. Scope

### In scope for release 1

- Property, landlord, contact, lease, document, and rent schedule records.
- Lease lifecycle and renewal request workflows.
- Renewal reminders and overdue escalation.
- Email and Frappe in-app notifications.
- Optional outbound Microsoft Teams webhook notification, if the organization retains Teams.
- Lists, saved filters, calendar, reports, dashboard charts, and Workspace.
- Role and permission configuration.
- Private attachments and document categorization.
- Version tracking and audit reporting.
- CSV/XLSX data import templates and migration validation.
- Installation, configuration, backup, restore, monitoring, and user documentation.

### Deferred or optional

- Rent payment execution, bank integration, or general ledger posting.
- A landlord self-service portal.
- OCR or AI extraction of lease terms.
- Electronic signatures.
- Full document management features such as check-in/check-out and records disposition.
- GIS mapping beyond stored coordinates and report-ready location data.
- ERPNext integration. This can be added later for Supplier, Department, Cost Center, Purchase Invoice, or Payment Entry links.
- SMS/WhatsApp alerts. These require approved providers and separate message costs.

## 4. Source-to-Frappe solution mapping

| Microsoft 365 plan component | Frappe implementation | Improvement in the proposed app |
|---|---|---|
| SharePoint team site | Rent Renewal Tracker Workspace | Role-aware navigation, live indicators, and shortcuts within Desk |
| Microsoft List | Lease, Property, Landlord, Rent Schedule, and Renewal Request DocTypes | Relational validation instead of a single flat list |
| SharePoint document library | Private File attachments plus Lease Document metadata | Documents inherit record permissions and are categorized per lease |
| List views | Standard and custom List Views, saved filters, Calendar, and Reports | Consistent filtering, indicators, exports, and assignment |
| Power Automate reminders | Daily scheduler job, Notification templates, and Reminder Log | Idempotency, retry history, escalation, and configurable thresholds |
| Power Automate approval | Native Workflow on Renewal Request | Role-based transitions, conditions, actions, and durable timeline |
| Power BI dashboard | Workspace number cards, Dashboard Charts, and Script Reports | No separate BI license or data refresh pipeline for operational reporting |
| Teams notifications | Frappe in-app alerts and optional Teams webhook | Core workflow does not depend on Teams; Teams remains an optional channel |
| Microsoft 365 groups | Frappe Roles, Role Permissions, User Permissions, and Page/Report roles | Document-, action-, and field-level controls |
| Version history/audit logs | Track Changes, Version, Workflow Action, timeline, Reminder Log, and Error Log | App-specific audit views and operational exception tracking |

## 5. Stakeholders and discovery decisions

Before development starts, a requirements workshop must confirm:

- Number of properties, leases, users, departments, regions, and expected annual growth.
- Whether one property can have concurrent leases or multiple leased units.
- Whether rent values are monthly, annual, or variable over the lease term.
- Required currencies and exchange-rate reporting rules.
- Whether service charges, taxes, deposits, and utilities must be tracked separately.
- Renewal approval order, rejection/rework behavior, delegates, and approval limits.
- Whether every approval stage is mandatory or can be conditionally skipped.
- Reminder recipients by threshold and escalation recipients after expiry.
- Required document categories, maximum file size, retention period, and allowed extensions.
- Whether historical documents must remain immutable.
- Whether Microsoft Teams, ERPNext, SSO, SMS, or WhatsApp integrations are required.
- Required report filters and the definition of each management KPI.
- Hosting, backup, disaster recovery, data residency, and availability requirements.

Unresolved items will be recorded in a decision log with an owner and due date. Development should not begin on approval rules until the workflow matrix is signed off.

## 6. Functional design

### 6.1 Application module and Workspace

Create a module named **Rent Renewal Tracker** and a public Workspace visible only to permitted Desk users.

Workspace content:

- **Actions:** New Lease, New Property, Start Renewal, Import Leases.
- **Operational shortcuts:** Active Leases, Expiring in 90 Days, Expired, Renewals Awaiting My Action, Upcoming Rent Payments, Documents.
- **Number cards:** Total Leases, Active, Expiring This Month, Expiring Next Quarter, Overdue Renewals, Total Annual Rent.
- **Charts:** Rent by Region, Rent by Department, Lease Status, Renewal Pipeline, Expiry Trend.
- **Reports:** Lease Register, Renewal Pipeline, Upcoming Expiries, Upcoming Payments, Rent Exposure, Reminder Delivery, Audit Review.

### 6.2 DocType model

#### Property

Master record for a leased location or asset.

Key fields:

- Property ID and property name.
- Property type: Office, Factory, Warehouse, Regional Office, Land, Residential, Other.
- Address, city, state, country, region, latitude, and longitude.
- Responsible department and default responsible officer.
- Ownership/occupancy status and active flag.
- Notes and attachments.

#### Landlord

Standalone counterparty master so the app does not require ERPNext.

Key fields:

- Landlord ID, legal name, registration/tax identifier.
- Address and preferred currency.
- Primary contact name, email, and phone.
- Bank/payment notes protected by elevated field permissions if included.
- Active flag and compliance notes.

#### Lease Department

Small master used for ownership, filtering, and user permissions. If ERPNext integration is enabled later, this record can map to ERPNext Department.

#### Lease Contact (child)

Reusable child table structure for landlord, legal, facility, and escalation contacts.

Fields: contact type, name, organization, email, phone, receives reminders, and notes.

#### Lease

Authoritative contract record. Naming series: `LEASE-.YYYY.-.#####`.

Identity and ownership fields:

- Property, lease title, landlord, region, lease type, and external/reference number.
- Responsible department, responsible officer, contract owner, and backup officer.
- Lease contacts child table.

Term fields:

- Start date, end date, notice period in days, notice deadline, and tenure.
- Renewal option, renewal option deadline, break clause date, and auto-renew flag.
- Computed days to expiry and next action date.

Financial fields:

- Currency, rent basis, monthly rent, annual rent, payment frequency, security deposit.
- Service charge, tax, escalation/indexation rule, and current total annual occupancy cost.
- Rent schedule child rows or linked Rent Schedule records for stepped/variable rent.

Status fields:

- Lease status: Draft, Active, Expiring Soon, Renewal in Progress, Renewed, Expired, Terminated.
- Renewal status: Not Started, Draft, Pending Approval, Approved, Rejected, Completed, Not Renewing.
- Renewal completed flag, last reminder date, next reminder date, and last renewal request.

Control fields:

- Confidentiality classification, maximum attachments, comments, and migration source ID.
- Track Changes enabled; standard assignments, comments, email, tags, and private attachments available.

Validations:

- End date must be later than start date.
- Notice period must be zero or positive.
- Annual rent and payment values cannot be negative.
- Active leases require a property, landlord, department, responsible officer, end date, notice period, currency, and rent value.
- Conflicting active leases for the same property/unit produce a warning or error according to approved business rules.
- Dates and financial totals are calculated server-side, not trusted from the browser.

#### Rent Schedule

Use a linked DocType rather than only monthly/annual fields when rent changes over time.

Fields:

- Lease, period from/to, due date, description, currency, base rent, service charge, tax, total due, payment status, and payment reference.
- Status: Planned, Due, Paid, Waived, Overdue, Cancelled.

Release 1 tracks planned and recorded payment status only; it does not move money or post accounts.

#### Lease Document

Metadata record linked to a private Frappe File.

Fields:

- Lease, category, title, file, document date, effective date, expiry date, confidentiality, version label, uploaded by, and notes.
- Categories: Signed Agreement, Addendum, Renewal Letter, Approval, Payment Receipt, Valuation, Correspondence, Other.

Files must be private by default. Access follows the linked lease/document permissions. The application must validate permitted extensions and file-size settings.

#### Renewal Request

Submittable transaction representing one renewal cycle. Naming series: `RNEW-.YYYY.-.#####`.

Fields:

- Lease and renewal sequence number.
- Current term/rent snapshot.
- Proposed start/end dates, notice date, rent, currency, frequency, escalation, and other commercial terms.
- Recommendation: Renew, Renegotiate, Relocate, Terminate.
- Business justification, risk, budget impact, alternative options, and supporting documents.
- Workflow state, current approver role, requested by/on, final decision by/on, rejection reason, and completion date.
- Approval decision history child table populated by server-side workflow handlers if the built-in timeline is insufficient for audit reporting.

Only one open renewal request may exist for the same lease and renewal cycle.

#### Reminder Policy

Configurable policy rather than hard-coded thresholds.

Fields:

- Policy name, enabled flag, thresholds in days, overdue cadence, recipients by role/field, escalation recipients, channels, templates, and stop conditions.
- Default thresholds: 90, 60, 30, 14, and 7 days, plus expiry day and overdue.

#### Reminder Log

Immutable operational record for each attempted notification.

Fields:

- Lease, renewal request, policy, threshold, scheduled date, channel, recipient, status, sent time, retry count, message ID, and error summary.
- Unique deduplication key: lease + renewal cycle + threshold + channel + recipient.

#### Rent Renewal Settings (Single)

- Default reminder policy.
- Expiring-soon threshold.
- Default currency and timezone.
- Email sender/account.
- Teams webhook enabled and secret configuration reference.
- Reminder retry limit and administrator error recipients.
- Whether a renewal request is created automatically at the first threshold.

### 6.3 Relationship model

```text
Property 1 --- * Lease * --- 1 Landlord
                   |
                   +--- * Lease Document --- 1 private File
                   +--- * Rent Schedule
                   +--- * Renewal Request
                   +--- * Reminder Log
                   +--- * Lease Contact (child)

Reminder Policy 1 --- * Reminder Log
Lease Department 1 --- * Lease
User 1 --- * Lease (responsible/owner/backup)
```

### 6.4 Lease lifecycle

1. Lease Administrator creates and validates the draft lease.
2. An authorized user activates the lease.
3. A daily job recalculates derived status, next action, and reminder eligibility.
4. At the first configured threshold, the responsible officer starts a Renewal Request; the app may auto-create a draft if enabled.
5. The renewal proceeds through approval.
6. On final approval, the responsible officer records executed renewal documents and completes the request.
7. Completion updates the existing lease term or creates a successor lease, according to the signed-off data policy. Creating a successor record is recommended because it preserves historical commercial terms.
8. If not renewed, the lease becomes Expired or Terminated and overdue escalation stops only when the decision is formally completed.

### 6.5 Renewal workflow

Proposed default states and transitions:

| State | Allowed action | Acting role | Next state |
|---|---|---|---|
| Draft | Submit for Department Review | Responsible Officer / Lease Administrator | Department Review |
| Department Review | Approve | Department Head | Finance Review |
| Department Review | Return | Department Head | Draft |
| Finance Review | Approve | Finance Approver | Legal Review |
| Finance Review | Return | Finance Approver | Draft |
| Legal Review | Approve | Legal Approver | Management Approval |
| Legal Review | Return | Legal Approver | Draft |
| Management Approval | Approve | Management Approver | Approved |
| Management Approval | Reject | Management Approver | Rejected |
| Approved | Mark Executed | Lease Administrator | Completed |

Rules:

- A return or rejection requires a comment.
- Users cannot approve their own stage where segregation of duties is required.
- Workflow email alerts and in-app Workflow Actions notify the next role.
- Delegation is handled by time-bound role assignment or an approved substitute process.
- Conditional transitions may skip stages only where the signed approval matrix permits it.
- Approved commercial values become read-only; changes require amendment/rework.
- Final completion requires the signed renewal agreement and new lease dates.

### 6.6 Reminder engine

Implement a daily scheduler event in application code.

Algorithm:

1. Select active leases with an end date and enabled reminder policy.
2. Calculate days to expiry using the site's timezone.
3. Determine whether a configured threshold or overdue cadence is due.
4. Resolve recipients from responsible officer, department, Finance, Legal, and explicit escalation fields.
5. Check the Reminder Log deduplication key.
6. Queue email/in-app/optional Teams delivery after the database transaction commits.
7. Write a success or failure log for every recipient and channel.
8. Update last reminder and next reminder only after successful delivery.
9. Retry transient failures up to the configured limit; alert System Manager when exhausted.

Important controls:

- Never rely only on a browser form script for dates or reminders.
- The job must be safe to run repeatedly without duplicate messages.
- Reminder content includes property, lease ID, end date, days remaining, responsible officer, current renewal state, and a direct record link.
- Completed, terminated, or superseded leases are excluded.
- Scheduler, queue worker, and outbound email health are included in production monitoring.

### 6.7 Views and reports

#### Operational views

- Active Leases.
- Expiring Within 90 Days.
- Expiring This Month.
- Expiring Next Quarter.
- Expired Leases.
- Renewed Leases.
- By Department.
- By Region.
- Renewals Awaiting My Action.
- Failed Reminders.
- Upcoming Payments.

The Lease list will show color indicators for Active, Expiring Soon, Renewal in Progress, Expired, and Terminated. A Calendar view will use lease end date and rent due date.

#### Reports and KPIs

- Total, active, expiring, renewed, expired, and terminated leases.
- Total annual rent and total annual occupancy cost by currency.
- Rent by property, landlord, region, and department.
- Expiry exposure by month/quarter.
- Renewal pipeline by state and aging.
- Approvals pending by role and age.
- Upcoming payments and overdue recorded payments.
- Reminder delivery rate and failures.
- Lease data completeness exceptions.
- Audit changes by document, user, and period.

Currency totals must not combine different currencies without an agreed conversion method. Dashboards should either filter by currency or display separate totals.

## 7. Security, privacy, and audit design

### Roles

- **Rent Renewal System Manager:** app configuration, roles, policies, imports, and all records.
- **Lease Administrator:** create/edit leases, documents, schedules, and complete approved renewals.
- **Responsible Officer:** read assigned leases, prepare renewal requests, upload supporting documents.
- **Department Head:** read department leases and act on Department Review.
- **Finance Approver:** read commercial fields and act on Finance Review.
- **Legal Approver:** read contract documents and act on Legal Review.
- **Management Approver:** organization-wide read and final approval.
- **Lease Auditor:** read/export records, workflow history, reminders, and audit reports; no edits.
- **Lease Viewer:** read permitted operational records; no restricted financial fields if policy requires field-level separation.

### Permission controls

- Define standard DocType permissions in app fixtures/code and verify them after install.
- Use User Permissions on Lease Department or Region for row-level restriction.
- Apply permission levels to sensitive financial, bank, or legal fields.
- Restrict Reports, Pages, Workspace, export, import, print, share, delete, submit, cancel, and amend separately.
- Do not expose confidential leases or files through public website routes.
- Make attachments private by default and test direct URL access with unauthorized users.
- Enforce server-side permission checks in all whitelisted methods and report queries.
- Keep integration secrets in site configuration or an encrypted Password field, never in source code.

### Audit controls

- Enable Track Changes for Lease, Rent Schedule, Lease Document, Renewal Request, Reminder Policy, and Settings.
- Preserve standard creation, modification, owner, Version, comments, assignments, emails, and workflow actions.
- Record reminder attempts in immutable Reminder Log rows.
- Prohibit ordinary users from deleting submitted renewal requests or audit logs.
- Define backup retention and legal retention with stakeholders; application history is not a substitute for tested backups.
- Add an administrator report for changes to critical fields such as dates, rent, landlord, status, approver, and policy thresholds.

## 8. Technical architecture

### Baseline

- Frappe Framework v16.x on Linux. For Windows development, use Ubuntu under WSL or containers.
- MariaDB 11.8, Python 3.14, Node.js 24, Redis/Valkey, queue workers, scheduler, NGINX, and a supported PDF renderer according to the Frappe v16 environment requirements.
- Git repository with a `version-16` production branch and tagged releases.
- Standalone app dependency on Frappe only.

### Logical architecture

```text
Desk/Web client
      |
Frappe web application
      +--- DocTypes, Workflow, permissions, Reports, Workspace
      +--- REST API and optional outbound webhooks
      |
MariaDB -------- private/public file storage
      |
Redis/Valkey queues --- workers --- email / in-app / optional Teams
      |
Scheduler --- daily reminder and status jobs
```

### Proposed repository layout

```text
rent_renewal_tracker/
  pyproject.toml
  rent_renewal_tracker/
    hooks.py
    modules.txt
    patches.txt
    install.py
    scheduled_tasks.py
    rent_renewal_tracker/
      doctype/
      report/
      dashboard_chart/
      workspace/
      notification/
      workflow/
    public/
      js/
      css/
    templates/
      emails/
    integrations/
      teams.py
    tests/
```

Standard DocTypes, reports, Workspace, roles, workflows, notifications, and other configuration must be committed as application artifacts or fixtures so a fresh install is reproducible.

### Install and upgrade contract

Planned installation flow:

```bash
cd frappe-bench
bench get-app rent_renewal_tracker https://<git-host>/<organization>/Rent-Renewal-Tracker --branch <branch>
bench --site <site-name> install-app rent_renewal_tracker
bench --site <site-name> migrate
bench --site <site-name> enable-scheduler
bench --site <site-name> list-apps
```

The app must support clean install, uninstall in a disposable test site, backup/restore, and forward migration. Schema or data transformations after release will use versioned patches in `patches.txt`.

## 9. Delivery plan

The estimate assumes one Frappe developer, one part-time QA analyst, one business product owner, and timely stakeholder decisions. Calendar duration is approximately **9 weeks**. Add contingency for integrations, complex data cleansing, or approval changes.

| Phase | Duration | Main activities | Exit criteria |
|---|---:|---|---|
| 0. Discovery and solution validation | 1 week | Workshops, source review, data profiling, workflow matrix, KPI definitions, hosting decision, backlog | Signed requirements, data dictionary, workflow matrix, acceptance criteria |
| 1. App scaffold and foundations | 1 week | Create app/module, CI, coding standards, roles, masters, naming, settings, install hooks | App installs on clean v16 site; roles and masters verified |
| 2. Lease register and documents | 1.5 weeks | Property, Landlord, Lease, contacts, document metadata, private files, validations, list/calendar views | Lease CRUD and permissions pass tests; files protected |
| 3. Rent schedules and operational views | 0.5 week | Rent Schedule, calculations, due states, saved operational reports | Financial calculations and views reconcile to test cases |
| 4. Renewal workflow | 1.5 weeks | Renewal Request, workflow, actions, email alerts, decision validation, successor lease logic | Complete approve/return/reject/execute paths pass by role |
| 5. Reminder and escalation engine | 1 week | Policies, daily job, queueing, templates, deduplication, retries, logs, Teams adapter | Threshold, overdue, retry, and duplicate-prevention tests pass |
| 6. Workspace, dashboards, and reports | 1 week | Workspace, cards, charts, management and audit reports, exports | KPIs reconcile to seeded data; role access verified |
| 7. Migration, hardening, and UAT | 1 week | Import templates, trial migration, security tests, performance, backups, UAT fixes | Data reconciliation and UAT sign-off |
| 8. Production deployment and hypercare | 0.5 week plus 4-week support window | Production install, final migration, training, monitoring, issue triage | Go-live checklist complete; handover accepted |

## 10. Engineering work packages

### Foundation

- Scaffold app with `bench new-app rent_renewal_tracker`.
- Set Frappe v16 dependency and Python/package metadata.
- Configure linting, formatting, unit tests, test site creation, and build checks.
- Implement `after_install` validation/default setup and safe `before_uninstall` behavior.
- Add fixtures or standard artifacts for roles, Workspace, workflow, notifications, reports, and charts.

### Domain and validation

- Implement all master and transaction DocTypes.
- Add naming series, indexes, mandatory rules, unique constraints, and calculation methods.
- Add lease overlap validation and open-renewal uniqueness.
- Add server-side status derivation and successor lease creation.
- Seed controlled choices only where a master is unnecessary.

### Automation and integration

- Implement scheduler hooks and queued delivery services.
- Implement Reminder Log deduplication and retry states.
- Build email and in-app templates.
- Add optional Teams adapter behind an interface and feature flag.
- Add error logging and health report.

### User experience and analytics

- Configure list columns, indicators, buttons, filters, and calendar mappings.
- Add contextual actions: Start Renewal, Open Documents, View Payment Schedule, Mark Executed.
- Build Workspace, number cards, dashboard charts, and reports.
- Add print formats for Lease Summary and Renewal Approval Pack.

### Data migration

- Publish import templates for Property, Landlord, Lease, Rent Schedule, and Lease Document metadata.
- Create a source-to-target mapping and transformation rules.
- Normalize dates, currencies, departments, regions, emails, and duplicate landlords/properties.
- Import master data before leases, then schedules/documents, then open renewals.
- Reconcile row counts, totals by currency, earliest/latest dates, statuses, attachments, and samples.
- Keep migration scripts idempotent and retain a source ID for traceability.

## 11. Test strategy

### Automated tests

- Clean app installation and default setup.
- DocType permissions for every role.
- Lease date, rent, required-field, overlap, and status validation.
- Notice deadline, days-to-expiry, annual rent, and next-reminder calculations.
- Reminder thresholds at 90/60/30/14/7/0/overdue days.
- Timezone and date-boundary behavior.
- Duplicate reminder prevention and retry behavior.
- Workflow transitions, role restrictions, mandatory comments, and self-approval rules.
- Successor lease creation and history preservation.
- Report filters, totals, currency separation, and unauthorized data exclusion.
- Private file access and API permission tests.
- Migration patch and backward-compatibility tests for released versions.

### Manual/UAT scenarios

- Create, edit, activate, expire, terminate, renew, and supersede a lease.
- Upload, download, replace, and deny access to private documents.
- Submit, approve, return, reject, resubmit, and complete a renewal.
- Deliver email and in-app reminders; simulate failure and retry.
- Verify every operational view and dashboard against prepared data.
- Import representative legacy records and reconcile them.
- Verify mobile/responsive use for key approval and lease review screens.
- Run backup and restore rehearsal before production go-live.

### Non-functional tests

- Permission and insecure direct object reference tests.
- File upload extension, size, and authorization tests.
- Performance using expected five-year record and audit-log volumes.
- Scheduler recovery after downtime.
- Email/queue failure observability.
- Browser support and basic accessibility: keyboard operation, labels, focus, contrast, and status not conveyed by color alone.

## 12. Release 1 acceptance criteria

Release 1 is accepted when:

1. The app installs on a clean supported Frappe v16 site using documented Bench commands.
2. Authorized users can manage the full lease dataset and unauthorized users cannot access restricted records or private files.
3. The system calculates lease notice/expiry dates and generates the approved operational views.
4. Reminders are sent at all configured thresholds without duplication and every attempt is logged.
5. A renewal can complete the Officer -> Department Head -> Finance -> Legal -> Management sequence, including return and rejection.
6. Final approval and execution preserve a reviewable actor/time/comment history.
7. Dashboard and report totals reconcile to seeded and migrated data, including currency separation.
8. The agreed legacy data and documents are imported with signed reconciliation results.
9. Automated tests, security tests, UAT, and backup/restore rehearsal pass.
10. Administrator guide, user guide, training, deployment runbook, and support ownership are delivered.

## 13. Deployment and operations

### Environments

- Development: developer mode, synthetic data, automated tests.
- UAT/Staging: production-like configuration, masked migration sample, real role matrix.
- Production: restricted administrator access, TLS, backups, monitoring, and approved integrations.

### Go-live checklist

- Pin and record exact Frappe/app versions.
- Take and verify pre-deployment backups.
- Confirm site timezone, currency, email account, file limits, roles, policies, and scheduler.
- Install/migrate app and run smoke tests.
- Import and reconcile approved data.
- Test one notification per channel with controlled recipients.
- Verify workers, scheduler, failed-job logs, backups, TLS, and private files.
- Freeze legacy edits or define a final delta-migration window.
- Train users and publish support contacts.

### Monitoring and maintenance

- Daily: scheduler status, queue failures, email failures, and overdue renewals.
- Weekly: backup success, failed Reminder Logs, permission/role changes, and data-quality exceptions.
- Monthly: restore sample, storage growth, app/framework security updates, and KPI reconciliation.
- Quarterly: role recertification, workflow review, retention review, and disaster recovery rehearsal according to policy.
- Use tagged app releases, change logs, tested patches, and rollback instructions for every production release.

## 14. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Approval rules remain ambiguous | Rework and control gaps | Sign workflow matrix and approval limits before build |
| Historical data is incomplete or duplicated | Unreliable reminders/reports | Profile early, define cleansing ownership, trial-import twice |
| Scheduler or workers are disabled | Missed notifications | Health monitoring, failed-job alerts, daily operations check |
| Email delivery is rejected or filtered | Stakeholders miss alerts | Configure SPF/DKIM/DMARC, controlled tests, in-app fallback, delivery logs |
| Attachments are exposed | Confidentiality breach | Private-by-default files, permission tests, TLS, restricted exports |
| Mixed currencies are summed | Misleading management totals | Filter/separate currency or implement approved exchange-rate rules |
| Users bypass workflow through broad permissions | Audit/control failure | Least privilege, explicit submit/cancel/amend rights, negative tests |
| Frappe upgrades introduce breaking changes | Downtime or defects | Pin versions, staging rehearsal, automated regression suite, versioned branches |
| Custom Teams integration changes | Notification outage | Keep Teams optional and isolate it behind a tested adapter |
| Excessive app customization | High maintenance cost | Prefer native Frappe features and keep business logic in app code |

## 15. Deliverables

- Git repository for `rent_renewal_tracker`.
- Installable Frappe v16 app and tagged release package.
- DocTypes, workflows, roles, permissions, Workspace, notifications, charts, reports, print formats, and patches.
- Automated test suite and test results.
- Data dictionary, role matrix, workflow matrix, and source-to-target migration mapping.
- Import templates, migration scripts, and reconciliation report.
- Deployment/rollback runbook and backup/restore procedure.
- Administrator configuration guide and role-based user guide.
- Training session and four-week hypercare issue log.

## 16. Recommended post-release roadmap

### Release 1.1

- Bulk renewal initiation and reassignment.
- SLA aging/escalation for pending approvals.
- Enhanced audit and data-quality dashboards.
- Teams adaptive cards or two-way approval links, subject to security review.

### Release 1.2

- ERPNext Supplier, Department, Cost Center, Purchase Invoice, and Payment Entry integration.
- Budget-versus-rent analysis and payment reconciliation.
- Exchange-rate conversion with dated rates.

### Release 2

- Landlord portal, e-signature, OCR extraction, advanced document retention, and predictive rent/expiry analysis.

## 17. Immediate next steps

1. Approve Frappe v16 as the deployment baseline and confirm hosting model.
2. Nominate product owner and representatives from Administration/Facilities, Finance, Legal, IT, and Management.
3. Run the discovery workshop and approve the workflow/role matrix.
4. Profile the existing lease register and document archive.
5. Confirm Release 1 scope and acceptance criteria.
6. Create the app repository, Bench development site, backlog, and delivery calendar.

## 18. Official Frappe references used for technical validation

- [Frappe app structure and installation](https://docs.frappe.io/framework/user/en/basics/apps)
- [Bench commands](https://docs.frappe.io/framework/user/en/bench/bench-commands)
- [Frappe v16 installation requirements](https://docs.frappe.io/framework/user/en/installation)
- [Background jobs and scheduler events](https://docs.frappe.io/framework/user/en/api/background_jobs)
- [Notifications](https://docs.frappe.io/framework/notifications)
- [Users and permissions](https://docs.frappe.io/framework/user/en/basics/users-and-permissions)
- [File attachments](https://docs.frappe.io/framework/user/en/desk/attachments)
- [Desk, Workspace, views, and timeline](https://docs.frappe.io/framework/user/en/desk)
- [Workflows](https://docs.frappe.io/erpnext/workflows)
- [Report Builder](https://docs.frappe.io/framework/user/en/desk/reports/report-builder)
- [Script Reports](https://docs.frappe.io/framework/user/en/guides/reports-and-printing/how-to-make-script-reports)
- [Frappe v16 migration notes](https://github.com/frappe/frappe/wiki/Migrating-to-version-16)

## Appendix A - Requirements traceability from the supplied plan

| Source requirement | Planned implementation | Verification |
|---|---|---|
| Centralized lease/rent information | Lease and related master/transaction DocTypes | Lease register UAT and reconciliation |
| Store property, landlord, dates, notice, rent, owner, status, documents | Lease model and attachments | Field-level acceptance tests |
| Active, expiring, expired, renewed, department views | Lists, filters, calendar, reports | View/filter UAT |
| 90/60/30/14/7-day and expired reminders | Reminder Policy and daily scheduler | Date-boundary automated tests |
| Email reminders | Notification templates and queued email | Delivery and failure test |
| Teams alert | Optional Teams webhook adapter | Integration test if enabled |
| Officer -> Department -> Finance -> Legal -> Management approval | Renewal Request Workflow | Role-based workflow tests |
| Total/active/expiring/renewed/expired/rent KPIs | Workspace cards, charts, and reports | KPI reconciliation |
| Quick links, recent activity, upcoming renewals, contacts | Workspace, timeline, reports, and contact records | Workspace UAT |
| IT/Admin/Finance/Legal/Management/read-only access | Frappe roles and permissions | Permission matrix tests |
| Version history, audit logs, retention | Track Changes, timeline, audit reports, operational policy | Audit UAT and backup/retention review |
| Create/edit/upload/remind/approve/report/permission/expiry tests | Automated and manual test strategy | Test report and UAT sign-off |
| Training, guides, first-month monitoring | Documentation, training, four-week hypercare | Handover acceptance |

