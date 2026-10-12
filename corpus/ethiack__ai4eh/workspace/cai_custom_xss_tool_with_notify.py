from pathlib import Path
from cai.sdk.agents import Agent, Runner, OpenAIChatCompletionsModel
from cai.tools.reconnaissance.generic_linux_command import generic_linux_command
from cai.sdk.agents import function_tool
from openai import AsyncOpenAI
import asyncio
import subprocess

MODEL = "o4-mini"


@function_tool
async def notify_vulnerability(
    title: str, severity: str, description: str, url: str
) -> str:
    """
    This tool sends a notification with the given vulnerability details
    """
    s = f"{title}\nSeverity: {severity})\nURL: `{url}`\nDescription: {description}\n"

    tmp_file_path = "/tmp/notify_data.txt"
    with Path(tmp_file_path).open("w") as f:
        f.write(s)

    subprocess.run(
        ["notify", "-bulk", "-data", tmp_file_path],
        check=False,
        stderr=subprocess.DEVNULL,
    )
    Path.unlink(tmp_file_path)


agent = Agent(
    name="CTF agent",
    description="Agent focused on finding vulnerabilities in web application.",
    instructions="You are a security expert facing a security assessment. Use the notify tool only if you are sure you found a valid vulnerability.",
    tools=[
        generic_linux_command,
        notify_vulnerability,
    ],
    model=OpenAIChatCompletionsModel(
        model=MODEL,
        openai_client=AsyncOpenAI(),
    ),
)


async def main():
    result = await Runner.run(agent, "Fnd XSS at https://challenges.ethiack.io/xss.php")
    print(result.final_output)


asyncio.run(main())
