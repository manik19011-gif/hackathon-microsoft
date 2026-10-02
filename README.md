# Hackathon SIH — Development Workspace

## Quick Start

```bash
# 1. Clone and enter
git clone <repo-url>
cd "Hackathon SIH"

# 2. Set up environment
cp .env.example .env
# Edit .env with your values

# 3. For Node.js projects
npm install
npm run dev

# 4. For Python projects
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Project Structure

```
.
├── AGENTS.md              # AI agent rules
├── .agents/skills/        # Reusable AI workflows
├── .gitignore             # Git exclusions
├── .env.example           # Environment variable template
├── README.md              # This file
└── src/                   # Your source code
```

## Available AI Skills

The `.agents/skills/` directory contains workflows the AI assistant can use:

| Skill | Purpose |
|-------|---------|
| `plan-feature` | Structure and design a feature before building |
| `implement-feature` | Step-by-step feature implementation |
| `debug-failure` | Systematic debugging methodology |
| `code-review` | Structured code quality review |
| `write-tests` | Test creation with proper coverage |
| `security-review` | Security audit checklist |
| `deploy-prep` | Deployment readiness verification |

## Development Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Git | 2.55.0 | Version control |
| Node.js | 24.19.0 | JavaScript runtime |
| npm | 11.17.0 | Package manager |
| Python | 3.14.7 | Python runtime |
| TypeScript | 7.0.2 | Type-safe JavaScript |
| ESLint | 10.12.0 | JavaScript linting |
| Prettier | 3.9.9 | Code formatting |

## Security Notes

- Never commit `.env` files — they are in `.gitignore`
- Use `.env.example` as a template for required variables
- Never hardcode API keys or secrets in source files
- Pin dependency versions in package.json / requirements.txt
