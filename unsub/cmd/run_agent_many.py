"""
Run an unsubscribe agent on a real URL.
"""

import argparse
import glob
import json
import os
import traceback

from openai import OpenAI

from unsub.unsub_agent import create_driver, unsubscribe_on_website


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email_dir", type=str, required=True)
    parser.add_argument("--user_email", type=str, required=True)
    parser.add_argument("--log_path", type=str, required=True)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.log_path, exist_ok=True)

    openai_client = OpenAI()
    browser = create_driver(headless=args.headless)

    for path in glob.glob(os.path.join(args.email_dir, "*", "*.json")):
        with open(path, "r") as f:
            url = (json.load(f).get("unsub_link") or {}).get("href")
        if not url:
            continue
        try:
            domain = url.split("://")[1].split("/")[0]
        except KeyboardInterrupt:
            raise
        except:
            continue
        out_path = os.path.join(args.log_path, domain + ".json")
        if os.path.exists(out_path):
            print("skipping url for domain:", domain)
            continue
        print("working on url:", url)

        result = dict(url=url, domain=domain, user_email=args.user_email)
        try:
            status, conversation = unsubscribe_on_website(
                openai_client,
                browser,
                url,
                args.user_email,
                verbose=args.verbose,
            )
            result["status"] = status
            result["conversation"] = conversation
        except KeyboardInterrupt:
            raise
        except:
            result["error"] = traceback.format_exc()

        print(" - done with status:", result.get("status"))

        with open(out_path, "w") as f:
            json.dump(result, f)


if __name__ == "__main__":
    main()
