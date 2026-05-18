---
title: VPN troubleshooting playbook (example)
category: IT runbook
last_reviewed: 2026-04-01
audience: tier-1 IT
---

# VPN troubleshooting playbook

This is an **example** document. Replace it (and add 10–20 more) with real
proprietary knowledge for your team's project.

## Symptoms

- User reports VPN client connects but cannot reach internal services.
- VPN client hangs on "authenticating..." for more than 60 seconds.
- Frequent reconnections during the workday.

## Common causes

1. Stale Kerberos ticket — log out and back in, then retry.
2. Split tunnelling misconfigured — confirm `pushed routes` in the client.
3. MFA push delivery delay — re-send the push from the auth portal.

## Resolution steps (in order)

1. Confirm the user's account is not locked in the SSO console.
2. Have the user disconnect and re-launch the VPN client.
3. If still failing, reset the user's VPN device token in the IT console.
4. Escalate to networking-on-call if the certificate was rotated this week.

## Required customer information

- Username (SSO id, not display name)
- Approximate time of first failure
- Whether the issue started after an OS update or office network change
