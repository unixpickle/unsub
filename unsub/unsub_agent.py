import re
from typing import Literal

from openai import OpenAI
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

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
    max_output_len: int = 512,
) -> tuple[Literal["success", "failure", "timeout"], list[ChatMessage]]:
    driver.get(url)

    conversation: list[ChatMessage] = []
    previous_output = None

    for _ in range(max_steps):
        screenshot = driver.get_screenshot_as_base64()
        image_content: ChatMessageContentImage = {
            "type": "input_image",
            "image_url": f"data:image/png;base64,{screenshot}",
        }
        msg = ""
        if previous_output:
            if len(previous_output) > max_output_len:
                previous_output = previous_output[:max_output_len]
                previous_output += (
                    f"\n... output truncated at {max_output_len} chars ...\n"
                )
            msg = f"Output from previous code:\n```\n{previous_output}\n```\n\n"
        msg += (
            "Below is a screenshot of a webpage from an email Unsubscribe link. "
            "Your goal is to figure out how to run JavaScript on the page to make sure the user is "
            "unsubscribed from this source of spam. You may think out loud in your response, but "
            "end the response with a code block to execute on the page. "
            "If the page already says that the user has been unsubscribed from all emails, then "
            "output the code success(). If the page does not seem to have anything to do "
            "with unsubscribing, or you do not know what to do, then output the code `failure()`. "
            "To get more information from the page, you can use a new print() function, which will "
            "convert its argument to string and I will send the outputs of all prints in the next "
            "message so that you can iterate. After every message you send, I will give you a new "
            "screenshot of the page, and any output from print() calls. "
            f"The user's email address is: {user_email}"
        )
        conversation.append(
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": msg},
                    image_content,
                ],
            }
        )
        response = completion(
            client,
            instructions="You are an agent which executes JavaScript to control webpages.",
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
            """
        )

        code_to_run = matches[0].strip()
        try:
            driver.execute_script(code_to_run)
        except Exception as e:
            previous_output = f"ERROR while executing script: {e}"
            continue

        previous_output = driver.execute_script("return window.logMessages")
        status = driver.execute_script("return window.unspamStatus")

        if status:
            return status, conversation

    return "timeout", conversation
