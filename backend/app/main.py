import json
import time
import uuid

from typing import AsyncGenerator, List, Literal, Optional
from http import HTTPStatus

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, UserPromptPart, ModelResponse, TextPart


app = FastAPI()


agent = Agent("openai:gpt-4o")


#
# These two models represent what https://api.openai.com/v1/chat/completions expects. This
# is what Assistant UI will send to us.
#


class ChatCompletionMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatCompletionMessage]
    stream: Optional[bool] = False


#
# This endpoint behaves just like https://api.openai.com/v1/chat/completions as documented
# on https://platform.openai.com/docs/api-reference/chat/create with the notable exception
# that it only supports streaming. Streaming mode is the default in Assistant UI.
#
# First the incoming chat messages are converted to a model that Pydantic AI expects. Then
# we call the agent in streaming mode, which will return deltas for the response. These are
# just text fragments.
#
# The deltas returned by Pydantic AI are then converted to the OpenAI streaming response
# format and sent back to Assistant UI which will render the responses progressively.
#
# We do not keep track of past messages - this is done by Asisstant UI. It will send the
# whole conversation in every request to the chat completion endpoint.
#


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # Only handle streaming
    if not request.stream:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Bad Request: Only streaming is supported",
        )

    # Convert OpenAI message history to Pydantic AI models
    message_history = []
    for m in request.messages:
        match m.role:
            case "user":
                message_history.append(ModelRequest(parts=[UserPromptPart(content=m.content)]))
            case "assistant":
                message_history.append(ModelResponse(parts=[TextPart(content=m.content)]))

    async def agent_stream() -> AsyncGenerator[str, None]:
        async with agent.run_stream(message_history=message_history) as result:
            completion_id = str(uuid.uuid4())
            completion_created = int(time.time())

            #
            # Send the initial "role" chunk
            #

            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": completion_created,
                "model": request.model,
                "choices": [
                    {
                        "delta": {
                            "content": "",
                            "role": "assistant",
                        },
                        "index": 0,
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"

            #
            # Send content chunks
            #

            async for message in result.stream_text(delta=True):
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": completion_created,
                    "model": request.model,
                    "choices": [
                        {
                            "delta": {"content": message},
                            "index": 0,
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk)}\n\n"

            #
            # Send the final "stop" chunk
            #

            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": completion_created,
                "model": request.model,
                "choices": [
                    {
                        "delta": {},
                        "index": 0,
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(agent_stream(), media_type="text/event-stream")
