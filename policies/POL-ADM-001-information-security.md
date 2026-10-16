---
id: POL-ADM-001
title: Information Security Policy
category: Security
version: "6.1"
effective_date: "2026-03-15"
owner: Chief Information Security Officer
roles: [employee, hr, admin]
---

# Information Security Policy

**Purpose:** The master security policy for the company. It defines authentication standards, data classification, encryption, patching, network security, and the security responsibilities of every employee.

## Password and Authentication Standards

Passwords must be at least 14 characters, unique per service, and stored only in the approved password manager. Single sign-on with strong multi-factor authentication is mandatory for all company applications; SMS-based MFA is deprecated and must be replaced with app-based or hardware-token methods. Authentication challenges must never be shared, approved remotely for someone else, or bypassed. Failed-login lockout applies to all critical systems after 5 consecutive failures.

## Data Classification

All information is classified into one of four levels: Public, Internal, Confidential, and Restricted. Restricted data (security keys, privileged credentials, investigation records, compensation mechanics) is accessible only on a need-to-know basis with explicit owner approval. Confidential data (customer data, contracts, unreleased plans) must be encrypted at rest and in transit and never stored on personal devices or unapproved cloud services.

## Encryption

Data in transit must use TLS 1.2 or newer on all internal and external services. Data at rest on company systems must use AES-256 encryption. Backups must be encrypted and tested quarterly. Cryptographic keys are managed in the central key vault with a documented rotation schedule at least every 12 months.

## Patching and Vulnerability Management

Server and endpoint operating systems must be patched within 7 days for critical vulnerabilities and within 30 days for high severity. Vulnerability scans run weekly, and penetration tests are conducted at least annually. Findings above the agreed risk threshold require a remediation plan with an owner and a due date tracked to closure.

## Phishing and Social Engineering

Employees must complete security-awareness training within 30 days of joining and annually thereafter. Phishing simulations are run quarterly. Any suspicious email must be reported through the report-phishing button or to the security team within 1 hour of discovery; do not click, reply, or forward to colleagues.

## Network and Endpoint Security

Corporate networks enforce network segmentation, 802.1X for wired access, and encrypted Wi-Fi. Unapproved network devices are prohibited. Endpoint protection agents must remain enabled on all laptops and servers, and compliance is audited monthly. Security exceptions require CISO approval, are time-boxed, and are reviewed quarterly.

## Roles and Responsibilities

Every employee is responsible for following this policy. Asset owners maintain inventory and classification of their systems. The security team operates monitoring, incident response, and awareness training. Non-compliance is handled under the disciplinary framework and may constitute gross misconduct for deliberate breaches.

## Related Documents

Access Control and Identity Management Policy; IT Acceptable Use and Device Policy; Incident Response and Business Continuity Policy; Data Privacy and GDPR Compliance Policy. This policy is reviewed every 12 months by the CISO.
