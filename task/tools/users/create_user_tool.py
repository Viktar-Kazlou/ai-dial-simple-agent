from typing import Any

from task.tools.users.base import BaseUserServiceTool
from task.tools.users.models.user_info import UserCreate


class CreateUserTool(BaseUserServiceTool):

    @property
    def name(self) -> str:
        return "add_user"

    @property
    def description(self) -> str:
        return "Creates a new user in the user service."

    @property
    def input_schema(self) -> dict[str, Any]:
        return UserCreate.model_json_schema()

    def execute(self, arguments: dict[str, Any]) -> str:
        try:
            user_create_model = UserCreate.model_validate(arguments)
            return self._user_client.add_user(user_create_model)
        except Exception as e:
            return f"Error while creating a new user: {str(e)}"
