# Rent Renewal Tracker User Guide

Version: 1.4

Prepared: 16 July 2026

## 1. Purpose

Rent Renewal Tracker is a Frappe-based application for managing the full lease lifecycle from property setup to lease monitoring, rent payment scheduling, renewal approvals, supporting documents, and reminder delivery.

This guide explains how end users can work with the application from the `Rent Renewal Tracker` workspace in the app menu.

## 2. What the App Covers

The application helps teams:

- Register properties, landlords, and lease departments.
- Create and maintain lease records.
- Track notice deadlines, expiry dates, next action dates, and occupancy cost.
- Store private lease-related documents.
- Manage rent schedules and payment follow-up.
- Run a controlled multi-stage lease renewal approval process.
- Send automated pre-expiry and overdue reminders.
- Review operational reports for expiries, renewals, payments, exposure, and reminder delivery.

## 3. Access and Roles

Access to screens and actions depends on user role. The main roles used by the app are:

- `Rent Renewal System Manager`: Full setup, configuration, and administrative access.
- `Lease Administrator`: Maintains operational records and can complete approved renewals.
- `Responsible Officer`: Creates and manages leases, rent schedules, documents, and renewal requests.
- `Department Head`: Reviews and returns or approves renewal requests at department stage.
- `Finance Approver`: Reviews and returns or approves renewal requests at finance stage.
- `Legal Approver`: Reviews and returns or approves renewal requests at legal stage.
- `Management Approver`: Gives final approval or rejection.
- `Lease Auditor`: Read-only audit and report access.
- `Lease Viewer`: Basic read-only access.

If a menu item is missing, the usual cause is role-based permission rather than a system error.

Role permission makes a DocType available, while record-level authorization determines which specific records the user may open or change. Lease assignment, Lease Department User Permissions, and confidentiality clearance are rechecked when a record is opened or saved.

## 4. Opening the App

After signing in to Frappe:

1. Open the app launcher or desk menu.
2. Select `Rent Renewal Tracker`.
3. The workspace opens with four shortcuts:
   - `Leases`
   - `Renewals`
   - `Payments`
   - `Documents`

The dashboard also shows permission-aware cards for upcoming expiries, renewals waiting for
the current user, overdue rent, failed reminders, and annual rent exposure. Select a card to
open the corresponding filtered report.

The workspace also groups links under three sections:

- `Operations`
- `Registers and Setup`
- `Reports`

## 5. Workspace Navigation

### Operations

Use this section for day-to-day records:

- `My Actions`
- `Leases`
- `Renewal Requests`
- `Rent Schedules`
- `Lease Documents`

### Registers and Setup

Use this section for master data and reminder controls:

- `Setup Readiness`
- `Properties`
- `Landlords`
- `Lease Departments`
- `Reminder Policies`
- `Reminder Logs`
- `Settings`

### Reports

Use this section for monitoring and management review:

- `Upcoming Expiries`
- `Renewal Pipeline`
- `Upcoming Payments`
- `Rent Exposure`
- `Reminder Delivery`

## 6. Recommended Setup Sequence

For a new implementation, create records in this order:

1. `Lease Departments`
2. `Properties`
3. `Landlords`
4. `Rent Renewal Settings`
5. `Reminder Policies` if the default policy needs adjustment
6. `Leases`
7. `Lease Documents`
8. `Rent Schedules`

This order reduces lookup errors while creating transactional records.

Use `Setup Readiness` to confirm that departments, assigned users, a reminder policy, outgoing
email, properties, and leases are configured. The weekly management digest is optional and is
enabled from `Rent Renewal Settings` after valid recipient email addresses are entered.

## 7. Master Data Setup

### 7.1 Lease Departments

Open `Registers and Setup > Lease Departments` to maintain the list of departments responsible for leases.

Important fields:

- `Department Name`
- `Department Code`
- `Disabled`
- `Description`

Use department records to assign operational ownership on properties and leases.

### 7.2 Properties

Open `Registers and Setup > Properties` to register each leased or managed location.

Important fields:

- `Property Name`
- `Property Type`
- `Active`
- `Address`, `City`, `State`, `Country`, `Region`
- `Latitude`, `Longitude`
- `Responsible Department`
- `Default Responsible Officer`
- `Occupancy Status`
- `Notes`

Tips:

