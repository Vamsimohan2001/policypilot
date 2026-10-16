---
id: POL-ADM-002
title: Access Control and Identity Management Policy
category: Security - Restricted
version: "3.9"
effective_date: "2026-02-20"
owner: Chief Information Security Officer
roles: [admin]
---

# Access Control and Identity Management Policy

**Purpose:** This restricted policy defines how identities are created, how access is granted and revoked, privileged access management, periodic reviews, and emergency access. It is restricted to administrators because it documents privileged procedures and control design.

## Principles

Access follows the principles of least privilege, need-to-know, and separation of duties. No single individual may hold both the ability to change production data and the ability to modify audit logs without a compensating control. All access is granted to named individuals; shared accounts are prohibited except for a small set of documented service accounts managed by the platform team.

## Identity Lifecycle

Joiner: accounts are provisioned only after HR records the signed contract and the manager submits an access request through the identity portal. Mover: role changes trigger automatic review of group memberships within 24 hours. Leaver: all access must be revoked within 24 hours of the termination event; for involuntary terminations it is revoked immediately at the start of the conversation according to the runbook. HR notifies the identity team through an automated feed; the security team reconciles the feed against all systems weekly.

## Access Requests and Approvals

Employee access is requested via the identity portal with a business justification, approved by the line manager, and for sensitive systems additionally by the system owner. Approvals expire after 30 days if not actioned. Vendors and contractors receive time-boxed external identities that expire automatically at the end of the engagement unless explicitly renewed.

## Privileged Access Management

Administrative and root access is granted just-in-time through the privileged access management vault. Sessions are brokered, recorded, and retained for 12 months. Permanent standing admin rights require CISO approval and are limited to five designated accounts. MFA with a hardware token is mandatory for all privileged access. Privileged groups are reviewed quarterly by the CISO, and any entitlement unused for 90 consecutive days is automatically revoked.

## Recertification

User access to critical systems (production, finance, HR, customer data) is recertified every quarter; lower-risk systems annually. Reviews are executed by system owners in the identity portal with evidence retained for audit. Overdue recertifications are escalated to the CIO after 10 business days.

## Dormant and Orphaned Accounts

Accounts inactive for 90 days are automatically disabled; service accounts without a registered owner for 30 days are disabled and reviewed for deletion. Orphaned accounts in critical systems are reported to the CISO monthly.

## Emergency (Break-Glass) Access

A sealed break-glass account exists for each critical system. Use requires a page to the on-call security engineer, an incident ticket, and post-use review within 24 hours. Break-glass usage triggers an automatic alert to the CISO and is logged with session recording.

## Related Documents

Information Security Policy; Incident Response and Business Continuity Policy. Reviewed annually by Security.
