import { z } from "zod";
import {
  verifyAwsConnectionSchema,
} from "@/lib/cloud-connections/contracts";
import {
  AwsConnectionCheckError,
  verifyAwsConnection,
} from "@/lib/cloud-connections/aws-connection-checker";
import { apiError, parseJsonBody } from "@/lib/cloud-connections/http";
import {
  getConnection,
  markConnectionFailed,
  markConnectionVerified,
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

  const parsedBody = await parseJsonBody(request, verifyAwsConnectionSchema);

  if ("response" in parsedBody) {
    return parsedBody.response;
  }

  if (connection.authMethod !== parsedBody.data.authMethod) {
    return apiError({
      code: "auth_method_mismatch",
      message: "Verification method does not match the connection setup.",
      status: 409,
    });
  }

  try {
    const identity = await verifyAwsConnection({
      connection: parsedBody.data,
      externalId: connection.externalId,
    });
    const verifiedConnection = await markConnectionVerified({
      connectionId: connection.id,
      roleArn:
        parsedBody.data.authMethod === "aws-role"
          ? parsedBody.data.roleArn
          : null,
      accountId: identity.accountId,
      principalArn: identity.principalArn,
      regions: parsedBody.data.regions,
    });

    return Response.json(verifiedConnection);
  } catch (error) {
    if (error instanceof AwsConnectionCheckError) {
      await markConnectionFailed({
        connectionId: connection.id,
        verificationError:
          "AWS rejected the credentials or role trust configuration.",
      });

      return apiError({
        code: "aws_verification_failed",
        message:
          "AWS rejected the credentials or role trust configuration. Check the role, external ID, and permissions.",
        status: 422,
      });
    }

    return apiError({
      code: "connection_verification_failed",
      message: "Could not verify the AWS connection.",
      status: 500,
    });
  }
}
