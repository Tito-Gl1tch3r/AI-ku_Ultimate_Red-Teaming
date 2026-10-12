from kernagent.agent import ReverseEngineeringAgent


class DummyToolCallFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class DummyToolCall:
    def __init__(self, name: str, arguments: str = "{}"):
        self.id = "call_1"
        self.type = "function"
        self.function = DummyToolCallFunction(name, arguments)


class DummyMessage:
    def __init__(self, content, tool_calls=None):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls or []


class DummyResponse:
    def __init__(self, message):
        self.choices = [type("Choice", (), {"message": message})()]


class FakeLLM:
    def __init__(self):
        self.invocations = 0

    def chat(self, **kwargs):
        if self.invocations == 0:
            self.invocations += 1
            tool_call = DummyToolCall("echo_tool", '{"text": "hi"}')
            return DummyResponse(DummyMessage(None, [tool_call]))

        self.invocations += 1
        return DummyResponse(DummyMessage("final-answer"))


def test_agent_runs_tool_loop():
    llm = FakeLLM()

    def echo_tool(**kwargs):
        return {"received": kwargs}

    agent = ReverseEngineeringAgent(
        llm=llm,
        tools_spec=[
            {
                "type": "function",
                "function": {
                    "name": "echo_tool",
                    "parameters": {"type": "object", "properties": {"text": {"type": "string"}}},
                },
            }
        ],
        tool_map={"echo_tool": echo_tool},
    )

    answer = agent.run("test question")
    assert answer == "final-answer"
