import {
  createAwsConnectionSchema,
} from "@/lib/cloud-connections/contracts";
import { apiError, parseJsonBody } from "@/lib/cloud-connections/http";
import { createAwsConnection } from "@/lib/cloud-connections/repository";

export async function POST(request: Request) {
  const parsedBody = await parseJsonBody(request, createAwsConnectionSchema);

  if ("response" in parsedBody) {
    return parsedBody.response;
  }

  try {
    const connection = await createAwsConnection(parsedBody.data);

    return Response.json(connection, { status: 201 });
  } catch {
    return apiError({
      code: "connection_setup_failed",
      message: "Could not create the AWS connection.",
      status: 500,
    });
  }
}
