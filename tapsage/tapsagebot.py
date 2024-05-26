import json
import uuid

import requests
from tapsage.taptypes import (
    Message,
    MessageContent,
    MessageRequest,
    MessageStream,
    Session,
    SessionRequest,
    SessionUser,
    Task,
    TaskResult,
)


class TapSageBot:
    API_V1_SESSION = "https://api.tapsage.com/api/v1/chat/session"

    def __init__(self, api_key, bot_id):
        self.api_key = api_key
        self.endpoints = {
            "sessions": f"{self.API_V1_SESSION}s?userId={{user_id}}",
            "session": f"{self.API_V1_SESSION}",
            "get_session": f"{self.API_V1_SESSION}/{{session_id}}",
            "message": f"{self.API_V1_SESSION}/{{session_id}}/message",
            "async_task": f"{self.API_V1_SESSION}/{{session_id}}/message/async",
            "get_async_task": f"{self.API_V1_SESSION}/{{session_id}}/message/async/{{task_id}}",
            "stream": f"{self.API_V1_SESSION}/{{session_id}}/message/stream",
        }
        self.headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
        }
        self.bot_id = bot_id

    def create_session(self, user_id: str = None) -> Session:
        if user_id is None:
            user_id = str(uuid.uuid4())

        session_request = SessionRequest(
            botId=self.bot_id, user=SessionUser(id=user_id, name="Mahdi")
        )

        response = requests.post(
            url=self.endpoints.get("session"),
            headers=self.headers,
            json=session_request.model_dump(),
        )
        response.raise_for_status()
        return Session(**response.json())

    def list_sessions(self, user_id: str) -> list[Session]:
        url = self.endpoints.get("sessions").format(user_id=user_id)
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return [Session(**data) for data in response.json()]

    def retrieve_session(self, session_id: str) -> Session:
        url = self.endpoints.get("get_session").format(session_id=session_id)
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return Session(**response.json())

    def delete_session(self, session: Session) -> None:
        url = self.endpoints.get("get_session").format(session_id=session.id)
        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()

    def send_message(self, session: Session, prompt: str) -> Message:
        url = self.endpoints.get("message").format(session_id=session.id)
        data = MessageRequest(
            message=MessageContent(
                type="USER",
                content=prompt,
            )
        )
        response = requests.post(url, headers=self.headers, json=data.model_dump())
        response.raise_for_status()
        return Message(**response.json())

    def send_message_async(self, session: Session, prompt: str) -> Task:
        url = self.endpoints.get("async_task").format(session_id=session.id)
        data = MessageRequest(
            message=MessageContent(
                type="USER",
                content=prompt,
            )
        )
        response = requests.post(url, headers=self.headers, json=data.model_dump())
        response.raise_for_status()
        return Task(**response.json())

    def retrieve_async_task(self, session: Session, task: Task) -> TaskResult:
        url = self.endpoints.get("get_async_task").format(
            session_id=session.id, task_id=task.taskId
        )
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return TaskResult(**response.json())

    def stream_messages(
        self, session: Session, prompt: str, split_criteria: dict = None
    ):
        url = self.endpoints.get("stream").format(session_id=session.id)
        data = MessageRequest(
            message=MessageContent(
                type="USER",
                content=prompt,
            )
        )
        response = requests.post(
            url, headers=self.headers, json=data.model_dump(), stream=True
        )
        response.raise_for_status()

        if split_criteria.get("words"):
            split_criteria["splitter"] = " "
        elif split_criteria.get("sentence"):
            split_criteria["splitter"] = ".?!:"
        elif split_criteria.get("line"):
            split_criteria["splitter"] = "\n"

        buffer = ""
        for line in response.iter_lines():
            if line:
                data = line.decode("utf-8").replace("data:", "")
                msg = MessageStream(**json.loads(data))
                if not split_criteria:
                    yield MessageStream(**json.loads(data))
                    continue

                buffer += msg.message.content
                if split_criteria.get("min-length"):
                    if len(buffer) >= split_criteria.get("min-length"):
                        yield MessageStream(
                            message=MessageContent(
                                type="AI", content=buffer, attachments=None
                            )
                        )
                        buffer = ""

                if split_criteria.get("splitter"):
                    for splitter in split_criteria.get("splitter"):
                        if splitter in buffer:
                            yield MessageStream(
                                message=MessageContent(
                                    type="AI", content=buffer, attachments=None
                                )
                            )
                            buffer = ""
        
        yield MessageStream(
            message=MessageContent(
                type="AI", content=buffer, attachments=None
            )
        )
