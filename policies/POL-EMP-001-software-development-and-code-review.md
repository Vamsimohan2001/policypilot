---
id: POL-EMP-001
title: Software Development and Code Review Policy
category: Engineering
version: "3.4"
effective_date: "2026-02-01"
owner: VP Engineering
roles: [employee]
---

# Software Development and Code Review Policy

**Purpose:** This policy describes the mandatory engineering workflow for all production software, including branching, code review, continuous integration, and release practices. It applies to engineers, QA, and anyone who merges code into a production repository.

## Branching and Protected Branches

The primary branches `main` and `release/*` are protected. Direct pushes to protected branches are disabled at the repository level. All changes must be made on short-lived feature branches and merged through a pull request (PR). Force-pushing to protected branches is prohibited except through a documented incident recovery process approved by a principal engineer.

## Code Review Requirements

Every pull request requires at least two approving reviews before merge, and at least one reviewer must be a senior engineer or above when the change touches authentication, payments, infrastructure, or customer data. Reviewers must respond to a PR request within one business day. Authors should keep PRs small; a PR above 600 changed lines must include a justification in the description. Self-merging an unreviewed change is treated as a policy violation.

## Continuous Integration and Quality Gates

The CI pipeline must pass before merge. Required gates include: unit tests, linting, dependency vulnerability scan, and secret scanning. New or changed code must maintain at least 80 percent line coverage; the pipeline fails below this threshold. Test failures must be fixed, not muted, and flaky tests must be quarantined with a tracking ticket within two business days.

## Secrets and Dependencies

Credentials, API keys, and tokens must never be committed to the repository. Secrets are stored in the central vault and injected at runtime. Any secret accidentally committed must be rotated within 24 hours of discovery and reported as a security incident. Dependencies must be updated at least monthly, and critical vulnerabilities must be patched within 7 days of disclosure.

## Releases and Change Management

Production releases follow the standard release process with a change record in the deployment system. High-risk changes require a rollback plan and a canary deployment before full rollout. A change freeze applies during the last two business days of each quarter; emergency exceptions require director approval. Post-release, any rollback must be documented with a short incident note within 3 business days.

## Legacy and Open Source

Use of new open-source libraries requires a licence check via the dependency review process; copyleft licences (GPL, AGPL) require legal approval. Abandoned internal services must be decommissioned rather than left running without an owner.

## Related Documents

Information Security Policy; IT Acceptable Use and Device Policy; Incident Response and Business Continuity Policy. The engineering standards committee reviews this policy every 12 months.
