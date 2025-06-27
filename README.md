# Assistant-UI & Pydantic AI

_Stefan Arentz, June 2025_

This is a minimal demo application that shows how to expose a [Pydantic AI](https://ai.pydantic.dev) Agent with an [Assistant UI](https://github.com/assistant-ui/assistant-ui) frontend.

This is a great combination to make conversational bots available using a good looking React based frontend. The demo uses the default starter template but Assistant UI is highly customizable.

## Running the demo

Clone the project and then start the backend as follows:

```
$ cd backend
$ export OPENAI_API_KEY=...
$ uv run fastapi dev
```

If you use a different AI provider, set the appropriate environment variable and change the first argument to `Agent()` in `backend/app/main.py`.

In another window start the frontend:

```
$ cd frontend
$ npm run dev
```

You can now visit the UI on http://127.0.0.1:3000

## Implementation details

The only notable change in the frontend is to create a custom OpenAI provider that instead points to our own OpenAI-compatible backend.

```diff
diff --git a/frontend/app/api/chat/route.ts b/frontend/app/api/chat/route.ts
index 8f43f91..01e495c 100644
--- a/frontend/app/api/chat/route.ts
+++ b/frontend/app/api/chat/route.ts
@@ -1,15 +1,20 @@
-import { openai } from "@ai-sdk/openai";
+import { createOpenAI } from "@ai-sdk/openai";
 import { frontendTools } from "@assistant-ui/react-ai-sdk";
 import { streamText } from "ai";
 
 export const runtime = "edge";
 export const maxDuration = 30;
 
+const localOpenAI = createOpenAI({
+  apiKey: "does-not-matter",
+  baseURL: "http://127.0.0.1:8000/v1",
+});
+
 export async function POST(req: Request) {
   const { messages, system, tools } = await req.json();
 
   const result = streamText({
-    model: openai("gpt-4o"),
+    model: localOpenAI("does-not-matter"), // The model doesn't really matter since it is configured in the backend
     messages,
     // forward system prompt and tools from the frontend
     toolCallStreaming: true,
```

The backend code is in backend/app/main.py in the `chat_completions` function. The code is well documented to explain how it consumes messages and streams the Agent / LLM output.

