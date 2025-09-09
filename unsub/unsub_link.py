from openai import OpenAI

from .api_util import BadResponseFormat, completion
from .link import Link


def find_unsubscribe_link(
    client: OpenAI,
    links: list[Link],
    max_url_len: int = 50,
    max_links_per_call: int = 20,
) -> Link | None:
    if len(links) > max_links_per_call:
        for i in range(0, len(links), max_links_per_call):
            if link := find_unsubscribe_link(
                client, links[i : i + max_links_per_call], max_url_len=max_url_len
            ):
                return link

    instructions = (
        "Out of these links, choose the one that looks like an unsubscribe link. "
        'End your response with "Answer: N" where N is a link number, or -1 if '
        "none of the links look like an unsubscribe link. If more than one looks "
        "like an unsubscribe link, simply pick one of them arbitrarily."
    )
    link_text = ""
    for i, link in enumerate(links):
        url_text = link.href[:max_url_len]
        if len(url_text) > max_url_len:
            url_text = url_text[:max_url_len] + "..."
        link_text += f"{i+1}. {repr(link.text)} {repr(url_text)}"

    response = completion(client, instructions=instructions, input=link_text)

    last_line = response.strip().splitlines()[-1]
    if not last_line.startswith("Answer:"):
        raise BadResponseFormat("no answer at end of response")

    try:
        answer_idx = int(last_line[len("Answer:") :].strip())
        if answer_idx < 1:
            return None
        elif answer_idx > len(links):
            raise BadResponseFormat(
                f"answer is out of range: {answer_idx} (only have {len(links)} links)"
            )
        else:
            return links[answer_idx - 1]
    except ValueError as exc:
        raise BadResponseFormat("invalid response integer") from exc
