import { z } from "zod";
import { createIngestionRunSchema } from "@/lib/cloud-connections/contracts";
import { apiError, parseJsonBody } from "@/lib/cloud-connections/http";
import {
  createIngestionRun,
  getConnection,
} from "@/lib/cloud-connections/repository";

const connectionIdSchema = z.string().cuid();

export async function POST(
  request: Request,
  { params }: { params: Promise<{ connectionId: string }> },
) {
  const { connectionId } = await params;
  const parsedConnectionId = connectionIdSchema.safeParse(connectionId);

  if (!parsedConnectionId.success) {
    return apiError({
      code: "invalid_connection_id",
      message: "Connection ID is invalid.",
      status: 400,
    });
  }

  const connection = await getConnection(parsedConnectionId.data);

  if (!connection) {
    return apiError({
      code: "connection_not_found",
      message: "Connection was not found.",
      status: 404,
    });
  }

  if (connection.status !== "verified") {
    return apiError({
      code: "connection_not_verified",
      message: "Verify the connection before starting ingestion.",
      status: 409,
    });
  }

  const parsedBody = await parseJsonBody(request, createIngestionRunSchema);

  if ("response" in parsedBody) {
    return parsedBody.response;
  }

  const ingestionRun = await createIngestionRun({
    connectionId: connection.id,
    kind: parsedBody.data.kind,
    regions: parsedBody.data.regions ?? connection.regions,
  });

  return Response.json(ingestionRun, { status: 202 });
}
