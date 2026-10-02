---
name: security-review
description: >-
  Use this skill when the user asks to check security, audit vulnerabilities, or
  harden an application.
---

# Security Review

## Steps

1. **Check secrets management** — Ensure no API keys, passwords, or tokens are hardcoded. Verify .env is in .gitignore.
2. **Check input validation** — Verify all user inputs are validated and sanitized.
3. **Check authentication** — Verify auth is properly implemented and enforced on protected routes.
4. **Check authorization** — Verify users can only access their own resources.
5. **Check SQL injection** — Ensure parameterized queries are used everywhere.
6. **Check XSS** — Ensure user content is escaped before rendering in HTML.
7. **Check CORS** — Verify CORS policies are restrictive and explicit.
8. **Check dependencies** — Run `npm audit` or `pip audit` to find known vulnerabilities.
9. **Check error exposure** — Ensure stack traces and internal errors are not sent to clients.
10. **Report findings** — List vulnerabilities with severity and remediation steps.
