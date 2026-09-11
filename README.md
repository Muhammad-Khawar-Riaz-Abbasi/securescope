# SecureScope

SecureScope is a privacy-first account security auditor for people who want to understand password risk without handing credentials to a third party.

## What it does

- Analyzes a password locally in the browser and on the API request path without persisting it.
- Produces an explainable risk score based on length, character variety, repetition, sequences, contextual words, and common-password signals.
- Uses Have I Been Pwned's k-anonymity password endpoint so the full password never leaves the client/API boundary.
- Provides an actionable account-security checklist covering MFA, active sessions, recovery methods, and suspicious applications.

SecureScope does **not** attempt logins, guess passwords, scrape social networks, access friend lists, or store credentials.

## Architecture

```text
React + TypeScript + Vite
          |
          v
FastAPI + Pydantic  ----->  HIBP Pwned Passwords (k-anonymity)
          |
          v
   No database / no password persistence
```

## Run locally

### API

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### Web

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173`.

## Quality checks

```bash
cd api && pytest
cd ../web && npm run build
```

## Privacy model

The API accepts the password only for the duration of the request. It is excluded from request logs, response payloads, analytics, and error details. The breach lookup sends only the first five characters of a SHA-1 hash to HIBP and filters the matching suffix locally.

This project is an educational defensive tool, not a replacement for a password manager or a provider's official security controls.
