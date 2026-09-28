# AWS Cloud Cost

AWS Cloud Cost is a workspace for finding, implementing, validating, and
proving cloud-cost savings. It presents a guided workflow that starts with a
cloud-account connection and continues through ingestion, audit,
recommendations, implementation, testing, deployment, live validation, and
measured savings.

## What is implemented

- A Next.js 16 / React 19 frontend for the nine-stage savings workflow.
- AWS connection setup using either an IAM role with an external ID or access
  keys. The verifier uses AWS STS to confirm the selected identity.
- SQLite persistence through Prisma for cloud-connection drafts and ingestion
  runs.
- Typed API request and response validation with Zod.
- A streaming chat endpoint built with AI SDK and assistant-ui.
- Playwright coverage for stage navigation, connection UX, and connection API
  behavior.

The current AWS ingestion and workflow stages are UI and persistence
foundations. They do not yet execute a full billing ingestion or apply cloud
changes.

## Repository layout

```text
.
├── backend_agent/       # Chat model configuration and server-side tools
├── frontend/            # Next.js application, API routes, Prisma, and UI tests
├── tests/               # Root Playwright example tests
└── AGENTS.md            # Contributor and agent instructions
```

Key frontend areas:

- `frontend/app/` — workflow pages and App Router API routes.
- `frontend/lib/connect/` — validated connection request and response types.
- `frontend/lib/cloud-connections/` — STS verification and database access.
- `frontend/prisma/` — SQLite schema and migrations.
- `frontend/tests/` — Playwright integration and UI tests.

## Prerequisites

- Node.js 22 or a current Node.js LTS release.
- pnpm 12.5.1 (enabled with Corepack).
- An OpenAI API key only when using the chat endpoint.
- AWS credentials only when verifying a real AWS connection.

## Local development

Run the frontend from its own directory:

```bash
cd frontend
corepack enable
pnpm install
```

Create `frontend/.env.local` for local-only configuration:

```bash
OPENAI_API_KEY=replace_with_your_key
DATABASE_URL=file:./prisma/dev.db
```

Generate the Prisma client and apply the committed local SQLite migration:

```bash
pnpm db:generate
pnpm db:deploy
```

Start the application:

```bash
pnpm dev
```

Open [http://127.0.0.1:3001/connect](http://127.0.0.1:3001/connect). The dev
server writes output to `frontend/log.txt`; review it after starting the app.

## AWS connection security

Prefer the IAM role flow. It generates an external ID and verifies the assumed
identity with AWS STS. When access keys are used, the current verifier uses
them only for the verification request; the SQLite connection record stores
connection metadata, not the submitted access-key values.

Use a least-privilege, read-only IAM role or credentials. Never add cloud
credentials, `.env.local`, or local SQLite database files to Git.

## Testing

With the frontend dependencies installed, run the application tests from the
frontend directory:

```bash
cd frontend
pnpm test:e2e
```

The frontend Playwright configuration starts the development server on port
3001. The root `pnpm test` command runs the root example Playwright suite and
does not exercise the frontend application.

## Contribution notes

Read [`AGENTS.md`](./AGENTS.md) before changing code. In particular:

- Keep code modular and validate external data with Zod.
- Use pnpm rather than npm or yarn.
- For UI changes, add or update Playwright coverage, inspect `log.txt`, and
  validate the result with agent-browser.
- Do not commit unrelated work already present in the working tree.
