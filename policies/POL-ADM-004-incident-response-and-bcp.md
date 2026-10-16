---
id: POL-ADM-004
title: Incident Response and Business Continuity Policy
category: Operations - Restricted
version: "2.8"
effective_date: "2026-02-01"
owner: Chief Information Security Officer
roles: [admin]
---

# Incident Response and Business Continuity Policy

**Purpose:** This restricted policy defines how the company detects, classifies, responds to, and recovers from security incidents and service disruptions, and how business continuity and disaster recovery are maintained. It is restricted to administrators because it documents response runbooks and recovery capabilities.

## Severity Classification

Incidents are classified on a four-level scale. SEV1: critical outage or confirmed data breach affecting customers - acknowledge within 15 minutes, war room within 1 hour, executive briefing within 2 hours. SEV2: major degradation or suspected breach - acknowledge within 30 minutes, war room within 2 hours. SEV3: limited impact with a workaround - acknowledge within 4 business hours. SEV4: minor issues handled in normal support queues. Severity may be raised immediately by any on-call engineer without approval.

## Incident Response Phases

The response lifecycle follows six phases: detect, triage, contain, eradicate, recover, and learn. The on-call incident commander coordinates response, owns communication cadence, and may page any employee or open emergency vendor cases. Containment actions that affect customer availability require either incident-commander judgement (SEV1) or the CISO's approval (SEV2). All actions taken during response are logged in the incident channel and attached to the incident record.

## Communication

Internal updates are posted in the incident channel at least every 60 minutes for SEV1 and every 4 hours for SEV2. Customer-facing updates go through the status page and support macros approved by communications. Regulatory notification timelines (such as the 72-hour GDPR breach clock) are tracked by the duty DPO and must not be missed; the incident record captures the notification decision and its rationale.

## Post-Incident Reviews

A blameless post-incident review is mandatory for every SEV1 and SEV2. The review document is published within 5 business days, includes a timeline, contributing factors, and action items with owners and due dates. Action items are tracked to closure by the operations team and reported monthly to the executive team.

## Business Continuity and Disaster Recovery

Critical services carry an RTO of 4 hours and an RPO of 1 hour. Multi-region failover is configured for tier-1 systems and exercised through a disaster-recovery drill at least once per year, typically in the third quarter. Backup restore tests run quarterly, and results are reported to the CISO. Alternate work arrangements (remote failover, secondary office) are documented in the continuity plan owned by IT Operations.

## Crisis Management

Major incidents affecting more than 25 percent of customers or lasting beyond 8 hours escalate to the crisis management team, which includes the CEO office, legal, communications, and the CISO. The crisis team owns external messaging, regulator engagement, and customer remediation decisions such as credits.

## Roles and Training

On-call rotations maintain a primary and secondary responder for security and platform. New on-call engineers complete incident-response training within 30 days of joining rotation. Tabletop exercises covering a ransomware scenario and a data-breach scenario are held twice a year.

## Related Documents

Information Security Policy; Access Control and Identity Management Policy; Data Privacy and GDPR Compliance Policy. Reviewed annually by the CISO with IT Operations.
