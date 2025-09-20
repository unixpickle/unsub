import re
import textwrap
import time
from base64 import b64encode
from io import BytesIO
from typing import Literal

from openai import OpenAI
from PIL import Image, ImageChops
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver

from .api_util import ChatMessage, ChatMessageContentImage, completion


def create_driver(headless: bool = False) -> WebDriver:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1000,1000")
    return WebDriver(options=options)


def unsubscribe_on_website(
    client: OpenAI,
    driver: WebDriver,
    url: str,
    user_email: str,
    max_steps: int = 10,
    max_output_len: int = 2048,
    wait_between_turns: float = 2.0,
    verbose: bool = False,
    max_code_length_to_summarize: int = 32768 * 8,
) -> tuple[Literal["success", "failure", "timeout"], list[ChatMessage]]:
    driver.get(url)

    conversation: list[ChatMessage] = []
    previous_output = None

    previous_image: Image.Image | None = None

    instructions = textwrap.dedent(
        f"""\
        Your goal is to figure out how to run JavaScript on the page to make sure the user is
        unsubscribed from this source of spam and any other sources that this vendor might send.

        * After every message you send, I will give you a new screenshot of the page (if it has changed), and any output from print() calls.
        * You may think out loud in your response, but end the response with a code block to execute on the page.
        * If the page already says that the user has been unsubscribed from ALL emails, then output the code success().
        * If the page does not seem to have anything to do with unsubscribing, or you do not know what to do, then output the code failure().
        * Do not output success() prematurely; make sure you see the latest page first.
        * DO NOT attempt to submit forms (e.g. by pressing buttons) until you have VISUALLY CONFIRMED that you have checked the correct boxes or typed the correct text.
        * To get more information from the page, you can use the provided print() function, which will call toString() on its argument. I will send the outputs of all prints in the next message to allow iteration.
        * The output of print() will be truncated, so the page might have too much code to print directly in one call.
        * I have provided an extra clickText() function which finds elements that contain the given text and clicks them all. It returns true if a click was performed, false otherwise.
        * I have provided an extra scrollDown() function which scrolls down the page further (if it's a long page) so that you can see more content.
        * The user's email address is: {user_email}
        """
    )

    for turn in range(max_steps):
        # Get raw PNG bytes
        png_bytes = driver.get_screenshot_as_png()

        # Make PIL Image
        image = Image.open(BytesIO(png_bytes))

        # Compare with previous screenshot
        if previous_image is not None:
            diff = ImageChops.difference(image, previous_image)
            identical_to_prev = not diff.getbbox()  # None if no difference
        else:
            identical_to_prev = False

        previous_image = image

        b64_data = b64encode(png_bytes).decode("ascii")
        data_url = f"data:image/png;base64,{b64_data}"
        image_content: ChatMessageContentImage | None = {
            "type": "input_image",
            "image_url": data_url,
        }

        msg = ""
        if previous_output:
            if len(previous_output) > max_output_len:
                previous_output = previous_output[:max_output_len]
                previous_output += (
                    f"\n... output truncated at {max_output_len} chars ...\n"
                )
            if verbose:
                print("[PREVIOUS OUTPUT]")
                print(previous_output)
            msg += f"Output from previous code:\n```\n{previous_output}\n```\n\n"
        elif turn:
            if verbose:
                print("[NO PREVIOUS OUTPUT]")
            msg += "There was no print() output from previous code.\n\n"

        page_summary = driver.execute_script(
            """
            const tags = ["button", "input", "a", "form"];
            const counts = tags.map(tag => {
                const count = document.querySelectorAll(tag).length;
                return `${count} <${tag}>`;
            });
            const elementSummary = "There are " + counts.join(", ");
            
            const totalHeight = document.documentElement.scrollHeight;
            const viewportHeight = window.innerHeight;
            const percent = (viewportHeight / totalHeight) * 100;
            const heightSummary = `${percent.toFixed(2)}% of the height of the page is visible.`;

            return heightSummary + '\\n' + elementSummary;
            """
        )

        msg += page_summary + "\n"

        if turn == 0:
            code = driver.execute_script("return document.body.innerHTML")
            if len(code) < max_code_length_to_summarize:
                summary = describe_website_from_code(client, code)
                if verbose:
                    print("[SUMMARY]")
                    print(summary)
                    print("-" * 50)
                msg += "Here is a summary for chunks of the HTML code on the page:\n"
                msg += summary
                msg += "\n\n"

        if identical_to_prev:
            msg += "The screenshot has not changed from the previous message."
            conversation.append(
                {
                    "role": "user",
                    "content": msg.strip(),
                }
            )
        else:
            msg += "Below is a screenshot of a webpage from the email Unsubscribe link."
            conversation.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": msg.strip()},
                        image_content,
                    ],
                }
            )

        response = completion(
            client,
            instructions=instructions,
            input=conversation,
        )
        conversation.append(
            {
                "role": "assistant",
                "content": [{"type": "output_text", "text": response}],
            }
        )

        matches = re.findall(r"```(?:[a-zA-Z]*)\n(.*?)```", response, re.DOTALL)
        if len(matches) != 1:
            previous_output = "ERROR: expected exactly one codeblock in your response"
            continue

        # Rerun this every loop iteration in case the page changed
        # or reloaded.
        driver.execute_script(
            """
            window.logMessages = '';
            window.print = (x) => {
                window.logMessages += x.toString() + '\\n';
            }
            window.unspamStatus = null;
            window.failure = () => {
                window.unspamStatus = 'failure';
            }
            window.success = () => {
                window.unspamStatus = 'success';
            }
            window.scrollDown = () => { window.scrollBy(0, 500); }
            window.clickText = (targetText) => {
                const all = document.querySelectorAll("*");
                let matches = [];

                for (const el of all) {
                    // Get candidate label: textContent for most elements, value for inputs/buttons
                    let label = "";
                    if (el.tagName === "INPUT" || el.tagName === "BUTTON") {
                        if (el.value) label = el.value;
                    }
                    if (!label && el.textContent) {
                        label = el.textContent;
                    }

                    if (label && label.includes(targetText)) {
                        // Prioritize leaf nodes, but also allow input elements (which are leaves anyway)
                        if (el.children.length === 0 || el.tagName === "INPUT" || el.tagName === "BUTTON") {
                            matches.push(el);
                        }
                    }
                }

                // Fallback: if no leaf/input/button matches found, allow any match
                if (matches.length === 0) {
                    for (const el of all) {
                        let label = el.value || el.textContent;
                        if (label && label.includes(targetText)) {
                            matches.push(el);
                        }
                    }
                }

                let found = false;
                for (const el of matches) {
                    const style = window.getComputedStyle(el);
                    if (style.visibility !== "hidden" && style.display !== "none") {
                        el.click();
                        found = true;
                    }
                }

                return found;
            }
            """
        )

        if verbose:
            print("[RESPONSE]")
            print(response)
            print("-" * 50)

        code_to_run = matches[0].strip()
        try:
            driver.execute_script(code_to_run)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            previous_output = f"ERROR while executing script: {e}"
            continue

        previous_output = driver.execute_script("return window.logMessages")
        status = driver.execute_script("return window.unspamStatus")

        if verbose:
            print("[STATUS]:", status)

        if status:
            return status, conversation

        if verbose:
            print("-" * 50)
        time.sleep(wait_between_turns)

        # If a new window/tab was opened, we want to show it to the agent.
        driver.switch_to.window(driver.window_handles[-1])

    return "timeout", conversation


def describe_website_from_code(
    client: OpenAI, code: str, max_code_len: int = 32768, block_overlap: int = 128
):
    code_blocks = [code]
    if len(code) > max_code_len:
        code_blocks = []
        for i in range(0, len(code), max_code_len - block_overlap):
            code_blocks.append(code[i : i + max_code_len])

    instructions = textwrap.dedent(
        """\
        Below is a chunk of code from an email Unsubscribe webpage.
        Describe in a few sentences, from this chunk, what you see that might be relevant to unsubscribing (using JavaScript).
        Be specific about the kinds of HTML tags used, and IDs/values/text if applicable.

        It is possible that you are not looking at a relevant chunk (e.g. this might just be stylesheets).
        In this case, simply give a few word summary.
        """
    )

    responses = []
    for block in code_blocks:
        response = completion(client, instructions=instructions, input=block)
        responses.append(response)
    return "\n\n".join(responses)
