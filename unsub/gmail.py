import base64
import html
import os
import re
from dataclasses import dataclass
from typing import Any, Iterator

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .link import Link

# ----- CONFIG -----
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Your details
CLIENT_ID: str | None = os.getenv("GOOGLE_CLIENT_ID", None)
CLIENT_SECRET: str | None = os.getenv("GOOGLE_CLIENT_SECRET", None)
PROJECT_ID: str | None = os.getenv("GOOGLE_PROJECT_ID", None)
REDIRECT_URI_PORT = 1337


def load_creds(path: str) -> Credentials | None:
    if os.path.exists(path):
        creds = Credentials.from_authorized_user_file(path, SCOPES)
        # Refresh if expired and refresh token available
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds
    return None


def save_creds(path: str, creds: Any) -> None:
    with open(path, "w") as f:
        f.write(creds.to_json())


def build_flow() -> InstalledAppFlow:
    assert (
        CLIENT_ID is not None and CLIENT_SECRET is not None and PROJECT_ID is not None
    )
    # Use PKCE with an "installed" client config; no client secret needed.
    client_config: dict[str, Any] = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "project_id": PROJECT_ID,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"http://localhost:{REDIRECT_URI_PORT}/"],
        }
    }
    return InstalledAppFlow.from_client_config(client_config, SCOPES)


def get_gmail_service(credentials_path: str = "token.json") -> Any:
    creds = load_creds(credentials_path)
    if not creds or not creds.valid:
        flow = build_flow()
        # Spin up a local server on the exact port in your redirect URI (1337)
        creds = flow.run_local_server(
            host="localhost",
            port=REDIRECT_URI_PORT,
            authorization_prompt_message="We need to access your email",
            success_message="You're all set! You can close this tab.",
            open_browser=True,
        )
        save_creds(credentials_path, creds)
    return build("gmail", "v1", credentials=creds)


@dataclass
class Email:
    id: str
    sender: str
    subject: str
    snippet: str
    raw_body: str

    @property
    def body(self) -> str:
        return base64.urlsafe_b64decode(self.raw_body).decode("utf-8", errors="replace")

    def links(self, max_text_len: int = 100) -> list[Link]:
        html_content = self.body
        soup = BeautifulSoup(html_content, "html.parser")

        links: list[Link] = []
        for a in soup.find_all("a", href=True):
            href: str = a["href"].strip()  # type: ignore
            if text := a.get_text(strip=True):
                if len(text) <= max_text_len:
                    links.append(Link(href=href, text=text))

        return links


def _header(headers: list[dict[str, str]], name: str, default: str = "") -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", default)
    return default


def _clean_text(s: str) -> str:
    s = html.unescape(s)

    # Remove zero-width characters (u200b, u200c, u200d, feff, etc.)
    s = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", s)

    return s


def iter_emails(service: Any, page_size: int = 100) -> Iterator[Email]:
    next_page_token = None

    while True:
        resp = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX", "CATEGORY_PROMOTIONS"],
                maxResults=page_size,
                pageToken=next_page_token,
            )
            .execute()
        )

        if not (messages := resp.get("messages", [])):
            break

        for m in messages:
            full = (
                service.users()
                .messages()
                .get(userId="me", id=m["id"], format="full")
                .execute()
            )

            payload = full.get("payload", {})
            headers = payload.get("headers", [])

            body = payload.get("body", {}).get("data", "")
            if not body:
                for part in payload.get("parts", []):
                    if part["mimeType"] == "text/html":
                        body = body or part.get("body", {}).get("data", "")

            yield Email(
                id=full["id"],
                sender=_header(headers, "From", "(unknown)"),
                subject=_header(headers, "Subject", "(no subject)"),
                snippet=_clean_text(full.get("snippet", "").strip()),
                raw_body=body,
            )

        if not (next_page_token := resp.get("nextPageToken")):
            break
