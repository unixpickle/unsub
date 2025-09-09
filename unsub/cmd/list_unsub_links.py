import argparse
import json
import os
import traceback
from dataclasses import asdict
from typing import Any

from openai import OpenAI

from unsub.gmail import get_gmail_service, iter_emails
from unsub.spam import is_spam
from unsub.unsub_link import find_unsubscribe_link


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-path", type=str, default="token.json")
    parser.add_argument("--output-dir", type=str, default="emails")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    openai_client = OpenAI()

    svc = get_gmail_service(credentials_path=args.token_path)
    for email in iter_emails(svc):
        out_path = os.path.join(args.output_dir, f"{email.id[-2:]}", email.id + ".json")
        if os.path.exists(out_path):
            continue
        output_data: dict[str, Any] = dict(email=asdict(email))
        try:
            spam = is_spam(openai_client, email)
            output_data["spam"] = spam
            link = find_unsubscribe_link(openai_client, email)
            output_data["unsub_link"] = asdict(link) if link else None
            if spam or link:
                print(
                    f"found email with spam={spam} and link={link}: {email.sender} {email.subject}"
                )
            else:
                print(f"clean email from {email.sender}: {email.subject}")
        except Exception as exc:
            traceback.print_exc()
            output_data["error"] = str(exc)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(output_data, f)


if __name__ == "__main__":
    main()
