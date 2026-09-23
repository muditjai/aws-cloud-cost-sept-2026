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
import { Copy } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

export function AwsConnection() {
  const [isOpen, setIsOpen] = useState(false);
  const [externalId, setExternalId] = useState("");
  const [hasCopiedExternalId, setHasCopiedExternalId] = useState(false);

  useEffect(() => {
    setExternalId(`migracle-${crypto.randomUUID()}`);
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsOpen(false);
  }

  async function handleCopyExternalId() {
    await navigator.clipboard.writeText(externalId);
    setHasCopiedExternalId(true);
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
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

        <Tabs defaultValue="aws-role">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="aws-role">IAM role</TabsTrigger>
            <TabsTrigger value="aws-keys">Access keys</TabsTrigger>
          </TabsList>

          <TabsContent value="aws-role">
            <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
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
                    value={externalId}
                    readOnly
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleCopyExternalId}
                    disabled={!externalId}
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
                    placeholder="All supported regions"
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
                <Button type="submit">Continue</Button>
              </DialogFooter>
            </form>
          </TabsContent>

          <TabsContent value="aws-keys">
            <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
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
                    placeholder="All supported regions"
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
                <Button type="submit">Continue</Button>
              </DialogFooter>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
