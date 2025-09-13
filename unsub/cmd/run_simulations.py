"""
Run unsubscribe agent simulation(s).
"""

import argparse
import json
import os
import time

from openai import OpenAI

from unsub.simulations import Simulations
from unsub.unsub_agent import create_driver, unsubscribe_on_website


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulation", type=str, default=None)
    parser.add_argument(
        "--output-dir", type=str, default=f"simulations/{int(time.time())}"
    )
    parser.add_argument("--user_email", type=str, default="annabelle.lee@gmail.com")
    parser.add_argument("--runs", type=int, default=4)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    openai_client = OpenAI()

    simulations = (
        Simulations
        if args.simulation is None
        else {args.simulation: Simulations[args.simulation]}
    )

    browser = create_driver()

    for name, sim_fn in simulations.items():
        print(f"working on simulation: {name}")
        true_positives = 0
        true_negatives = 0
        false_positives = 0
        false_negatives = 0
        for trial_idx in range(args.runs):
            sim = sim_fn()
            url = sim.start()
            status, conversation = unsubscribe_on_website(
                openai_client, browser, url, args.user_email
            )
            actual_status = sim.finish()
            print(
                f" * trial {trial_idx}: agent_status={status} simulation_status={actual_status} "
                f"with {len(conversation)} messages"
            )
            if status == "success":
                if actual_status == "success":
                    true_positives += 1
                else:
                    false_positives += 1
            else:
                if actual_status == "success":
                    false_negatives += 1
                else:
                    true_negatives += 1
            os.makedirs(os.path.join(args.output_dir, name), exist_ok=True)
            with open(
                os.path.join(args.output_dir, name, f"trial_{trial_idx}.json"), "w"
            ) as f:
                json.dump(
                    dict(
                        agent_status=status,
                        sim_status=actual_status,
                        conversation=conversation,
                    ),
                    f,
                )
        print(
            f" SUMMARY: success_rate={true_positives}/{args.runs} (tn={true_negatives} "
            f"fp={false_positives} fn={false_negatives})"
        )


if __name__ == "__main__":
    main()
