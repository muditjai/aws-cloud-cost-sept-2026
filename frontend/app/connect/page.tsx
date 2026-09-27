import { AwsConnection } from "./aws";
import { AzureConnection } from "./azure";
import { GcpConnection } from "./gcp";
import { Plug } from "lucide-react";

export default function ConnectPage() {
  return (
    <section className="flex h-full min-h-0 flex-col overflow-y-auto px-6 py-10 sm:px-10 lg:px-14">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-8">
        <div className="flex max-w-xl flex-col gap-3">
          <div className="flex size-11 items-center justify-center rounded-xl border border-sky-200 bg-sky-50 text-sky-700 shadow-sm">
            <Plug className="size-5" aria-hidden="true" />
          </div>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-950">Connect a cloud account</h2>
          <p className="text-sm leading-6 text-slate-500">
            Choose the cloud environment where you want to identify and validate cost savings.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <AwsConnection />
          <GcpConnection />
          <AzureConnection />
        </div>
      </div>
    </section>
  );
}
