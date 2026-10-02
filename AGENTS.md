# Project Rules — Agent Instructions

These rules govern how the AI coding assistant operates within this workspace.

## Core Principles

1. **Understand before modifying** — Read and comprehend relevant files before making changes. Never blindly edit code.
2. **Plan before implementing** — For complex tasks, outline a plan and confirm it before writing code.
3. **Build complete features** — Deliver working, connected features, not disconnected stubs or mockups.
4. **Modular architecture** — Use small, focused modules with clear responsibilities and interfaces.
5. **Security first** — Never hardcode secrets, API keys, tokens, or passwords. Always use environment variables.
6. **Validate inputs** — Sanitize and validate all user input. Handle errors gracefully with informative messages.
7. **Test important logic** — Write tests for business-critical code. Run existing tests before and after changes.
8. **Run quality checks** — Execute linting, type checking, and formatting before considering work complete.
9. **Fix, don't hide** — Investigate root causes of errors. Never suppress or silence errors without understanding them.
10. **Minimal dependencies** — Keep dependencies lean and well-maintained. Prefer standard library solutions.
11. **Document clearly** — Document setup steps, API endpoints, environment variables, and non-obvious design decisions.
12. **Verify results** — Never claim a command succeeded without checking its output. Re-run if uncertain.
13. **Ask before destroying** — Confirm before destructive operations, broad refactors, or costly external API calls.
14. **Respect existing work** — Never overwrite user code without explicit permission.

## Code Style

- Use consistent formatting (Prettier for JS/TS, Black for Python).
- Follow language-idiomatic naming: camelCase for JS/TS, snake_case for Python.
- Prefer TypeScript over JavaScript for new files.
- Use ES modules (`import/export`) over CommonJS (`require`).
- Write meaningful variable and function names. Avoid single-letter names outside loops.
- Keep functions under 50 lines. Extract helpers for complex logic.

## Architecture Guidelines

- Separate concerns: API routes, business logic, data access, and UI components.
- Use environment variables for all configuration (ports, URLs, keys, feature flags).
- Structure projects with clear directories: `src/`, `tests/`, `docs/`, `scripts/`.
- Prefer composition over inheritance.
- Design APIs RESTfully with proper HTTP methods and status codes.

## Error Handling

- Use try/catch for async operations.
- Return structured error responses from APIs: `{ error: string, details?: any }`.
- Log errors with context (what operation, what input, what failed).
- Never expose stack traces or internal details to end users.

## Security

- Store secrets in `.env` files (never committed to git).
- Validate and sanitize all external input.
- Use parameterized queries for databases (never string concatenation).
- Set CORS policies explicitly.
- Use HTTPS in production.
- Pin dependency versions.

## Testing

- Place tests adjacent to source or in a parallel `tests/` directory.
- Name test files with `.test.ts`, `.test.py`, or `.spec.ts` suffixes.
- Test edge cases: empty input, nulls, boundary values, error paths.
- Mock external services in tests.

## Git Workflow

- Write clear, imperative commit messages: "Add user authentication" not "added stuff".
- Make atomic commits — one logical change per commit.
- Never commit secrets, credentials, or large binary files.
- Use feature branches for significant changes.
