# Telegram-бот для автоматизации администрирования группы

Бот выполняет функции администратора Telegram-группы: антиспам (5 сообщений
за 10 секунд), антимат (список слов на группу), антиссылки (белый список
доменов), систему варнов (3 → автоматический мут на 24 часа), команды
`/mute`, `/unmute`, `/warn`, `/kick`, `/ban`, `/unban`, `/info`, `/stats`,
`/setup`, `/export_logs`. Логи нарушений и действий администраторов
сохраняются в SQLite и в файл `errors.log`.

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# откройте .env, подставьте BOT_TOKEN (из @BotFather) и OWNER_ID
python main.py
```

## Подключение к группе

1. Создайте бота у [@BotFather](https://t.me/BotFather), скопируйте токен.
2. Добавьте бота в группу и выдайте ему права администратора:
   удаление сообщений и ограничение пользователей обязательно.
3. В группе выполните `/setup` — откроется меню настроек.

## Структура проекта

```
bot/
├── main.py                # точка входа
├── config.py              # загрузка .env
├── requirements.txt
├── .env.example
├── database/db.py         # модель SQLite + методы доступа
├── handlers/
│   ├── users.py           # автоматическая модерация
│   ├── admins.py          # /mute, /ban, /warn ...
│   └── setup.py           # меню /setup
├── filters/               # антиспам, антимат, антиссылки
├── utils/                 # logger, decorators
└── keyboards/             # inline-меню
```
