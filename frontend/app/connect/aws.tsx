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
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useState, type FormEvent } from "react";

export function AwsConnection() {
  const [isOpen, setIsOpen] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsOpen(false);
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

      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Connect AWS</DialogTitle>
          <DialogDescription>Connect an AWS account with a least-privilege IAM role.</DialogDescription>
        </DialogHeader>

        <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
          <FieldGroup className="gap-4">
            <Field>
              <FieldLabel htmlFor="aws-account-id">AWS account ID</FieldLabel>
              <Input id="aws-account-id" name="aws-account-id" placeholder="123456789012" required autoComplete="off" />
            </Field>
            <Field>
              <FieldLabel htmlFor="aws-role-arn">IAM role ARN</FieldLabel>
              <Input
                id="aws-role-arn"
                name="aws-role-arn"
                placeholder="arn:aws:iam::123456789012:role/MigracleReadOnly"
                required
                autoComplete="off"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="aws-external-id">External ID</FieldLabel>
              <Input
                id="aws-external-id"
                name="aws-external-id"
                placeholder="Provided by Migracle AI"
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
      </DialogContent>
    </Dialog>
  );
}
