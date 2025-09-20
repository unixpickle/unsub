import time
from typing import Any, Literal, TypedDict

from openai import OpenAI, RateLimitError


class CompletionError(Exception):
    pass


class BadResponseFormat(Exception):
    pass


class ChatMessageContentText(TypedDict):
    type: Literal["input_text", "output_text"]
    text: str


class ChatMessageContentImage(TypedDict):
    type: Literal["input_image"]
    image_url: str


ChatMessageContent = ChatMessageContentText | ChatMessageContentImage


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str | list[ChatMessageContent]


def completion(client: OpenAI, instructions: str, input: Any) -> str:
    while True:
        try:
            response = client.responses.create(
                model="gpt-4o",
                instructions=instructions,
                input=input,
            )
        except RateLimitError:
            time.sleep(30.0)
            continue
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            raise CompletionError("API call failed") from exc
        if err := response.error:
            raise CompletionError(f"error: {err}")
        return response.output_text
