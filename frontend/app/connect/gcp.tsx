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

export function GcpConnection() {
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
            src="https://api.iconify.design/logos:google-cloud.svg"
            alt=""
            className="size-4"
            data-icon="inline-start"
            aria-hidden="true"
          />
          GCP
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Connect GCP</DialogTitle>
          <DialogDescription>Connect a Google Cloud project with a service account.</DialogDescription>
        </DialogHeader>

        <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
          <FieldGroup className="gap-4">
            <Field>
              <FieldLabel htmlFor="gcp-project-id">Project ID</FieldLabel>
              <Input id="gcp-project-id" name="gcp-project-id" placeholder="your-gcp-project" required autoComplete="off" />
            </Field>
            <Field>
              <FieldLabel htmlFor="gcp-service-account-email">Service account email</FieldLabel>
              <Input
                id="gcp-service-account-email"
                name="gcp-service-account-email"
                placeholder="migracle-reader@your-gcp-project.iam.gserviceaccount.com"
                required
                autoComplete="off"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="gcp-service-account-key">Service account key</FieldLabel>
              <Input
                id="gcp-service-account-key"
                name="gcp-service-account-key"
                type="password"
                placeholder="Paste the service account key"
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