- Keep the `Region` field consistent because it is reused in lease reporting.
- Assign a default department and officer where possible to simplify lease setup.

### 7.3 Landlords

Open `Registers and Setup > Landlords` to create landlord or lessor records.

Important fields:

- `Legal Name`
- `Registration / Tax Identifier`
- `Active`
- `Contact Name`
- `Email`
- `Phone`
- `Address`
- `Preferred Currency`
- `Compliance Notes`

Use `Compliance Notes` for legal or vendor-risk remarks where that permission level is available.

## 8. Application Settings

Open `Registers and Setup > Settings` to manage default behavior.

Important settings:

- `Default Reminder Policy`
- `Expiring Soon Threshold (Days)`
- `Default Currency`
- `Timezone`
- `Email Sender`
- `Reminder Retry Limit`
- `Administrator Error Recipients`
- `Create Renewal Request at First Threshold`

How these settings work:

- `Expiring Soon Threshold` controls when active leases are automatically classified as expiring soon.
- `Reminder Retry Limit` controls how many times the system retries a failed reminder delivery.
- `Administrator Error Recipients` receives failure alerts when reminder delivery cannot be completed.
- `Create Renewal Request at First Threshold` allows the system to open a renewal request automatically at the earliest enabled threshold.

## 9. Reminder Policies

Open `Registers and Setup > Reminder Policies` to configure reminder timing, channels, and recipients.

Important fields:

- `Policy Name`
- `Enabled`
- `Reminder Thresholds`
- `Overdue Cadence (Days)`
- `Email Enabled`
- `System Notification Enabled`
- `Recipients`
- `Subject Template`
- `Message Template`

### Reminder Thresholds

Each threshold row defines how many days before expiry a reminder should be triggered. A default installation creates thresholds at:

- 90
- 60
- 30
- 14
- 7
- 0

### Recipients

Recipient rows support:

- `Lease User Field`
- `Lease Contact Type`
- `Role`
- `Explicit User`
- `Email`

Scope can be:

- `All`
- `Pre-Expiry`
- `Expiry`
- `Overdue`

Example:

- Send all reminders to the `responsible_officer`.
- Send overdue reminders to the `backup_officer`.
- Send legal-stage reminders to contacts tagged as `Legal`.

## 10. Creating and Managing Leases

Open `Operations > Leases`.

### 10.1 Create a New Lease

1. Click `Add Lease`.
2. Complete the key sections.
3. Save the record.

The save operation applies both the role permission and the record-level lease scope:

- `Rent Renewal System Manager` and `Lease Administrator` may create a Lease without being assigned to it because they are unrestricted operational roles.
- A `Responsible Officer` may create a Lease only when the new record assigns that user as Responsible Officer, Contract Owner, or Backup Officer, or the user has a matching Lease Department User Permission. The selected confidentiality classification must also be within the user's clearance.

Lease Documents, Rent Schedules, Renewal Requests, and Reminder Logs repeat the parent Lease authorization check through their required `Lease` link. Lease Documents additionally enforce their own `Confidentiality` field, so access must pass both the parent Lease classification and the linked document classification.

### 10.2 Lease Identity Section

Core fields:

- `Lease Title`
- `Property`
- `Landlord`
- `Lease Type`
- `External / Contract Reference`

The system names leases automatically using the pattern `LEASE-.YYYY.-#####`.

### 10.3 Ownership Section

Use this section to assign accountability:

- `Responsible Department`
- `Responsible Officer`
- `Contract Owner`
- `Backup Officer`
- `Reminder Policy`
- `Lease Contacts`

The `Region` field is auto-filled from the selected property.

#### Responsible Officer versus Contract Owner

The `Responsible Officer` is the required day-to-day operational owner of the lease. This user is the primary person expected to monitor dates, maintain the lease and its related records, initiate lifecycle action, and respond to reminders. The default reminder policy sends all lease-expiry reminders to this field, and operational views use it when identifying the officer responsible for an expiring lease.

The `Contract Owner` is an optional additional accountable user for the underlying commercial or business relationship. Use it when business ownership sits with a different person from the officer performing routine lease administration—for example, a business-unit sponsor, property portfolio owner, or contract relationship lead. A Contract Owner receives record access to the lease and its related renewal requests, rent schedules, documents, and reminder logs. Reminder policies may also target the `contract_owner` field when explicitly configured.

