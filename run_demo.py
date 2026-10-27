"""Создание примера чатов и выгрузка данных в JSON."""

import random
from collections import Counter
from datetime import date
from pathlib import Path

from helpdesk import Operator, SupportPlatform, User


FIRST_NAMES = [
    "Александр", "Анна", "Дмитрий", "Елена", "Иван", "Мария",
    "Михаил", "Ольга", "Сергей", "Татьяна", "Никита", "Анастасия",
]
LAST_NAMES = [
    "Иванов", "Смирнова", "Кузнецов", "Попова", "Соколов", "Лебедева",
    "Козлов", "Новикова", "Морозов", "Волкова", "Петров", "Соловьёва",
]
CITIES = [
    "Москва", "Санкт-Петербург", "Казань", "Новосибирск",
    "Екатеринбург", "Калининград", "Самара", "Нижний Новгород",
]
USER_POSITIONS = [
    "Менеджер", "Продавец-консультант", "Бухгалтер", "Инженер",
    "Программист", "Студент", "Врач", "Предприниматель",
]
OPERATOR_POSITIONS = [
    "Оператор поддержки", "Старший специалист поддержки",
    "Специалист клиентского сервиса",
]
USER_MESSAGES = [
    "Не получается войти в личный кабинет.",
    "Подскажите, когда будет обработан мой запрос?",
    "Не вижу обновление по заказу.",
    "Помогите изменить данные в профиле.",
    "У меня вопрос по последнему платежу.",
]
OPERATOR_REPLIES = [
    "Здравствуйте! Проверю информацию и помогу разобраться.",
    "Спасибо за подробности. Сейчас посмотрю статус обращения.",
    "Понял вас. Уточните, пожалуйста, когда возникла проблема?",
    "Проверил данные: подготовил решение для вашего обращения.",
]
USER_FOLLOW_UPS = [
    "Проблема появилась сегодня утром.",
    "Спасибо, это именно то, что мне нужно.",
    "Дополнительных деталей пока нет.",
]


def make_full_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def make_birth_date(rng: random.Random, earliest_year: int, latest_year: int) -> date:
    return date(
        rng.randint(earliest_year, latest_year),
        rng.randint(1, 12),
        rng.randint(1, 28),
    )


def create_demo_platform() -> SupportPlatform:
    rng = random.Random(42)
    platform = SupportPlatform(rng=random.Random(43))
    today = date.today()

    for user_id in range(1, 81):
        birth_date = make_birth_date(rng, 1965, 2004)
        maximum_experience = max(0, today.year - birth_date.year - 16)
        platform.add_user(
            User(
                user_id=user_id,
                full_name=make_full_name(rng),
                city=rng.choice(CITIES),
                birth_date=birth_date,
                position=rng.choice(USER_POSITIONS),
                experience_years=rng.randint(0, maximum_experience),
            )
        )

    for operator_id in range(1, 16):
        birth_date = make_birth_date(rng, 1975, 2000)
        maximum_experience = max(0, today.year - birth_date.year - 18)
        platform.add_operator(
            Operator(
                operator_id=operator_id,
                full_name=make_full_name(rng),
                city=rng.choice(CITIES),
                birth_date=birth_date,
                position=rng.choice(OPERATOR_POSITIONS),
                experience_years=rng.randint(0, maximum_experience),
            )
        )

    open_chats = []
    for index in range(120):
        if not platform.get_free_operators():
            oldest_open_chat = open_chats.pop(0)
            platform.close_chat(oldest_open_chat.chat_id, oldest_open_chat.operator.operator_id)
            if rng.random() < 0.75:
                platform.rate_chat(
                    oldest_open_chat.chat_id,
                    oldest_open_chat.user.user_id,
                    rng.randint(1, 5),
                )

        user = platform.users[rng.randint(1, len(platform.users))]
        chat = platform.create_chat(user.user_id, rng.choice(USER_MESSAGES))
        platform.reply_to_chat(chat.chat_id, chat.operator.operator_id, rng.choice(OPERATOR_REPLIES))

        if rng.random() < 0.45:
            platform.send_user_message(chat.chat_id, user.user_id, rng.choice(USER_FOLLOW_UPS))
            platform.reply_to_chat(
                chat.chat_id, chat.operator.operator_id, rng.choice(OPERATOR_REPLIES)
            )

        if index < 117 and rng.random() < 0.72:
            platform.close_chat(chat.chat_id, chat.operator.operator_id)
            if rng.random() < 0.8:
                platform.rate_chat(chat.chat_id, user.user_id, rng.randint(1, 5))
        else:
            open_chats.append(chat)

    return platform


def main() -> None:
    platform = create_demo_platform()
    export_dir = Path(__file__).resolve().parent / "exports"
    chat_counts = Counter(chat.operator.operator_id for chat in platform.chats.values())
    user_counts = Counter(chat.user.user_id for chat in platform.chats.values())
    busiest_operator_id = max(chat_counts, key=chat_counts.get)
    most_active_user_id = max(user_counts, key=user_counts.get)

    platform.export_chats(export_dir / "chats.json")
    platform.export_chats_by_operator(
        busiest_operator_id,
        export_dir / f"chats_operator_{busiest_operator_id}.json",
    )
    platform.export_chats_by_user(
        most_active_user_id,
        export_dir / f"chats_user_{most_active_user_id}.json",
    )
    platform.export_users(export_dir / "users.json")
    platform.export_operators(export_dir / "operators.json")

    open_count = sum(chat.status.value == "open" for chat in platform.chats.values())
    rated_count = sum(chat.csat is not None for chat in platform.chats.values())
    print(
        f"Demo complete: {len(platform.chats)} chats, "
        f"{open_count} open, {rated_count} rated."
    )


if __name__ == "__main__":
    main()
