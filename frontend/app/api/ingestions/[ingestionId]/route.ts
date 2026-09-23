import { z } from "zod";
import { apiError } from "@/lib/cloud-connections/http";
import { getIngestionRun } from "@/lib/cloud-connections/repository";

const ingestionIdSchema = z.string().cuid();

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ ingestionId: string }> },
) {
  const { ingestionId } = await params;
  const parsedIngestionId = ingestionIdSchema.safeParse(ingestionId);

  if (!parsedIngestionId.success) {
    return apiError({
      code: "invalid_ingestion_id",
      message: "Ingestion ID is invalid.",
      status: 400,
    });
  }

  const ingestionRun = await getIngestionRun(parsedIngestionId.data);

  if (!ingestionRun) {
    return apiError({
      code: "ingestion_not_found",
      message: "Ingestion run was not found.",
      status: 404,
    });
  }

  return Response.json(ingestionRun);
}
