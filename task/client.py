import json
from typing import Any

import requests

from task.models.message import Message
from task.models.role import Role
from task.tools.base import BaseTool


class DialClient:

    def __init__(
            self,
            endpoint: str,
            deployment_name: str,
            api_key: str,
            tools: list[BaseTool] | None = None
    ):
        if not api_key:
            raise ValueError("DIAL_API_KEY is required")

        self._endpoint = f"{endpoint}/openai/deployments/{deployment_name}/chat/completions"
        self._api_key = api_key

        tools = tools or []
        self._tools_dict = {tool.name: tool for tool in tools}
        self._tools = [tool.schema for tool in tools]


    def get_completion(self, messages: list[Message], print_request: bool = True) -> Message:
        headers = {
            "api-key": self._api_key,
            "Content-Type": "application/json"
        }
        request_data = {
            "messages": [msg.to_dict() for msg in messages],
            "tools": self._tools
        }

        if print_request:
            print(f"REQUEST:\n{json.dumps(request_data, indent=2)}")

        response = requests.post(
            url=self._endpoint,
            headers=headers,
            json=request_data,
        )

        if response.status_code == 200:
            response_json = response.json()
            choices = response_json.get("choices", [])
            if not choices:
                raise Exception("Invalid response: no choices")

            choice = choices[0]
            if print_request:
                print(f"RESPONSE CHOICE:\n{json.dumps(choice, indent=2)}")

            message_data = choice.get("message", {})
            content = message_data.get("content") or ""
            tool_calls = message_data.get("tool_calls")

            ai_response = Message(
                role=Role.AI,
                content=content,
                tool_calls=tool_calls
            )

            if choice.get("finish_reason") == "tool_calls":
                messages.append(ai_response)
                tool_messages = self._process_tool_calls(tool_calls or [])
                messages.extend(tool_messages)
                return self.get_completion(messages, print_request)

            return ai_response

        raise Exception(f"HTTP {response.status_code}: {response.text}")


    def _process_tool_calls(self, tool_calls: list[dict[str, Any]]) -> list[Message]:
        """Process tool calls and add results to messages."""
        tool_messages = []
        for tool_call in tool_calls:
            tool_call_id = tool_call.get("id")
            function = tool_call.get("function", {})
            function_name = function.get("name")
            arguments_raw = function.get("arguments", "{}")
            arguments = json.loads(arguments_raw) if isinstance(arguments_raw, str) else (arguments_raw or {})

            tool_execution_result = self._call_tool(function_name, arguments)
            tool_messages.append(
                Message(
                    role=Role.TOOL,
                    name=function_name,
                    tool_call_id=tool_call_id,
                    content=tool_execution_result,
                )
            )
            print(f"FUNCTION '{function_name}'\n{tool_execution_result}\n{'-'*50}")

        return tool_messages

    def _call_tool(self, function_name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools_dict.get(function_name)
        if tool:
            return tool.execute(arguments)
        return f"Unknown function: {function_name}"
