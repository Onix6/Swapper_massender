### README.md
# Swap Watcher GUI

Приложение для отслеживания Swap-событий в смарт-контрактах Ethereum с GUI-интерфейсом.

## Установка
```bash
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt
```

## Конфигурация
Отредактируйте `config.json`, указав:
- RPC URL
- Адрес смарт-контракта
- Список кошельков для отслеживания
- ABI события `Swap`
- Данные Telegram бота

## Запуск
```bash
python gui.py
```

## Структура проекта
```
swap_watcher_project/
│
├── gui.py                  # Главный GUI-файл
├── config.json             # Конфигурационный файл
├── requirements.txt        # Зависимости
├── README.md               # Инструкция
└── watcher/
    ├── __init__.py
    └── watcher.py          # Логика отслеживания событий
```

## Возможности
- Загрузка конфигурации через GUI
- Старт/стоп отслеживания событий Swap
- Логирование событий
- Уведомления в Telegram
