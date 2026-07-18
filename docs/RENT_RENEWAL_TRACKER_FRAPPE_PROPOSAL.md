# Proposal for Rent Renewal Tracker Frappe App Development

**Proposed app name:** `rent_renewal_tracker`  
**Target platform:** Frappe Framework v16.x  
**Deployment model:** Installable Frappe Bench app  
**Prepared:** 10 July 2026  
**Status:** Draft proposal for review and approval

## 1. Executive Summary

This proposal recommends the development of a dedicated Rent Renewal Tracker application on the Frappe Framework. The application will provide a centralized, auditable, and role-controlled system for managing leases, property records, landlord details, rent schedules, lease documents, renewal approvals, reminders, and management reporting.

The proposed solution will be delivered as a standalone Frappe Bench app that can be installed on a supported Frappe site. It will use native Frappe capabilities such as DocTypes, Workflows, Roles, Permissions, Notifications, Scheduler Jobs, Reports, Dashboard Charts, Workspace navigation, private file attachments, and audit trails.

The main goal is to prevent missed renewal deadlines, improve visibility over rent obligations, standardize approval decisions, and give management a reliable view of upcoming expiries and financial exposure.

## 2. Project Objectives

The Rent Renewal Tracker will be developed to achieve the following objectives:

1. Create one reliable lease and rent renewal register for the organization.
2. Track properties, landlords, lease terms, documents, rent values, renewal status, and responsible officers.
3. Send automated reminders before lease expiry and escalate overdue renewals.
4. Enforce a structured renewal approval workflow across responsible officers, department heads, Finance, Legal, and Management.
5. Provide dashboards and reports for active leases, expiring leases, expired leases, renewed leases, upcoming payments, and total rent exposure.
6. Improve accountability through role-based access, workflow history, reminder logs, and audit reporting.
7. Deliver an app that is installable, maintainable, testable, and upgrade-ready within a Frappe Bench environment.

## 3. Proposed Solution

The proposed solution is a custom Frappe application named `rent_renewal_tracker`. It will be developed as a standalone app with no dependency on ERPNext for Release 1. ERPNext integration can be introduced later if the organization wants accounting, supplier, cost center, purchase invoice, or payment-entry integration.

The app will include:

- A Rent Renewal Tracker Workspace for everyday navigation.
- Property, Landlord, Lease Department, Lease, Rent Schedule, Lease Document, Renewal Request, Reminder Policy, Reminder Log, and Rent Renewal Settings records.
- Private file attachment management for lease agreements, addenda, approval documents, renewal letters, receipts, correspondence, and related records.
- Automated reminder rules for 90, 60, 30, 14, and 7 days before expiry, expiry-day alerts, and overdue escalation.
- A configurable renewal approval process.
- Operational list views, calendar views, dashboard cards, dashboard charts, and exportable reports.
- Role-based access for lease administrators, responsible officers, department heads, Finance, Legal, Management, auditors, viewers, and system managers.
- Installation, deployment, migration, testing, and user documentation.

## 4. Scope of Work

### In Scope

- Design and development of the Frappe app.
- App installation support for a supported Frappe v16 Bench site.
- Lease, property, landlord, rent schedule, renewal, reminder, document, and settings modules.
- Workflow configuration for lease renewal review and approval.
- Automated reminder and escalation engine.
- Email and Frappe in-app notifications.
- Workspace, reports, number cards, charts, saved filters, and list indicators.
- Role and permission setup.
- Private document attachment controls.
- Data import templates and migration support for agreed source records.
- Automated and manual testing.
- Administrator guide, user guide, deployment runbook, and training support.
- Go-live support and hypercare period.

### Out of Scope for Release 1

- Bank payment execution.
- General ledger posting.
- Landlord self-service portal.
- Electronic signature integration.
- OCR or AI extraction of lease terms.
- SMS or WhatsApp notifications.
- Advanced document retention workflows.
- Full accounting integration.
- GIS/location visualization beyond basic location fields.

These items may be added in later releases after the core tracker is live and stable.

## 5. Key Functional Modules

### Property Management

The app will maintain a property register covering property name, type, location, address, region, responsible department, responsible officer, occupancy status, and notes.

### Landlord Management

The landlord register will store legal name, contact information, address, preferred currency, compliance notes, and active status. It will allow the organization to track leases by landlord and avoid duplicated counterparty records.

### Lease Register

The lease register will be the main contract record. It will capture property, landlord, lease title, lease type, start date, end date, notice period, notice deadline, renewal option, responsible department, responsible officer, currency, rent basis, monthly rent, annual rent, payment frequency, current lease status, renewal status, and supporting comments.

The app will calculate key dates and statuses server-side so reporting and reminders remain consistent.

### Rent Schedule

