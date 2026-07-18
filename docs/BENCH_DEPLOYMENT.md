# Frappe Bench Deployment

## Supported baseline

- Frappe Framework v16.x
- Python 3.14+
- Node.js 24+
- A Linux, WSL, or container-based Bench with its database and queue services running

The application depends only on Frappe; ERPNext is not required.

## Install

From the Bench directory, fetch the repository after its application files are committed.

Use the explicit `rent_renewal_tracker` app name when fetching this repository. The GitHub repository name contains hyphens, but Bench and Frappe asset builds expect the cloned app folder to match the Python module name.

```bash
bench get-app rent_renewal_tracker https://github.com/thekingchild/Rent-Renewal-Tracker --branch master
bench --site <site-name> install-app rent_renewal_tracker
bench --site <site-name> migrate
bench build --app rent_renewal_tracker
bench --site <site-name> clear-cache
```

Verify the installation contract:

```bash
bench --site <site-name> list-apps
bench --site <site-name> execute rent_renewal_tracker.health.verify_installation
```

The health command must return `true` for the app, DocTypes, roles, workflow primitives,
workflow, reminder defaults, Workspace, and reports.

## Test

Enable tests only on a development or disposable test site:

```bash
bench --site <test-site> set-config allow_tests true
bench --site <test-site> run-tests --app rent_renewal_tracker
```

The integration suite covers installation defaults, lease calculations, property-term overlap
protection, schedule financial defaults, partial payments and overpayment rejection, private
files, renewal cycles, successor leases, reminders, delivery retries, permissions-sensitive
report queries, and the Apps Page permission hook.

## Scheduler smoke test

```bash
bench --site <site-name> enable-scheduler
bench --site <site-name> execute rent_renewal_tracker.scheduled_tasks.refresh_lease_statuses
bench --site <site-name> execute rent_renewal_tracker.scheduled_tasks.refresh_rent_schedule_statuses
bench --site <site-name> execute rent_renewal_tracker.reminders.process_due_reminders
bench doctor
```

Configure an outgoing Email Account before expecting email reminder delivery. In-app alerts
use Frappe Notification Log and do not require an external email service.

## Upgrade

```bash
cd <frappe-bench>
bench update --apps rent_renewal_tracker
bench --site <site-name> migrate
bench build --app rent_renewal_tracker
bench --site <site-name> clear-cache
bench --site <site-name> execute rent_renewal_tracker.health.verify_installation
```

Schema and default-data changes are delivered through `patches.txt`; do not manually import
standard DocTypes or Workflow records during upgrades.

The safe lease and payment-controls migration also:

- Flags existing pairs of ongoing leases whose inclusive terms overlap for the same Property.
  It does not guess which legal record should be cancelled or terminated.
- Converts a legacy `Paid` schedule into one full-value historical payment row.
- Marks a legacy `Partially Paid` schedule for reconciliation without inventing a paid amount.
- Preserves existing Custom DocPerm rows and other site-specific permission customizations.

After migration, review `Setup Readiness > Lease Overlap Review`. Reconcile every flagged pair
against the signed agreements, then complete the appropriate termination/cancellation or correct
an inaccurate Property or term. Run the daily status refresh after resolving the source data:

```bash
bench --site <site-name> execute rent_renewal_tracker.scheduled_tasks.refresh_lease_statuses
```

## Rollback preparation

Before production installation or upgrade:

```bash
bench --site <site-name> backup --with-files
bench version
```

Record the Frappe and application commit IDs with the backup. Restore into a staging site and
run the health check before using that backup as a production rollback point.

