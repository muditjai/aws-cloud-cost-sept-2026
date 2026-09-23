import { PrismaBetterSqlite3 } from "@prisma/adapter-better-sqlite3";
import { PrismaClient } from "@/generated/prisma/client";

const databaseUrl = process.env.DATABASE_URL ?? "file:./prisma/dev.db";

function createDatabaseClient() {
  const adapter = new PrismaBetterSqlite3({ url: databaseUrl });

  return new PrismaClient({ adapter });
}

const globalDatabase = globalThis as typeof globalThis & {
  cloudCostDatabase?: PrismaClient;
};

export const database = globalDatabase.cloudCostDatabase ?? createDatabaseClient();

if (process.env.NODE_ENV !== "production") {
  globalDatabase.cloudCostDatabase = database;
}
