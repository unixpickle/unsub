from openai import OpenAI

from .api_util import BadResponseFormat, completion
from .gmail import Email


def is_spam(
    client: OpenAI,
    email: Email,
) -> bool:
    instructions = (
        "Based on information about an email, predict if it's promotional (spam) or not. "
        "Emails about orders that were successfully delivered, or personal emails, are not spam. "
        "On the other hand, emails about sales, promotions, or newsletters or random news "
        "updates from brands are spam. "
        "You may think about the message, but end your response with a new line that says either "
        "SPAM or NOT SPAM. If you are unsure, err on the side of caution and say NOT SPAM."
    )
    email_desc = (
        f"Sender: {email.sender}\nSubject: {email.subject}\nSnippet: {email.snippet}"
    )
    response = completion(client, instructions=instructions, input=email_desc)

    last_line = response.strip().splitlines()[-1]
    match last_line:
        case "SPAM":
            return True
        case "NOT SPAM":
            return False
        case _:
            raise BadResponseFormat(f"unexpected response: {last_line}")