The application does not assign a separate approval stage or automatic reminder to the Contract Owner merely because the field is populated. Workflow authority still comes from the approver's role and lease access. If the same person performs both functions, enter that user as Responsible Officer and leave Contract Owner blank, or enter the same user in both fields if your reporting convention requires explicit business ownership.

### 10.4 Lease Contacts

Contacts are entered in a child table with:

- `Contact Type`
- `Name`
- `Organization`
- `Email`
- `Phone`
- `Receives Reminders`
- `Notes`

Contact types include `Landlord`, `Legal`, `Facility`, `Finance`, `Escalation`, and `Other`.

Use the `Receives Reminders` checkbox for contacts who should be eligible when the reminder policy uses `Lease Contact Type`.

### 10.5 Term Section

Important fields:

- `Start Date`
- `End Date`
- `Notice Period (Days)`
- `Renewal Option`
- `Renewal Option Deadline`
- `Break Clause Date`
- `Auto Renew`

System-calculated fields:

- `Notice Deadline`
- `Days to Expiry`
- `Next Action Date`

The system calculates:

- `Notice Deadline` as `End Date - Notice Period`.
- `Days to Expiry` from the current date.
- `Next Action Date` as the earliest of notice deadline, renewal option deadline, or break clause date.

### 10.6 Financial Terms Section

Important fields:

- `Currency`
- `Rent Basis`
- `Monthly Rent`
- `Annual Rent`
- `Payment Frequency`
- `Security Deposit`
- `Annual Service Charge`
- `Annual Tax`
- `Escalation / Indexation Rule`

System-calculated field:

- `Total Annual Occupancy Cost`

If `Rent Basis` is `Monthly` and `Monthly Rent` is entered, the system calculates `Annual Rent` automatically.

### 10.7 Status Section

Lease status values include:

- `Draft`
- `Active`
- `Expiring Soon`
- `Renewal in Progress`
- `Renewed`
- `Expired`
- `Terminated`

Renewal status values include:

- `Not Started`
- `Draft`
- `Pending Approval`
- `Approved`
- `Rejected`
- `Completed`
- `Not Renewing`

Several status values are controlled automatically by date logic and workflow progress.

### 10.8 Validation Rules

The system prevents:

- End dates earlier than or equal to start dates.
- Negative notice periods.
- Negative monetary values.
- Active leases without core ownership, date, currency, and rent information.

## 11. Lease Documents

Open `Operations > Lease Documents`.

Use this screen to store supporting files in private storage.

Important fields:

- `Lease`
- `Title`
- `Category`
- `Private File`
- `Document Date`
- `Effective Date`
- `Expiry Date`
- `Version Label`
- `Confidentiality`
- `Uploaded By`
- `Notes`

### 11.1 What Document Confidentiality Means

The Lease Document `Confidentiality` field labels the sensitivity of that specific file as `Internal`, `Confidential`, or `Restricted`. It is useful for records management, review, and handling instructions. It is separate from the parent Lease field named `Confidentiality Classification`, which supports `Public`, `Internal`, `Confidential`, and `Restricted`.

Lease Document access is the intersection of the user's DocType role permission, linked Lease assignment or department scope, parent Lease confidentiality clearance, and the document's own confidentiality clearance. A user can open the Lease but still be denied a more restricted Lease Document. The same decision protects the private File attached to that document.

The effective boundary is the stricter combination of parent and child controls. Users cannot create a Lease Document above their own clearance, and changing assignments or Lease Department User Permissions on the parent Lease immediately affects access to its linked documents. Classify the parent lease for the overall relationship and classify each document for the sensitivity of that specific evidence.

Role effects are:

- `Rent Renewal System Manager` and `Lease Administrator` can read, create, edit, delete, print, email, and export Lease Document records, subject to the private-file controls. These roles are unrestricted by the lease assignment and confidentiality filter.
- `Responsible Officer` can read, create, edit, and print documents for authorized leases when both the parent and document are within the role's Public, Internal, or Confidential clearance. The role cannot delete, email, or export through the configured DocType permissions.
- `Department Head` and `Finance Approver` have read-and-print access to authorized documents through Confidential. They cannot create revisions because they lack Lease Document create and write permission.
- `Legal Approver` and `Management Approver` have read-and-print clearance through Restricted, while assignment or Lease Department scope still applies.
- `Lease Auditor` has read, print, and export clearance through Restricted; assignment or department scope still applies.
- `Lease Viewer` has read-and-print access only to authorized Internal documents on parent leases within the role's Public or Internal clearance.

