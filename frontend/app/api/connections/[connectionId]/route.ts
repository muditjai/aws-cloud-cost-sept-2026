import { z } from "zod";
import { apiError } from "@/lib/cloud-connections/http";
import { getConnection } from "@/lib/cloud-connections/repository";

const connectionIdSchema = z.string().cuid();

export async function GET(
  _request: Request,
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

  return Response.json(connection);
}
