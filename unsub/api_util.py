from openai import OpenAI


class CompletionError(Exception):
    pass


class BadResponseFormat(Exception):
    pass


def completion(client: OpenAI, instructions: str, input: str) -> str:
    try:
        response = client.responses.create(
            model="gpt-4o",
            instructions=instructions,
            input=input,
        )
    except Exception as exc:
        raise CompletionError("API call failed") from exc
    if err := response.error:
        raise CompletionError(f"error: {err}")
    return response.output_text
