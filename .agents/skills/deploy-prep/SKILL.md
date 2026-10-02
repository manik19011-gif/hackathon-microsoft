---
name: deploy-prep
description: >-
  Use this skill when the user asks to prepare a project for deployment,
  production, or release.
---

# Deployment Preparation

## Steps

1. **Run all tests** — Ensure the full test suite passes.
2. **Run linting and type checks** — Fix all errors and warnings.
3. **Check environment variables** — Verify all required env vars are documented and have defaults where safe.
4. **Build the project** — Run the production build and verify it succeeds without errors.
5. **Check dependencies** — Remove unused dependencies. Run security audit.
6. **Review configuration** — Verify production configs (database URLs, API endpoints, CORS, logging).
7. **Check documentation** — Verify README has deployment instructions, environment setup, and API docs.
8. **Create deployment checklist** — List the exact steps needed to deploy (commands, services, DNS, etc.).
