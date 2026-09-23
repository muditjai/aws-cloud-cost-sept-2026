# Backend Best Practices

## Current architecture

The connection backend uses Next.js Route Handlers as the HTTP boundary, Zod as the runtime contract, Prisma as the database access layer, and SQLite for local development. It has these routes:

```text
POST /api/connections/aws
GET  /api/connections/:connectionId
POST /api/connections/:connectionId/verify
POST /api/connections/:connectionId/ingestions
GET  /api/ingestions/:ingestionId
```

`lib/cloud-connections/contracts.ts` is safe to import from both the browser and server. It defines request and response schemas and derives their TypeScript types. The remaining modules are server-only by convention:

```text
contracts → route handler → connection checker/service → repository → database
```

Do not import a repository, Prisma client, AWS SDK, or secret-store implementation into a Client Component.

## API design

- Use resource names in URLs. `connections` and `ingestions` communicate what an ID identifies; `/api/id/:id` does not.
- Use `POST /verify` for the explicit state transition and `POST /ingestions` to create a new, trackable ingestion job.
- Return one stable JSON error shape: `{ error: { code, message, issues? } }`.
- Validate every request body with a strict Zod schema before side effects. Parse external responses with Zod too.
- Keep route handlers thin: parse input, authorize, call a service or repository, and map expected failures to HTTP responses.
- Add authentication and tenant authorization before exposing these endpoints. Every connection lookup must be constrained to the authenticated organization; IDs alone are not authorization.
- Add idempotency keys to connection setup and ingestion creation before clients can retry automatically.

## Database and ORM

SQLite is intentionally a local-development database. It makes this repo runnable with no infrastructure while Prisma provides migrations and type-safe queries. The schema is in `prisma/schema.prisma`; committed migration SQL is the source of truth for database changes.

For production, use managed PostgreSQL and change only the Prisma provider/adapter plus deployment configuration. PostgreSQL is the primary system of record for:

- organizations, users, and authorization;
- cloud connection metadata, verified AWS identity, and secret references;
- ingestion runs, statuses, checkpoints, and errors;
- resource inventory summaries, findings, approvals, and audit events.

Do not store `secretAccessKey`, session tokens, OAuth refresh tokens, or cloud-service-account keys in a database column. Store them in a managed secret service encrypted with KMS, and persist only an opaque `credentialReference` in PostgreSQL. IAM-role connections should persist the role ARN and external ID, not any customer secret.

For detailed billing data, keep immutable source exports in object storage and query them with an analytics engine. Store ingestion metadata and derived product-facing aggregates in PostgreSQL. Do not make PostgreSQL carry raw, high-volume billing line items indefinitely.

## Technology choices

| Technology | Decision | Why |
| --- | --- | --- |
| Zod | Use now | Already installed; it validates untrusted JSON at runtime and derives types. |
| Prisma | Use now | Clear schema, migrations, generated types, and a straightforward SQLite-to-PostgreSQL path. |
| tRPC | Do not add yet | Route Handlers plus shared Zod contracts already give a clear public API. Add tRPC only if an authenticated TypeScript-only web client begins to duplicate many client wrappers. |
| Hono | Do not add yet | Next Route Handlers are sufficient for this single Next backend. Consider Hono when extracting an edge-compatible or multi-runtime API service. |
| Drizzle | Valid Prisma alternative | Choose it only if SQL-first migrations and lower runtime abstraction become more valuable than Prisma's generated client. Do not run both ORMs. |

## AWS verification and ingestion

The verification service calls AWS STS `GetCallerIdentity`. For role-based connections it first calls `AssumeRole` using the server workload identity, stored external ID, and customer-provided role ARN. For access-key verification, credentials are used for that request only and are not written to SQLite.

The ingestion endpoint currently persists a `queued` run; it deliberately does not do long-running cost or resource collection inside the HTTP request. The next ingestion worker should:

1. claim a queued run atomically;
2. mark it `running` and record a checkpoint;
3. fetch Cost Explorer aggregates and resource inventory with bounded concurrency;
4. write progress and retryable failure details;
5. mark it `completed` or `failed`.

Before supporting key-based ingestion, connect a managed secret-store adapter. Role-based ingestion can use the server workload identity to assume the saved customer role.

## Operational safeguards

- Never log request bodies containing credentials or configuration secrets.
- Use least-privilege IAM policies and a unique external ID per connection.
- Rate-limit setup and verification endpoints and record audit events without secrets.
- Run `pnpm db:generate`, migrations, type checking, build, and API/UI tests in CI.
- Back up production PostgreSQL and object storage; test restore procedures.