The rent schedule module tracks planned rent obligations, due dates, period covered, service charge, tax, total due, individual payment evidence, total paid, outstanding balance, and derived payment status. Supported Monthly and Annual lease terms can supply installment defaults using the lease payment frequency; unsupported bases remain manual. Release 1 records payment evidence and reconciliation status only; it does not execute bank payments or post accounting entries.

### Lease Documents

Lease documents will be attached as private files and categorized using document metadata. Categories may include signed agreement, addendum, renewal letter, approval, payment receipt, valuation, correspondence, and other supporting documents.

### Renewal Requests

Renewal requests will represent each renewal cycle. Each request will include current lease details, proposed new terms, recommendation, business justification, budget impact, risk, supporting documents, approval status, final decision, and completion details.

Only one open renewal request will be allowed for a lease renewal cycle.

### Reminder Policy and Logs

Reminder policies will define reminder thresholds, recipients, channels, escalation rules, templates, and stop conditions. Reminder logs will record every reminder attempt, including recipient, threshold, channel, status, retry count, sent time, and error summary.

This creates a clear operational record of what was sent, when it was sent, and whether it succeeded.

## 6. Renewal Approval Workflow

The default approval workflow will follow this sequence:

| Stage | Acting Role | Outcome |
|---|---|---|
| Draft | Responsible Officer or Lease Administrator | Prepare renewal request |
| Department Review | Department Head | Approve or return |
| Finance Review | Finance Approver | Approve or return |
| Legal Review | Legal Approver | Approve or return |
| Management Approval | Management Approver | Approve or reject |
| Approved | Lease Administrator | Mark executed |
| Completed | System record | Renewal cycle closed |

Workflow controls will include:

- Mandatory comments for returns and rejections.
- Role-based approval permissions.
- Prevention of unauthorized workflow transitions.
- Final execution requirements before completion.
- Complete workflow history with actor, date, status, and comment trail.

## 7. Reminder and Escalation Design

The app will include a scheduled reminder service that runs daily. It will identify leases approaching expiry, determine the applicable threshold, resolve recipients, send notifications, and record delivery attempts.

Default reminder thresholds will be:

- 90 days before expiry.
- 60 days before expiry.
- 30 days before expiry.
- 14 days before expiry.
- 7 days before expiry.
- Expiry day.
- Overdue escalation after expiry.

The reminder engine will be designed to avoid duplicate messages for the same lease, renewal cycle, threshold, channel, and recipient.

## 8. Dashboards and Reports

The app will include reports and dashboard views for:

- Total leases.
- Active leases.
- Expiring leases.
- Expired leases.
- Renewed leases.
- Renewals awaiting action.
- Rent exposure by currency, property, landlord, region, and department.
- Expiry exposure by month and quarter.
- Renewal pipeline by approval stage.
- Upcoming rent payments.
- Overdue renewals.
- Reminder delivery and failures.
- Lease data completeness exceptions.
- Audit changes on critical fields.

Currency totals will be separated unless the organization approves a specific exchange-rate rule.

## 9. Security and Audit

The app will use Frappe roles, permissions, user permissions, private file controls, and track changes to protect lease data.

Proposed roles include:

- Rent Renewal System Manager.
- Lease Administrator.
- Responsible Officer.
- Department Head.
- Finance Approver.
- Legal Approver.
- Management Approver.
- Lease Auditor.
- Lease Viewer.

Audit features will include:

- Track Changes on key records.
- Workflow history.
- Reminder logs.
- Document upload history.
- Created and modified timestamps.
- User activity trail.
- Reports for changes to critical fields such as lease dates, rent values, landlord, status, approver, and reminder policy.

## 10. Technical Approach

The app will be built using Frappe Framework v16.x. Development will follow Frappe app conventions so the application can be installed, migrated, backed up, tested, and upgraded using Bench commands.

Planned technical components include:

- Custom DocTypes for master and transaction records.
- Server-side validations and calculations.
- Workflow definitions.
- Notification templates.
- Scheduler jobs and background queue processing.
- Workspace, reports, charts, and number cards.
- Fixtures or standard application artifacts for repeatable installation.
- Versioned patches for future schema and data changes.
- Automated tests for installation, permissions, validations, workflow, reminders, reports, and file security.

Planned installation flow:

```bash
cd frappe-bench
bench get-app rent_renewal_tracker https://<git-host>/<organization>/Rent-Renewal-Tracker --branch <branch>
bench --site <site-name> install-app rent_renewal_tracker
bench --site <site-name> migrate
bench --site <site-name> enable-scheduler
bench --site <site-name> list-apps
```

## 11. Delivery Plan

The estimated delivery duration is approximately 9 weeks, assuming timely stakeholder decisions, access to sample lease data, and availability of reviewers for user acceptance testing.

