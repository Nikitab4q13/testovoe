"""Модуль для моделирования чатов службы поддержки."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ChatStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class User:
    user_id: int
    full_name: str
    city: str
    birth_date: date
    position: str
    experience_years: int

    def __post_init__(self) -> None:
        _validate_profile(self.full_name, self.city, self.birth_date, self.position, self.experience_years)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "full_name": self.full_name,
            "city": self.city,
            "birth_date": self.birth_date.isoformat(),
            "position": self.position,
            "experience_years": self.experience_years,
        }


@dataclass
class Operator:
    operator_id: int
    full_name: str
    city: str
    birth_date: date
    position: str
    experience_years: int
    is_busy: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _validate_profile(self.full_name, self.city, self.birth_date, self.position, self.experience_years)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "full_name": self.full_name,
            "city": self.city,
            "birth_date": self.birth_date.isoformat(),
            "position": self.position,
            "experience_years": self.experience_years,
            "is_busy": self.is_busy,
        }


@dataclass(frozen=True)
class Message:
    sender_type: str
    sender_id: int
    sender_name: str
    text: str
    sent_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender_type": self.sender_type,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "text": self.text,
            "sent_at": self.sent_at,
        }


@dataclass
class Chat:
    chat_id: int
    user: User
    operator: Operator
    created_at: str
    status: ChatStatus = ChatStatus.OPEN
    csat: int | None = None
    messages: list[Message] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chat_id": self.chat_id,
            "user": {
                "user_id": self.user.user_id,
                "full_name": self.user.full_name,
            },
            "operator": {
                "operator_id": self.operator.operator_id,
                "full_name": self.operator.full_name,
            },
            "created_at": self.created_at,
            "status": self.status.value,
            "csat": self.csat,
            "messages": [message.to_dict() for message in self.messages],
        }


class SupportPlatform:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.users: dict[int, User] = {}
        self.operators: dict[int, Operator] = {}
        self.chats: dict[int, Chat] = {}
        self._rng = rng if rng is not None else random.Random()

    def add_user(self, user: User) -> None:
        if user.user_id in self.users:
            raise ValueError(f"User {user.user_id} is already registered")
        self.users[user.user_id] = user

    def add_operator(self, operator: Operator) -> None:
        if operator.operator_id in self.operators:
            raise ValueError(f"Operator {operator.operator_id} is already registered")
        self.operators[operator.operator_id] = operator

    def get_free_operators(self) -> list[Operator]:
        return [operator for operator in self.operators.values() if not operator.is_busy]

    def create_chat(self, user_id: int, initial_message: str) -> Chat:
        user = self._get_user(user_id)
        text = _validate_message(initial_message)
        free_operators = self.get_free_operators()
        if not free_operators:
            raise RuntimeError("Cannot create a chat: no free operators are available")

        operator = self._rng.choice(free_operators)
        chat = Chat(
            chat_id=len(self.chats) + 1,
            user=user,
            operator=operator,
            created_at=_current_timestamp(),
        )
        chat.messages.append(_make_message("user", user.user_id, user.full_name, text))
        self.chats[chat.chat_id] = chat
        operator.is_busy = True
        return chat

    def send_user_message(self, chat_id: int, user_id: int, text: str) -> Message:
        chat = self._get_chat(chat_id)
        self._ensure_open(chat)
        if chat.user.user_id != user_id:
            raise ValueError(f"User {user_id} does not own chat {chat_id}")
        return self._append_message(chat, "user", user_id, chat.user.full_name, text)

    def reply_to_chat(self, chat_id: int, operator_id: int, text: str) -> Message:
        chat = self._get_chat(chat_id)
        self._ensure_open(chat)
        if chat.operator.operator_id != operator_id:
            raise ValueError(f"Operator {operator_id} is not assigned to chat {chat_id}")
        return self._append_message(chat, "operator", operator_id, chat.operator.full_name, text)

    def close_chat(self, chat_id: int, operator_id: int) -> None:
        chat = self._get_chat(chat_id)
        self._ensure_open(chat)
        if chat.operator.operator_id != operator_id:
            raise ValueError(f"Operator {operator_id} is not assigned to chat {chat_id}")
        chat.status = ChatStatus.CLOSED
        chat.operator.is_busy = False

    def rate_chat(self, chat_id: int, user_id: int, rating: int) -> None:
        chat = self._get_chat(chat_id)
        if chat.user.user_id != user_id:
            raise ValueError(f"User {user_id} does not own chat {chat_id}")
        if chat.status is not ChatStatus.CLOSED:
            raise ValueError("A chat can be rated only after it has been closed")
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
            raise ValueError("CSAT rating must be an integer from 1 to 5")
        chat.csat = rating

    def export_chats(self, path: str | Path = "chats.json") -> Path:
        return self._export(path, [chat.to_dict() for chat in self.chats.values()], "All chats")

    def export_chats_by_operator(
        self, operator_id: int, path: str | Path | None = None
    ) -> Path:
        self._get_operator(operator_id)
        destination = path or f"chats_operator_{operator_id}.json"
        chats = [
            chat.to_dict()
            for chat in self.chats.values()
            if chat.operator.operator_id == operator_id
        ]
        return self._export(destination, chats, f"Chats for operator {operator_id}")

    def export_chats_by_user(self, user_id: int, path: str | Path | None = None) -> Path:
        self._get_user(user_id)
        destination = path or f"chats_user_{user_id}.json"
        chats = [
            chat.to_dict()
            for chat in self.chats.values()
            if chat.user.user_id == user_id
        ]
        return self._export(destination, chats, f"Chats for user {user_id}")

    def export_users(self, path: str | Path = "users.json") -> Path:
        users = [user.to_dict() for user in self.users.values()]
        return self._export(path, users, "Users")

    def export_operators(self, path: str | Path = "operators.json") -> Path:
        operators = [operator.to_dict() for operator in self.operators.values()]
        return self._export(path, operators, "Operators")

    def _append_message(
        self, chat: Chat, sender_type: str, sender_id: int, sender_name: str, text: str
    ) -> Message:
        message = _make_message(sender_type, sender_id, sender_name, _validate_message(text))
        chat.messages.append(message)
        return message

    def _get_user(self, user_id: int) -> User:
        try:
            return self.users[user_id]
        except KeyError:
            raise KeyError(f"User {user_id} is not registered") from None

    def _get_operator(self, operator_id: int) -> Operator:
        try:
            return self.operators[operator_id]
        except KeyError:
            raise KeyError(f"Operator {operator_id} is not registered") from None

    def _get_chat(self, chat_id: int) -> Chat:
        try:
            return self.chats[chat_id]
        except KeyError:
            raise KeyError(f"Chat {chat_id} does not exist") from None

    @staticmethod
    def _ensure_open(chat: Chat) -> None:
        if chat.status is not ChatStatus.OPEN:
            raise ValueError(f"Chat {chat.chat_id} is already closed")

    @staticmethod
    def _export(path: str | Path, records: list[dict[str, Any]], label: str) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as file:
            json.dump(records, file, ensure_ascii=False, indent=2)
            file.write("\n")
        print(f"{label}: {len(records)} records exported to {destination}")
        return destination


def _validate_profile(
    full_name: str, city: str, birth_date: date, position: str, experience_years: int
) -> None:
    for field_name, value in (
        ("full_name", full_name),
        ("city", city),
        ("position", position),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")
    if not isinstance(birth_date, date):
        raise ValueError("birth_date must be a datetime.date")
    if (
        isinstance(experience_years, bool)
        or not isinstance(experience_years, int)
        or experience_years < 0
    ):
        raise ValueError("experience_years must be a non-negative integer")


def _validate_message(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Message text must be a non-empty string")
    return text.strip()


def _current_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _make_message(sender_type: str, sender_id: int, sender_name: str, text: str) -> Message:
    return Message(
        sender_type=sender_type,
        sender_id=sender_id,
        sender_name=sender_name,
        text=text,
        sent_at=_current_timestamp(),
    )