### 11.2 Who Can Create a Lease Document?

Under the application's default DocType permissions:

- `Administrator` can create a Lease Document linked to any existing Lease because Frappe grants Administrator a permission bypass.
- `Rent Renewal System Manager` and `Lease Administrator` can create a Lease Document linked to any existing Lease. These roles bypass Lease assignment, department scope, and confidentiality filters.
- `Responsible Officer` can create a Lease Document only when the linked Lease is within the user's assignment or Lease Department scope and both the parent Lease and the document are within the user's confidentiality clearance.
- `System Manager` by itself cannot create a Lease Document. The role bypasses the application's record-level Lease filters, but it does not have Lease Document create permission in the default DocType permission matrix. The user must also hold `Rent Renewal System Manager`, `Lease Administrator`, `Responsible Officer`, or an explicitly configured custom create permission.
- `Department Head`, `Finance Approver`, `Legal Approver`, `Management Approver`, `Lease Auditor`, and `Lease Viewer` cannot create Lease Documents with only those roles. Their default Lease Document access is read-oriented.

The `Lease` field is mandatory and must link to a saved Lease. Being named as Responsible Officer, Contract Owner, Backup Officer, a Lease contact, or an approver does not by itself grant Lease Document creation. The user must first have a role that grants Lease Document create permission.

### 11.3 Exact Linked-Lease Requirements for a Responsible Officer

A user relying on the `Responsible Officer` role must satisfy at least one of these scope conditions on the selected Lease:

- The user's account is entered in `Responsible Officer`.
- The user's account is entered in `Contract Owner`.
- The user's account is entered in `Backup Officer`.
- The user has a Frappe User Permission with `Allow` set to `Lease Department`, `For Value` matching the Lease's `Responsible Department`, and `Applicable For` set to `Lease` or left blank.

Scope alone is not sufficient. A user with only the `Responsible Officer` role has clearance for Public, Internal, and Confidential parent Leases and for Internal and Confidential Lease Documents. That role cannot create a Restricted Lease Document or create against a Restricted Lease.

Frappe combines permissions from all roles assigned to a user. For example, a user who has both `Responsible Officer` and `Legal Approver`, `Management Approver`, or `Lease Auditor` receives Lease Document create permission from `Responsible Officer` and Restricted clearance from the additional role. The user can then create a Restricted Lease Document for a Restricted Lease only when the assignment or Lease Department scope condition is also satisfied.

Every attached file must also be private. The application checks the user's permission to use the File record, its owner or original attachment, the allowed file extension, and the site's maximum file size. After attachment, Frappe resolves private-file access through the Lease Document, so the linked Lease scope and document confidentiality rule also govern file reads and downloads.

### 11.4 Creating and Controlling Revisions

The `Create Revision` action appears only for a current revision when the user can create Lease Documents and can write the current record. The new record receives its name before the application assigns Document Family ID, Revision number, Revised By, and Revised On through Frappe's validation lifecycle. A revision must use a different private file, remain on the same Lease, include a Revision Reason, and branch from the current revision. Saving it updates the previous revision through the normal Frappe save lifecycle, including permission checks and change tracking, and marks the previous revision `Superseded`.

Document classifications and revision permissions are enforced on direct API requests as well as the Desk form; hiding the button is only a usability aid.

Document categories include:

- `Signed Agreement`
- `Addendum`
- `Renewal Letter`
- `Approval`
- `Payment Receipt`
- `Valuation`
- `Correspondence`
- `Other`

Important rule:

- A completed renewal requires a private supporting document before the workflow can be finalized.
- If the recommendation is not `Terminate`, the required category is `Renewal Letter`.
- If the recommendation is `Terminate`, the required category is `Approval`.

## 12. Rent Schedules and Payment Tracking

Open `Operations > Rent Schedules`.

Use rent schedules to track planned payment obligations by lease and period.

### 12.1 Key Fields

