"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  awsConnectionResponseSchema,
  defaultAwsRegion,
  type AwsConnection,
} from "@/lib/cloud-connections/contracts";
import { Copy } from "lucide-react";
import { useState, useTransition, type FormEvent } from "react";

export function AwsConnection() {
  const [isOpen, setIsOpen] = useState(false);
  const [roleConnection, setRoleConnection] = useState<AwsConnection | null>(null);
  const [hasCopiedExternalId, setHasCopiedExternalId] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleOpenChange(open: boolean) {
    setIsOpen(open);

    if (open && !roleConnection) {
      void prepareRoleConnection();
    }
  }

  async function prepareRoleConnection() {
    try {
      const connection = await createAwsConnection("aws-role", [defaultAwsRegion]);

      setRoleConnection(connection);
      setConnectionMessage(null);
    } catch {
      setConnectionMessage(
        "Could not prepare the IAM role connection. Close the dialog and try again.",
      );
    }
  }

  function handleRoleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!roleConnection) {
      return;
    }

    const formData = new FormData(event.currentTarget);
    const roleArn = formData.get("aws-role-arn");
    const regions = parseRegions(formData.get("aws-role-regions"));

    if (typeof roleArn !== "string") {
      return;
    }

    startTransition(async () => {
      try {
        const connection = await verifyAwsConnection(roleConnection.id, {
          authMethod: "aws-role",
          roleArn,
          regions,
        });

        setRoleConnection(connection);
        setConnectionMessage(`Verified AWS account ${connection.accountId}.`);
      } catch {
        setConnectionMessage(
          "AWS could not verify this role. Check its trust policy, external ID, and read-only permissions.",
        );
      }
    });
  }

  function handleKeySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const formData = new FormData(event.currentTarget);
    const accessKeyId = formData.get("aws-access-key-id");
    const secretAccessKey = formData.get("aws-secret-access-key");
    const regions = parseRegions(formData.get("aws-key-regions"));

    if (typeof accessKeyId !== "string" || typeof secretAccessKey !== "string") {
      return;
    }

    startTransition(async () => {
      try {
        const connection = await createAwsConnection("aws-keys", [defaultAwsRegion]);
        const verifiedConnection = await verifyAwsConnection(connection.id, {
          authMethod: "aws-keys",
          accessKeyId,
          secretAccessKey,
          regions,
        });

        setConnectionMessage(
          `Verified AWS account ${verifiedConnection.accountId}.`,
        );
      } catch {
        setConnectionMessage(
          "AWS could not verify these access keys. Check the keys and read-only permissions.",
        );
      }
    });
  }

  async function handleCopyExternalId() {
    if (!roleConnection?.externalId) {
      return;
    }

    await navigator.clipboard.writeText(roleConnection.externalId);
    setHasCopiedExternalId(true);
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          className="relative z-10 cursor-pointer shadow-sm hover:z-20 hover:-translate-y-px hover:shadow-md"
        >
          <img
            src="https://api.iconify.design/logos:aws.svg"
            alt=""
            className="size-4"
            data-icon="inline-start"
            aria-hidden="true"
          />
          AWS
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Connect AWS</DialogTitle>
          <DialogDescription>
            Connect an AWS account with read-only access.
          </DialogDescription>
        </DialogHeader>

        {connectionMessage ? (
          <p className="text-sm text-muted-foreground" role="status">
            {connectionMessage}
          </p>
        ) : null}

        <Tabs defaultValue="aws-role">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="aws-role">IAM role</TabsTrigger>
            <TabsTrigger value="aws-keys">Access keys</TabsTrigger>
          </TabsList>

          <TabsContent value="aws-role">
            <form className="flex flex-col gap-6" onSubmit={handleRoleSubmit}>
              <FieldGroup className="gap-4">
                <Field>
                  <FieldLabel htmlFor="aws-role-arn">IAM role ARN</FieldLabel>
                  <Input
                    id="aws-role-arn"
                    name="aws-role-arn"
                    placeholder="arn:aws:iam::123456789012:role/MigracleReadOnly"
                    required
                    autoComplete="off"
                  />
                  <FieldDescription>
                    Create a read-only role that trusts Migracle&apos;s AWS
                    account and requires this external ID.
                  </FieldDescription>
                </Field>
                <Field>
                  <FieldLabel htmlFor="aws-external-id">External ID</FieldLabel>
                  <Input
                    id="aws-external-id"
                    name="aws-external-id"
                    value={roleConnection?.externalId ?? "Preparing external ID..."}
                    readOnly
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleCopyExternalId}
                    disabled={!roleConnection?.externalId}
                  >
                    <Copy data-icon="inline-start" aria-hidden="true" />
                    {hasCopiedExternalId ? "Copied" : "Copy external ID"}
                  </Button>
                </Field>
                <Field>
                  <FieldLabel htmlFor="aws-role-regions">
                    Regions (optional)
                  </FieldLabel>
                  <Input
                    id="aws-role-regions"
                    name="aws-role-regions"
                    defaultValue={defaultAwsRegion}
                    autoComplete="off"
                  />
                </Field>
              </FieldGroup>
              <DialogFooter>
                <DialogClose asChild>
                  <Button type="button" variant="outline">
                    Cancel
                  </Button>
                </DialogClose>
                <Button type="submit" disabled={!roleConnection || isPending}>
                  {isPending ? "Verifying..." : "Verify connection"}
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>

          <TabsContent value="aws-keys">
            <form className="flex flex-col gap-6" onSubmit={handleKeySubmit}>
              <FieldGroup className="gap-4">
                <Field>
                  <FieldLabel htmlFor="aws-access-key-id">
                    Access key ID
                  </FieldLabel>
                  <Input
                    id="aws-access-key-id"
                    name="aws-access-key-id"
                    required
                    autoComplete="off"
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="aws-secret-access-key">
                    Secret access key
                  </FieldLabel>
                  <Input
                    id="aws-secret-access-key"
                    name="aws-secret-access-key"
                    type="password"
                    required
                    autoComplete="new-password"
                  />
                  <FieldDescription>
                    Use access keys only when an IAM role is not available.
                  </FieldDescription>
                </Field>
                <Field>
                  <FieldLabel htmlFor="aws-key-regions">
                    Regions (optional)
                  </FieldLabel>
                  <Input
                    id="aws-key-regions"
                    name="aws-key-regions"
                    defaultValue={defaultAwsRegion}
                    autoComplete="off"
                  />
                </Field>
              </FieldGroup>
              <DialogFooter>
                <DialogClose asChild>
                  <Button type="button" variant="outline">
                    Cancel
                  </Button>
                </DialogClose>
                <Button type="submit" disabled={isPending}>
                  {isPending ? "Verifying..." : "Verify connection"}
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

