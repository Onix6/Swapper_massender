import sys
import threading
import asyncio
import json
import time
import traceback
import logging
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QTextEdit, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from web3 import Web3
from eth_abi import decode_abi
import requests

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SwapWatcher(QObject):
    log_signal = pyqtSignal(str)

    def __init__(self, config_file):
        super().__init__()
        self.running = False
        self.config_file = config_file
        self.web3 = None
        self.contract = None
        self.token_contract = None
        self.router_contract = None
        self.known_wallets = []
        self.swap_event = None
        self.loop = None
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            self.web3 = Web3(Web3.HTTPProvider(config['rpc_url']))
            self.contract = self.web3.eth.contract(address=config['contract_address'], abi=config['contract_abi'])
            self.token_contract = self.web3.eth.contract(address=config['token_address'], abi=config['token_abi'])
            self.router_contract = self.web3.eth.contract(address=config['router_address'], abi=config['router_abi'])
            self.swap_event = self.router_contract.events.Swap.createFilter(fromBlock='latest')

            self.known_wallets = self.contract.functions.getClients().call()
            self.swap_method = self.contract.functions.swap
            self.swap_amount = int(config['swap_amount'])
            self.telegram_token = config['telegram_token']
            self.telegram_chat_id = config['telegram_chat_id']

            logger.info("Config loaded and contracts initialized.")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def start(self):
        if self.running:
            return
        self.running = True
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_loop, daemon=True).start()

    def stop(self):
        self.running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

    def run_loop(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.watch_swaps())
        except Exception as e:
            logger.error(f"Watcher loop error: {e}")
            self.log_signal.emit(f"Watcher error: {e}")

    async def watch_swaps(self):
        logger.info("SwapWatcher started")
        self.log_signal.emit("SwapWatcher started")
        while self.running:
            try:
                entries = self.swap_event.get_new_entries()
                for event in entries:
                    from_address = event['args']['sender']
                    if from_address in self.known_wallets:
                        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                        log_msg = f"Swap from known wallet: {from_address} at {timestamp}"
                        logger.info(log_msg)
                        self.log_signal.emit(log_msg)

                        tx_hash = self.send_swap(from_address)
                        notify = f"Swap initiated for {from_address}: {tx_hash}"
                        logger.info(notify)
                        self.log_signal.emit(notify)
                        self.send_telegram_notification(notify)
                await asyncio.sleep(2)
            except Exception as e:
                err_msg = f"Error in event loop: {traceback.format_exc()}"
                logger.error(err_msg)
                self.log_signal.emit(err_msg)
                await asyncio.sleep(5)

    def send_swap(self, wallet):
        tx = self.swap_method(wallet, self.swap_amount).buildTransaction({
            'from': wallet,
            'nonce': self.web3.eth.get_transaction_count(wallet),
            'gas': 2000000,
            'gasPrice': self.web3.toWei('5', 'gwei')
        })
        # Здесь можно подписать и отправить транзакцию, если есть приватный ключ
        return 'tx_hash_stub'

    def send_telegram_notification(self, message):
        try:
            requests.get(
                f'https://api.telegram.org/bot{self.telegram_token}/sendMessage',
                params={
                    'chat_id': self.telegram_chat_id,
                    'text': message
                }
            )
        except Exception as e:
            logger.error(f"Telegram notification error: {e}")
            self.log_signal.emit(f"Telegram error: {e}")


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.watcher = None

    def initUI(self):
        self.setWindowTitle('Swap Watcher GUI')
        layout = QVBoxLayout()

        self.status_label = QLabel('Статус: Остановлен')
        layout.addWidget(self.status_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.load_config_btn = QPushButton('Загрузить config.json')
        self.load_config_btn.clicked.connect(self.load_config)
        layout.addWidget(self.load_config_btn)

        self.start_btn = QPushButton('▶️ Старт')
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_watcher)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton('⏹️ Стоп')
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_watcher)
        layout.addWidget(self.stop_btn)

        self.setLayout(layout)
        self.setGeometry(300, 300, 600, 400)

    def append_log(self, text):
        self.log_output.append(text)

    def load_config(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Выбрать config.json', '', 'JSON files (*.json)')
        if file_name:
            try:
                self.watcher = SwapWatcher(file_name)
                self.watcher.log_signal.connect(self.append_log)
                self.start_btn.setEnabled(True)
                self.append_log("✅ Конфигурация загружена успешно")
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Ошибка при загрузке конфигурации: {str(e)}')

    def start_watcher(self):
        if self.watcher:
            self.watcher.start()
            self.status_label.setText('Статус: Запущен ✅')
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)

    def stop_watcher(self):
        if self.watcher:
            self.watcher.stop()
            self.status_label.setText('Статус: Остановлен ⛔')
            self.stop_btn.setEnabled(False)
            self.start_btn.setEnabled(True)
            self.append_log("⛔ Наблюдение остановлено")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = App()
    mainWin.show()
    sys.exit(app.exec_())
