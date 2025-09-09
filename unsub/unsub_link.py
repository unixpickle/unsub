from bs4 import BeautifulSoup
from openai import OpenAI

from .api_util import BadResponseFormat, completion
from .gmail import Email
from .link import Link


def find_unsubscribe_link(
    client: OpenAI,
    email: Email,
) -> Link | None:
    if not email.raw_body:
        return None
    if links := email.links():
        if link := _find_unsubscribe_link_from_list(client, links):
            return link
    return _find_unsubscribe_link_from_code(client, email.body)


def _find_unsubscribe_link_from_code(
    client: OpenAI, code: str, max_code_len: int = 8192, block_overlap: int = 128
):
    soup = BeautifulSoup(code, "html.parser")

    links: list[Link] = []
    for i, a in enumerate(soup.find_all("a", href=True)):
        a["data-index"] = str(i)  # type: ignore
        links.append(Link(href=a["href"], text=a.get_text(strip=True)))  # type: ignore
    for img in soup.find_all("img"):
        img["src"] = ""  # type: ignore
    code = str(soup)

    code_blocks = [code]
    if len(code) > max_code_len:
        code_blocks = []
        for i in range(0, len(code), max_code_len - block_overlap):
            code_blocks.append(code[i : i + max_code_len])
    code_blocks = sorted(
        code_blocks, key=lambda x: "unsubscribe" in x.lower(), reverse=True
    )

    instructions = (
        "Each link on this page has a data-index attribute with an integer value. "
        "Find the link that looks like an Unsubscribe link (this is an email's source code), and "
        'end your response with a line like "Answer: N" where N is the index. '
        "There may be no unsubscribe link, and the code may be truncated in such a way that the link "
        'is missing or hard to determine. In that case, output "Answer: -1". '
        "You may think out loud before giving your answer, but give the answer on a new line in the above format."
    )

    for block in code_blocks:
        response = completion(client, instructions=instructions, input=block)
        last_line = response.strip().splitlines()[-1]
        if not last_line.startswith("Answer:"):
            raise BadResponseFormat("no answer at end of response")
        answer_idx = int(last_line[len("Answer:") :].strip())
        if answer_idx < 0:
            continue
        elif answer_idx > len(links):
            raise BadResponseFormat(
                f"answer is out of range: {answer_idx} (only have {len(links)} links)"
            )
        else:
            return links[answer_idx]


def _find_unsubscribe_link_from_list(
    client: OpenAI,
    links: list[Link],
    max_url_len: int = 50,
    max_links_per_call: int = 20,
) -> Link | None:
    if len(links) > max_links_per_call:
        for i in range(0, len(links), max_links_per_call):
            if link := _find_unsubscribe_link_from_list(
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