async function createAwsConnection(
  authMethod: "aws-role" | "aws-keys",
  regions: string[],
) {
  const response = await fetch("/api/connections/aws", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ authMethod, regions }),
  });
  const body: unknown = await response.json();
  const connection = awsConnectionResponseSchema.safeParse(body);

  if (!response.ok || !connection.success) {
    throw new Error("Could not create the AWS connection.");
  }

  return connection.data;
}

async function verifyAwsConnection(
  connectionId: string,
  body:
    | {
        authMethod: "aws-role";
        roleArn: string;
        regions: string[];
      }
    | {
        authMethod: "aws-keys";
        accessKeyId: string;
        secretAccessKey: string;
        regions: string[];
      },
) {
  const response = await fetch(`/api/connections/${connectionId}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const responseBody: unknown = await response.json();
  const connection = awsConnectionResponseSchema.safeParse(responseBody);

  if (!response.ok || !connection.success) {
    throw new Error("Could not verify the AWS connection.");
  }

  return connection.data;
}

function parseRegions(value: FormDataEntryValue | null) {
  if (typeof value !== "string") {
    return [defaultAwsRegion];
  }

  const regions = value
    .split(",")
    .map((region) => region.trim())
    .filter(Boolean);

  return regions.length > 0 ? regions : [defaultAwsRegion];
}