| Phase | Duration | Key Activities | Output |
|---|---:|---|---|
| Discovery and validation | 1 week | Confirm requirements, data fields, workflow, reports, hosting, and acceptance criteria | Signed requirements and delivery backlog |
| App foundation | 1 week | Scaffold app, create module, setup roles, settings, masters, and install hooks | Installable app foundation |
| Lease register and documents | 1.5 weeks | Build Property, Landlord, Lease, Lease Document, validations, views, and file controls | Working lease register |
| Rent schedules and operational views | 0.5 week | Build rent schedules, due states, filters, and operational lists | Payment and rent tracking views |
| Renewal workflow | 1.5 weeks | Build Renewal Request, workflow, approvals, returns, rejections, and execution logic | End-to-end approval flow |
| Reminder engine | 1 week | Build policies, scheduler job, notification templates, retries, logs, and escalation | Automated reminders and audit logs |
| Dashboards and reports | 1 week | Build Workspace, reports, cards, charts, exports, and audit reports | Management reporting pack |
| Migration, testing, and UAT | 1 week | Import templates, trial migration, security tests, UAT, and fixes | UAT-ready release |
| Deployment and handover | 0.5 week | Production deployment, smoke testing, training, and handover | Live app and support start |

## 12. Testing and Acceptance

Testing will cover:

- Clean app installation on a supported Frappe site.
- Role and permission behavior.
- Lease creation, update, activation, expiry, termination, and renewal.
- Date calculations and notice deadlines.
- Rent calculations and currency separation.
- Reminder thresholds, retries, failures, and duplicate prevention.
- Workflow approvals, returns, rejections, and completion.
- Private file access and unauthorized access prevention.
- Report totals and dashboard reconciliation.
- Data import and reconciliation.
- Backup and restore rehearsal before production go-live.

Release 1 will be accepted when:

1. The app installs successfully using documented Bench commands.
2. Authorized users can manage lease records and unauthorized users cannot access restricted data.
3. Lease notice dates, expiry statuses, and next actions are calculated correctly.
4. Reminders are sent at approved thresholds without duplication.
5. Renewal approvals follow the agreed workflow and preserve history.
6. Reports and dashboards reconcile with test and migrated data.
7. Agreed legacy records and documents are imported with reconciliation sign-off.
8. User acceptance testing, security checks, and backup/restore rehearsal are completed.
9. Administrator guide, user guide, deployment runbook, and training materials are delivered.

## 13. Deployment and Handover

The deployment process will include:

- Development, UAT/staging, and production environments.
- App installation and migration on the production site.
- Site configuration for timezone, currency, email, scheduler, file limits, roles, and reminder policies.
- Final data import and reconciliation.
- Smoke testing after deployment.
- User training and administrator handover.
- Four-week hypercare support window after go-live.

Operational monitoring will include scheduler status, queue failures, email failures, overdue renewals, failed reminder logs, backup success, storage growth, and permission changes.

## 14. Project Deliverables

The project will deliver:

- Git repository for the `rent_renewal_tracker` app.
- Installable Frappe Bench app.
- DocTypes, workflows, roles, permissions, notifications, reports, charts, Workspace, and print formats.
- Automated test suite.
- Data dictionary and role matrix.
- Workflow matrix.
- Import templates and migration support scripts.
- Data reconciliation report.
- Deployment and rollback runbook.
- Administrator guide.
- User guide.
- Training session.
- Four-week hypercare issue log.

## 15. Key Assumptions

- Frappe Framework v16.x will be the target platform.
- The organization will provide sample lease records and documents for validation.
- A product owner will be available to approve requirements and resolve questions.
- Department, Finance, Legal, and Management representatives will validate the approval workflow.
- Email sending infrastructure will be available and configured before UAT.
- Production hosting, backup, recovery, and security policies will be confirmed before go-live.
- Any external integrations beyond email and standard Frappe notifications will be treated as separate scope unless approved during discovery.

## 16. Risks and Mitigation

| Risk | Potential Impact | Mitigation |
|---|---|---|
| Incomplete lease data | Incorrect reminders or reports | Profile data early and define cleansing responsibilities |
| Unclear approval rules | Rework and delayed sign-off | Approve workflow matrix before build |
| Disabled scheduler or queue workers | Missed reminders | Add health checks and operational monitoring |
| Email delivery issues | Stakeholders miss notifications | Test email configuration during UAT and keep in-app notifications enabled |
| Attachment permission gaps | Confidentiality risk | Use private files and run negative access tests |
| Mixed currencies in reports | Misleading totals | Separate totals by currency unless exchange rules are approved |
| Broad user permissions | Workflow bypass or data exposure | Use least privilege permissions and role-based testing |
| Framework upgrades | Regression risk | Pin versions, test patches in staging, and use tagged releases |

## 17. Recommended Next Steps

1. Approve Frappe v16.x as the development and deployment baseline.
2. Confirm hosting model and target Bench environment.
3. Nominate product owner and stakeholder reviewers.
4. Confirm Release 1 scope and out-of-scope items.
5. Run discovery workshop for fields, workflow, roles, reports, reminders, and migration.
6. Approve project timeline and begin app development.
