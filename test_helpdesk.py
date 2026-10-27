import json
import random
import tempfile
import unittest
from datetime import date
from pathlib import Path

from helpdesk import Operator, SupportPlatform, User


class SupportPlatformTests(unittest.TestCase):
    def setUp(self) -> None:
        self.platform = SupportPlatform(random.Random(1))
        self.user = User(1, "Анна Иванова", "Москва", date(1990, 5, 12), "Менеджер", 8)
        self.operator = Operator(
            1, "Иван Петров", "Казань", date(1988, 3, 10), "Оператор поддержки", 5
        )
        self.platform.add_user(self.user)
        self.platform.add_operator(self.operator)

    def test_chat_lifecycle_tracks_operator_availability_and_csat(self) -> None:
        chat = self.platform.create_chat(self.user.user_id, "Нужна помощь")
        self.assertTrue(self.operator.is_busy)
        self.assertEqual(len(chat.messages), 1)

        with self.assertRaises(RuntimeError):
            self.platform.create_chat(self.user.user_id, "Второе обращение")
        with self.assertRaises(ValueError):
            self.platform.rate_chat(chat.chat_id, self.user.user_id, 5)

        self.platform.reply_to_chat(chat.chat_id, self.operator.operator_id, "Помогу.")
        self.platform.close_chat(chat.chat_id, self.operator.operator_id)
        self.platform.rate_chat(chat.chat_id, self.user.user_id, 5)

        self.assertFalse(self.operator.is_busy)
        self.assertEqual(chat.csat, 5)
        self.assertEqual([message.sender_type for message in chat.messages], ["user", "operator"])

    def test_messages_and_ratings_validate_ownership_and_content(self) -> None:
        chat = self.platform.create_chat(self.user.user_id, "Вопрос")
        with self.assertRaises(ValueError):
            self.platform.send_user_message(chat.chat_id, 2, "Чужой чат")
        with self.assertRaises(ValueError):
            self.platform.reply_to_chat(chat.chat_id, 2, "Чужой оператор")
        with self.assertRaises(ValueError):
            self.platform.send_user_message(chat.chat_id, self.user.user_id, "  ")

        self.platform.close_chat(chat.chat_id, self.operator.operator_id)
        with self.assertRaises(ValueError):
            self.platform.rate_chat(chat.chat_id, self.user.user_id, 0)

    def test_exports_write_complete_and_filtered_json(self) -> None:
        chat = self.platform.create_chat(self.user.user_id, "Проверка выгрузки")
        self.platform.reply_to_chat(chat.chat_id, self.operator.operator_id, "Ответ")
        self.platform.close_chat(chat.chat_id, self.operator.operator_id)
        self.platform.rate_chat(chat.chat_id, self.user.user_id, 4)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            all_chats_path = self.platform.export_chats(root / "nested" / "chats.json")
            operator_path = self.platform.export_chats_by_operator(1, root / "operator.json")
            user_path = self.platform.export_chats_by_user(1, root / "user.json")
            users_path = self.platform.export_users(root / "users.json")
            operators_path = self.platform.export_operators(root / "operators.json")

            all_chats = json.loads(all_chats_path.read_text(encoding="utf-8"))
            self.assertEqual(len(all_chats), 1)
            self.assertEqual(all_chats[0]["csat"], 4)
            self.assertEqual(len(all_chats[0]["messages"]), 2)
            self.assertEqual(len(json.loads(operator_path.read_text(encoding="utf-8"))), 1)
            self.assertEqual(len(json.loads(user_path.read_text(encoding="utf-8"))), 1)
            self.assertEqual(json.loads(users_path.read_text(encoding="utf-8"))[0]["city"], "Москва")
            self.assertEqual(
                json.loads(operators_path.read_text(encoding="utf-8"))[0]["is_busy"],
                False,
            )


if __name__ == "__main__":
    unittest.main()
