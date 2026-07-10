# Rent Renewal Tracker

Rent Renewal Tracker is a standalone Frappe Framework v16 application for
managing properties, landlords, leases, rent obligations, renewal approvals,
documents, and expiry reminders. ERPNext is not required.

## Current foundation

The first application slice provides:

- An installable Frappe app package and `Rent Renewal Tracker` module.
- Application roles created safely during installation.
- Property, Landlord, Lease Department, Lease, Rent Schedule, and Lease Document DocTypes.
- Server-side notice-date, expiry, rent, and occupancy-cost calculations.
- Private-file, attachment-ownership, extension, and file-size controls for lease documents.
- Daily scheduled jobs that refresh time-dependent lease and rent-schedule values.
- A native Department, Finance, Legal, and Management renewal approval workflow.
- Immutable renewal snapshots, decision history, open-cycle uniqueness, and successor leases.
- Configurable expiry thresholds, overdue escalation, queued delivery, retries, and reminder logs.
- A permission-aware Frappe Apps entry, operational Workspace, calendars, and status indicators.
- Upcoming Expiries, Renewal Pipeline, Upcoming Payments, Rent Exposure, and Reminder Delivery reports.
- Frappe integration tests for the core lease rules.

The complete delivery scope and phased plan are in
[`docs/FRAPPE_APP_DEVELOPMENT_PLAN.md`](docs/FRAPPE_APP_DEVELOPMENT_PLAN.md).
Bench installation, testing, upgrade, and rollback commands are in
[`docs/BENCH_DEPLOYMENT.md`](docs/BENCH_DEPLOYMENT.md).

## Requirements

- Frappe Framework v16.x
- Python 3.14+
- Node.js 24+
- A supported Frappe Bench environment on Linux, WSL, or containers

## Install in Bench

From the Bench directory:

Use the explicit `rent_renewal_tracker` app name when fetching this repository. The GitHub repository name contains hyphens, but Bench and Frappe asset builds expect the cloned app folder to match the Python module name.

```bash
bench get-app rent_renewal_tracker https://github.com/thekingchild/Rent-Renewal-Tracker --branch master
bench --site <site-name> install-app rent_renewal_tracker
bench --site <site-name> migrate
bench --site <site-name> list-apps
```

For local app development, place this repository under `frappe-bench/apps`,
then install it editable through Bench before running `install-app`.

## Test

```bash
bench --site <test-site> run-tests --app rent_renewal_tracker
```

## License

MIT
