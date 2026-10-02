---
name: debug-failure
description: >-
  Use this skill when the user reports a bug, error, test failure, or unexpected behavior.
  Provides a systematic debugging methodology.
---

# Debug a Failure

## Steps

1. **Reproduce the issue** — Run the failing command or reproduce the error exactly.
2. **Read the error** — Carefully read the full error message, stack trace, and logs.
3. **Identify the location** — Find the exact file, line, and function where the error originates.
4. **Understand the context** — Read surrounding code to understand intended behavior.
5. **Form a hypothesis** — Explain what you think is wrong and why.
6. **Verify the hypothesis** — Add logging, inspect variables, or write a minimal test that demonstrates the bug.
7. **Fix the root cause** — Make the minimal change needed to fix the issue. Don't patch symptoms.
8. **Verify the fix** — Re-run the original failing command to confirm the fix works.
9. **Check for regressions** — Run the full test suite to ensure nothing else broke.
10. **Explain the fix** — Tell the user what was wrong and what you changed.