- `Lease`
- `Description`
- `Period From`
- `Period To`
- `Due Date`
- `Currency`
- `Base Rent`
- `Service Charge`
- `Tax`
- `Total Due`
- `Payment Status`
- `Schedule Status`
- `Payment Reference`
- `Paid On`
- `Notes`

### 12.2 System Behavior

The system calculates `Total Due` as:

- `Base Rent + Service Charge + Tax`

The system also derives `Schedule Status` automatically:

- `Planned` if due date is in the future
- `Due` if due today
- `Overdue` if due date has passed and not settled
- `Paid` if payment status is `Paid`
- `Waived` if payment status is `Waived`
- `Cancelled` if the record is cancelled

### 12.3 Validation Rules

The system prevents:

- Period end before period start
- Rent periods outside the parent lease start and end dates
- Negative amounts
- Empty schedules with all zero amounts
- Currency mismatch between schedule and lease

## 13. Renewal Request Workflow

Open `Operations > Renewal Requests`.

Use this screen to manage structured lease renewal decisions and approvals.

### 13.1 Who Can Start a Lease Renewal?

Under the application's default Renewal Request permissions:

- `Administrator` can create a Renewal Request for any Lease.
- `Rent Renewal System Manager` and `Lease Administrator` can create a Renewal Request without Lease assignment, department-scope, or confidentiality restrictions.
- `Responsible Officer` can create a Renewal Request only for a Lease within the user's assignment or Lease Department scope and confidentiality clearance.
- `System Manager` by itself cannot create a Renewal Request. Record-level filter bypass does not grant the Renewal Request create permission that is absent from the default DocType permission matrix.
- `Department Head`, `Finance Approver`, `Legal Approver`, `Management Approver`, `Lease Auditor`, and `Lease Viewer` cannot create a Renewal Request with only those roles.

The recommended operational path is:

1. Open a submitted Lease.
2. Open the `Lifecycle` menu.
3. Select `Start Renewal`.
4. Complete the proposed terms and recommendation in the generated Draft.
5. Save the request.
6. Use `Submit for Department Review`.

The `Start Renewal` action accepts only submitted Leases whose status is `Active`, `Expiring Soon`, or `Expired`. If an open renewal request already exists, the existing request opens. If an open termination request exists, it must be completed or cancelled first.

Create-enabled users can also use `Add Renewal Request` from the Renewal Request list. The current application applies the submitted/status eligibility check through the `Start Renewal` action, not through direct list creation, so operational users should use the Lease lifecycle action as the standard entry point.

The system automatically:

- Assigns the next `Renewal Sequence`.
- Captures a snapshot of the current lease terms.
- Defaults proposed values from the current lease.
- Fills `Requested By` and `Requested On`.

If `Create Renewal Request at First Threshold` is enabled in Rent Renewal Settings, the reminder engine may create a Draft automatically at the first configured reminder threshold. Human create permission is not used for that background action, but all subsequent record-scope and workflow-stage controls continue to apply.

### 13.2 Exact Linked-Lease Requirements

A user relying on the `Responsible Officer` role must satisfy at least one of these scope conditions:

- The user's account is entered in the Lease's `Responsible Officer`.
- The user's account is entered in `Contract Owner`.
- The user's account is entered in `Backup Officer`.
- The user has a Frappe User Permission with `Allow` set to `Lease Department`, `For Value` matching the Lease's `Responsible Department`, and `Applicable For` set to `Lease` or left blank.

A Responsible Officer alone has clearance for Public, Internal, and Confidential Leases, but not Restricted Leases. Frappe combines role clearances, so a Responsible Officer who also has `Legal Approver`, `Management Approver`, `Lease Auditor`, or an unrestricted operational role can receive Restricted clearance.

The same linked-Lease authorization is required for every scoped workflow approver. A workflow role does not by itself grant access to the Renewal Request. The approver must also be assigned to the Lease or hold the matching Lease Department User Permission and must have sufficient confidentiality clearance.

### 13.3 Workflow States

The renewal process follows this sequence:

1. `Draft`
2. `Department Review`
3. `Finance Review`
4. `Legal Review`
5. `Management Approval`
6. `Approved`
7. `Completed`

Possible exit state:

- `Rejected`

### 13.4 Who Acts at Each Stage

