"""
Run an unsubscribe agent on a real URL.
"""

import argparse
import json
import os
import traceback

from openai import OpenAI

from unsub.unsub_agent import create_driver, unsubscribe_on_website


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, required=True)
    parser.add_argument("--user_email", type=str, required=True)
    parser.add_argument("--log_path", type=str, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    openai_client = OpenAI()
    browser = create_driver()

    result = dict(url=args.url, user_email=args.user_email)
    try:
        status, conversation = unsubscribe_on_website(
            openai_client,
            browser,
            args.url,
            args.user_email,
            verbose=args.verbose,
        )
        result["status"] = status
        result["conversation"] = conversation
    except:
        result["error"] = traceback.format_exc()

    if args.log_path:
        with open(args.log_path, "w") as f:
            json.dump(result, f)


if __name__ == "__main__":
    main()
