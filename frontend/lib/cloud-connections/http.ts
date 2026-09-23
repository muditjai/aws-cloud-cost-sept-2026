import { z } from "zod";

export function apiError({
  code,
  message,
  status,
  issues,
}: {
  code: string;
  message: string;
  status: number;
  issues?: z.core.$ZodIssue[];
}) {
  return Response.json(
    {
      error: {
        code,
        message,
        issues: issues?.map((issue) => ({
          path: issue.path.join("."),
          message: issue.message,
        })),
      },
    },
    { status },
  );
}

export async function parseJsonBody<T>(request: Request, schema: z.ZodType<T>) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return {
      response: apiError({
        code: "invalid_json",
        message: "Request body must be valid JSON.",
        status: 400,
      }),
    };
  }

  const parsedBody = schema.safeParse(body);

  if (!parsedBody.success) {
    return {
      response: apiError({
        code: "invalid_request",
        message: "Request body is invalid.",
        status: 400,
        issues: parsedBody.error.issues,
      }),
    };
  }

  return { data: parsedBody.data };
}
