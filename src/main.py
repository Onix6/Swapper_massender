import sys
import os
import threading
import asyncio

# Добавляем корень проекта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.swap_watcher import SwapWatcher
from src.bot import start_bot
from gui2 import run_gui

def start_swap_monitor():
    watcher = SwapWatcher(config_path='config/config.json')
    watcher.run()

def run_bot_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())

def main():
    # Запускаем SwapWatcher в отдельном потоке
    swap_thread = threading.Thread(target=start_swap_monitor, daemon=True)
    swap_thread.start()

    # Запускаем Telegram-бота в отдельном потоке и loop
    bot_thread = threading.Thread(target=run_bot_in_thread, daemon=True)
    bot_thread.start()

    # GUI должен запускаться в главном потоке
    run_gui()

if __name__ == "__main__":
    main()
