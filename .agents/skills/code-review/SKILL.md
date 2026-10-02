---
name: code-review
description: >-
  Use this skill when the user asks to review code, audit quality, or check for issues.
  Performs a structured code review.
---

# Code Review

## Steps

1. **Read all changed files** — Understand the full scope of changes.
2. **Check correctness** — Does the code do what it's supposed to? Are there logic errors?
3. **Check error handling** — Are errors caught, logged, and handled gracefully?
4. **Check security** — Are inputs validated? Are secrets protected? Is authentication enforced?
5. **Check performance** — Are there N+1 queries, memory leaks, or unnecessary re-renders?
6. **Check style** — Is the code consistent with project conventions?
7. **Check tests** — Are critical paths tested? Are edge cases covered?
8. **Check documentation** — Are new APIs, config options, or setup steps documented?
9. **Summarize findings** — Present issues categorized by severity: critical, important, suggestion.