- `Draft`: `Responsible Officer` edits the proposal. `Responsible Officer` or `Lease Administrator` can submit it for Department Review.
- `Department Review`: `Department Head` can approve to Finance Review or return the request to Draft.
- `Finance Review`: `Finance Approver` can approve to Legal Review or return the request to Draft.
- `Legal Review`: `Legal Approver` can approve to Management Approval or return the request to Draft.
- `Management Approval`: `Management Approver` can approve the request or reject it.
- `Approved`: `Lease Administrator` can use `Mark Executed` to complete the renewal.

`Administrator` can perform all stages. `Rent Renewal System Manager` has broad Renewal Request DocType permissions and unrestricted record scope, but that role alone is not listed for a workflow transition. The user must also hold the role assigned to the current workflow action. Likewise, `Lease Administrator` can submit a Draft and execute an Approved request, but cannot replace the Department, Finance, Legal, or Management approver without also holding that stage's role.

Important control:

- The original requester cannot approve their own review stage.
- Return and Reject require a workflow comment.
- Role permissions and confidentiality clearances are combined when a user has multiple roles.
- Department Head and Finance Approver have clearance through Confidential. Acting on a Restricted Lease requires an additional role that supplies Restricted clearance or an unrestricted operational role.
- Legal Approver and Management Approver have Restricted clearance but still require Lease assignment or department scope unless they also hold an unrestricted operational role.

### 13.5 Proposal and Recommendation Fields

Important fields include:

- `Proposed Property`
- `Proposed Start Date`
- `Proposed End Date`
- `Proposed Notice Date`
- `Proposed Currency`
- `Proposed Rent Basis`
- `Proposed Monthly Rent`
- `Proposed Annual Rent`
- `Proposed Payment Frequency`
- `Proposed Escalation Rule`
- `Recommendation`
- `Business Justification`
- `Risk Assessment`
- `Budget Impact`
- `Alternative Options`

Recommendation values:

- `Renew`
- `Renegotiate`
- `Relocate`
- `Terminate`

### 13.6 Workflow Comments and Decision History

Use `Workflow Comment` whenever context is needed.

The system requires a comment when:

- Returning a request
- Rejecting a request

Every valid transition is written to `Decision History` with:

- from state
- action
- to state
- actor
- action date/time
- comment

### 13.7 Completion Behavior

When a request moves to `Completed`:

- The system checks that proposed lease dates exist.
- A current private `Renewal Letter` Lease Document must be linked to the same Lease and the exact Renewal Request and must have a Document Date.
- If the recommendation is not `Terminate`, the system creates a successor lease automatically if one does not already exist.
- The successor lease carries forward the main lease structure and uses the approved proposed terms.

Only `Lease Administrator` can perform the configured `Mark Executed` transition. Completing a termination uses a current private `Approval` document instead of a Renewal Letter.

### 13.8 Open-Cycle Control

Only one open renewal request is allowed per lease at a time. The system blocks creation of another active cycle until the previous one is completed, rejected, or cancelled.

### 13.9 Current Interface and Workflow Limitations

- The Lease form currently displays `Start Renewal` based on Lease status and submission state rather than checking Renewal Request create permission. A read-only user may see the button, but the server rejects unauthorized creation.
- `Rent Renewal System Manager` can create a Renewal Request but cannot progress it through workflow transitions with that role alone.
- Direct `Add Renewal Request` creation does not use the same submitted/status eligibility gate as the recommended `Start Renewal` lifecycle action.

## 14. Automated Status Updates

The app runs daily background jobs that:

- Refresh lease status and date-derived values.
- Refresh unpaid rent schedule statuses.
- Process due reminders.

This means:

- `Days to Expiry` stays current.
- `Expiring Soon`, `Expired`, and `Active` statuses update automatically.
- `Planned`, `Due`, and `Overdue` schedule statuses update automatically.

## 15. Reminder Processing

The reminder engine monitors leases that:

- are not `Draft`, `Renewed`, or `Terminated`
- are not in renewal status `Completed` or `Not Renewing`
- have an `End Date`

When a threshold is reached, the system:

1. Resolves the active reminder policy.
2. Determines whether that threshold is due.
3. Optionally creates a renewal request automatically at the first threshold.
4. Creates reminder log records.
5. Queues email and or in-app notification delivery.
6. Retries failed deliveries up to the configured retry limit.

After successful delivery, the lease updates:

- `Last Reminder Date`
- `Next Reminder Date`

