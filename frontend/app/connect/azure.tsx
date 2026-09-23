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

export function AzureConnection() {
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
            src="https://api.iconify.design/logos:microsoft-azure.svg"
            alt=""
            className="size-4"
            data-icon="inline-start"
            aria-hidden="true"
          />
          Azure
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Connect Azure</DialogTitle>
          <DialogDescription>Connect an Azure subscription with an app registration.</DialogDescription>
        </DialogHeader>

        <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
          <FieldGroup className="gap-4">
            <Field>
              <FieldLabel htmlFor="azure-tenant-id">Tenant ID</FieldLabel>
              <Input
                id="azure-tenant-id"
                name="azure-tenant-id"
                placeholder="00000000-0000-0000-0000-000000000000"
                required
                autoComplete="off"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="azure-subscription-id">Subscription ID</FieldLabel>
              <Input
                id="azure-subscription-id"
                name="azure-subscription-id"
                placeholder="00000000-0000-0000-0000-000000000000"
                required
                autoComplete="off"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="azure-client-id">Application (client) ID</FieldLabel>
              <Input
                id="azure-client-id"
                name="azure-client-id"
                placeholder="00000000-0000-0000-0000-000000000000"
                required
                autoComplete="off"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="azure-client-secret">Client secret</FieldLabel>
              <Input
                id="azure-client-secret"
                name="azure-client-secret"
                type="password"
                placeholder="Enter client secret"
                required
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
