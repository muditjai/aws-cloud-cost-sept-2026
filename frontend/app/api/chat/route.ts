import { openai } from "@ai-sdk/openai";
import { frontendTools } from "@assistant-ui/ai-sdk";
import {
  type JSONSchema7,
  streamText,
  convertToModelMessages,
  type UIMessage,
  tool,
  stepCountIs,
  zodSchema,
  createUIMessageStreamResponse,
  toUIMessageStream,
} from "ai";
import { z } from "zod";
import {
  CHAT_MODEL,
  getCurrentWeather,
  MAX_AGENT_STEPS,
} from "../../../../backend_agent/chat";

// Allow streaming responses up to 30 seconds
export const maxDuration = 30;

export async function POST(req: Request) {
  const {
    messages,
    system,
    tools,
  }: {
    messages: UIMessage[];
    system?: string;
    tools?: Record<string, { description?: string; parameters: JSONSchema7 }>;
  } = await req.json();

  const result = streamText({
    model: openai(CHAT_MODEL),
    messages: await convertToModelMessages(messages),
    ...(system ? { system } : {}),
    stopWhen: stepCountIs(MAX_AGENT_STEPS),
    tools: {
      ...frontendTools(tools ?? {}),
      get_current_weather: tool({
        description: "Get the current weather",
        inputSchema: zodSchema(
          z.object({
            city: z.string(),
          }),
        ),
        execute: getCurrentWeather,
      }),
    },
  });

  return createUIMessageStreamResponse({
    stream: toUIMessageStream({ stream: result.stream }),
  });
}
