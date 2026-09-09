# Phase 13 — Documents & Notifications

EnterpriseOne now includes two connected enterprise services: document lifecycle management and event-driven notifications.

## Documents
- Tenant-scoped folders, categories, tags and templates.
- Document metadata, linked business records, visibility and lifecycle state.
- Version history with file metadata and SHA-256 checksum calculation.
- User permissions, secure shares and access logging.
- Multi-step approval workflows and decisions.
- Comments and threaded replies.
- Retention policies, retention events, expiry and archival.
- Search, filtering, upload/download and version restore foundations.

## Notifications
- In-app, email, SMS and webhook channel model.
- Versioned templates with safe variable substitution.
- User channel/event preferences and quiet-period configuration.
- Notification inbox, read tracking and delivery history.
- Event rules, subscriptions and recipient strategies.
- Scheduled notifications and reminders.
- Retry/backoff for failed deliveries.
- Notification batching and digest records.
- Audit trail for notification lifecycle.

## Cross-module events
The event bus defines business events for Sales, Finance, HR, Payroll, Projects, Support, Documents and AI/ML. Existing modules can publish events without coupling their domain logic to a particular delivery channel.

## Validation
Python source compilation is used in the build environment. Full Django migration/test execution requires the project's Django dependencies to be installed in the target environment.