## 16. Reports

### 16.1 Upcoming Expiries

Use this report to identify leases ending within a date range.

Helpful fields shown:

- Lease
- Title
- Property
- Landlord
- Department
- Officer
- End Date
- Days to Expiry
- Lease Status
- Renewal Status
- Next Action

Use it for weekly renewal planning and operational review meetings.

### 16.2 Renewal Pipeline

Use this report to track every renewal request in progress or completed.

Helpful fields shown:

- Renewal
- Lease
- Cycle
- Workflow State
- Pending With
- Age (Days)
- Recommendation
- Requested By
- Requested On
- Proposed Start and End
- Proposed Annual Rent

Use it to identify approvals that are ageing or stuck at a stage.

### 16.3 Upcoming Payments

Use this report to monitor unpaid obligations within a date range.

Helpful fields shown:

- Schedule
- Lease
- Description
- Period
- Due Date
- Days
- Currency
- Base Rent
- Service Charge
- Tax
- Total Due
- Status

By default, it excludes `Paid`, `Waived`, and `Cancelled` entries unless filters are changed.

### 16.4 Rent Exposure

Use this report for financial visibility across active and expiring leases.

Helpful fields shown:

- Lease
- Title
- Property
- Landlord
- Region
- Department
- Currency
- Monthly Rent
- Annual Rent
- Service Charge
- Tax
- Total Annual Cost
- Status
- End Date

If multiple currencies exist and no currency filter is applied, totals should be reviewed per currency rather than combined.

### 16.5 Reminder Delivery

Use this report to audit reminder operations.

Helpful outputs:

- Reminder log list
- Delivery status counts
- Donut chart of `Queued`, `Sent`, and `Failed`
- Delivery rate summary

Helpful fields shown:

- Log
- Lease
- Renewal
- Policy
- Threshold
- Scheduled Date
- Channel
- Recipient
- Status
- Sent At
- Retries
- Error

## 17. Common Operating Procedures

### 17.1 Register a New Lease

1. Confirm the `Property`, `Landlord`, and `Lease Department` already exist.
2. Create the lease and complete ownership, term, and financial fields.
3. Add lease contacts.
4. Save and confirm notice deadline and next action date.
5. Upload the signed agreement under `Lease Documents`.
6. Create the initial rent schedules.

### 17.2 Start a Renewal

1. Open the lease.
2. Review end date, notice deadline, and latest reminders.
3. Create a `Renewal Request`.
4. Adjust proposed terms and business justification.
5. Submit for department review.

### 17.3 Complete an Approved Renewal

1. Confirm the request is in `Approved`.
2. Upload the supporting `Renewal Letter` or `Approval` document.
3. Use `Mark Executed`.
4. Confirm the successor lease was created if applicable.
5. Add new rent schedules for the successor lease.

### 17.4 Close Out a Rejected or Terminated Renewal

1. Review the final comment and rejection reason.
2. Confirm whether the original lease should remain active until expiry or be treated as terminating.
3. Update supporting documents and notes as needed.

## 18. Troubleshooting Tips

- If a user cannot create or edit a Lease, verify their role, assignment or Lease Department User Permission, confidentiality clearance, and the current workflow or document state.
- If a renewal cannot be completed, check for the required `Lease Document` category.
- If a rent schedule will not save, confirm the currency matches the parent lease and the period stays within lease dates.
- If reminders are not sending, review `Settings`, the chosen `Reminder Policy`, and the `Reminder Delivery` report.
- If a lease status looks outdated, check whether the daily scheduler is running successfully.

## 19. Good Data Entry Practices

- Use consistent property names, regions, and department codes.
- Always assign a responsible department and officer.
- Enter either monthly rent or annual rent accurately and verify the derived amount.
- Keep lease contacts up to date, especially reminder recipients.
- Upload approval evidence before closing a renewal.
- Review upcoming expiries and upcoming payments at least weekly.

## 20. Summary

Rent Renewal Tracker is designed to give one controlled process for lease ownership, payment planning, renewal governance, and reminder visibility. The strongest results come from:

- clean setup data
- disciplined use of renewal workflow states
- timely document uploads
- active review of expiry and payment reports
- correct reminder policy configuration

With those controls in place, the app becomes a reliable operating register for lease administration and rent renewal management.
