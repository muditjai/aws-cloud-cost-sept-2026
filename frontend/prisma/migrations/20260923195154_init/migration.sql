-- CreateTable
CREATE TABLE "CloudConnection" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "provider" TEXT NOT NULL,
    "authMethod" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "regionsJson" TEXT NOT NULL,
    "externalId" TEXT,
    "roleArn" TEXT,
    "accountId" TEXT,
    "principalArn" TEXT,
    "credentialReference" TEXT,
    "verificationError" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "IngestionRun" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "connectionId" TEXT NOT NULL,
    "kind" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'queued',
    "regionsJson" TEXT NOT NULL,
    "error" TEXT,
    "startedAt" DATETIME,
    "completedAt" DATETIME,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "IngestionRun_connectionId_fkey" FOREIGN KEY ("connectionId") REFERENCES "CloudConnection" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE INDEX "CloudConnection_provider_status_idx" ON "CloudConnection"("provider", "status");

-- CreateIndex
CREATE INDEX "CloudConnection_accountId_idx" ON "CloudConnection"("accountId");

-- CreateIndex
CREATE INDEX "IngestionRun_connectionId_status_idx" ON "IngestionRun"("connectionId", "status");
