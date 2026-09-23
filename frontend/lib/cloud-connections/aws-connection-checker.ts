import {
  AssumeRoleCommand,
  GetCallerIdentityCommand,
  STSClient,
} from "@aws-sdk/client-sts";
import type { VerifyAwsConnectionInput } from "@/lib/cloud-connections/contracts";

export class AwsConnectionCheckError extends Error {
  constructor() {
    super("AWS could not verify this connection.");
  }
}

export async function verifyAwsConnection({
  connection,
  externalId,
}: {
  connection: VerifyAwsConnectionInput;
  externalId: string | null;
}) {
  const region = connection.regions[0] ?? "us-east-1";
  const identityClient =
    connection.authMethod === "aws-role"
      ? await createRoleIdentityClient({
          roleArn: connection.roleArn,
          externalId,
          region,
        })
      : new STSClient({
          region,
          credentials: {
            accessKeyId: connection.accessKeyId,
            secretAccessKey: connection.secretAccessKey,
            sessionToken: connection.sessionToken,
          },
        });

  try {
    const identity = await identityClient.send(new GetCallerIdentityCommand({}));

    if (!identity.Account || !identity.Arn) {
      throw new AwsConnectionCheckError();
    }

    return {
      accountId: identity.Account,
      principalArn: identity.Arn,
    };
  } catch {
    throw new AwsConnectionCheckError();
  }
}

async function createRoleIdentityClient({
  roleArn,
  externalId,
  region,
}: {
  roleArn: string;
  externalId: string | null;
  region: string;
}) {
  if (!externalId) {
    throw new AwsConnectionCheckError();
  }

  try {
    const assumedRole = await new STSClient({ region }).send(
      new AssumeRoleCommand({
        RoleArn: roleArn,
        RoleSessionName: "migracle-connection-check",
        ExternalId: externalId,
      }),
    );
    const credentials = assumedRole.Credentials;

    if (
      !credentials?.AccessKeyId ||
      !credentials.SecretAccessKey ||
      !credentials.SessionToken
    ) {
      throw new AwsConnectionCheckError();
    }

    return new STSClient({
      region,
      credentials: {
        accessKeyId: credentials.AccessKeyId,
        secretAccessKey: credentials.SecretAccessKey,
        sessionToken: credentials.SessionToken,
      },
    });
  } catch {
    throw new AwsConnectionCheckError();
  }
}
