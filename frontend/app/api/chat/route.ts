import { createOpenAI } from "@ai-sdk/openai";
import { frontendTools } from "@assistant-ui/react-ai-sdk";
import { streamText } from "ai";

export const runtime = "edge";
export const maxDuration = 30;

const localOpenAI = createOpenAI({
  apiKey: "does-not-matter",
  baseURL: "http://127.0.0.1:8000/v1",
});

export async function POST(req: Request) {
  const { messages, system, tools } = await req.json();

  const result = streamText({
    model: localOpenAI("does-not-matter"), // The model doesn't really matter since it is configured in the backend
    messages,
    // forward system prompt and tools from the frontend
    toolCallStreaming: true,
    system,
    tools: {
      ...frontendTools(tools),
    },
    onError: console.log,
  });

  return result.toDataStreamResponse();
}
