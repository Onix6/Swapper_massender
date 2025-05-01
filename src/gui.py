import sys
import asyncio
import json
import threading
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, QTextEdit
from web3 import Web3
from swap_watcher import SwapWatcher, get_token_symbol, get_token_decimals
from config import swapper_masssender_abi

# --- Конфиг ---
RPC_URL = "https://polygon-rpc.com"
CHAIN_ID = 137
w3 = Web3(Web3.HTTPProvider(RPC_URL))

with open("config.json") as f:
    config = json.load(f)

private_key = config["private_key"]
public_address = w3.to_checksum_address(config["public_address"])
contract_address = w3.to_checksum_address(config["contract_address"])
router_address = w3.to_checksum_address(config["router_address"])


def start_watching_swaps(w3, token_address, amount, logger):
    watcher = SwapWatcher()

    def handle_event(event):
        try:
            from_address = event['args']['from']
            amt = event['args']['amount']
            fee = event['args']['fee']
            logger(f"💱 Swap: from {from_address}, amount: {amt}, fee: {fee}")
        except Exception as e:
            logger(f"❌ Ошибка при обработке ивента: {e}")

    try:
        swap_event = watcher.contract.events.Swap
        event_filter = swap_event.create_filter(from_block='latest')
        logger("👀 Слежение за Swap событиями начато...")

        while True:
            for event in event_filter.get_new_entries():
                handle_event(event)
            time.sleep(2)
    except Exception as e:
        logger(f"❌ Ошибка при создании фильтра событий: {e}")


class SwapWatcherApp(QMainWindow):
    def __init__(self):
        super(SwapWatcherApp, self).__init__()

        self.setWindowTitle("Swap Watcher GUI")
        self.setGeometry(100, 100, 600, 420)

        self.label_token = QLabel("Token Address:", self)
        self.label_token.move(20, 20)
        self.input_token = QLineEdit(self)
        self.input_token.setGeometry(150, 20, 400, 25)

        self.label_amount = QLabel("Amount:", self)
        self.label_amount.move(20, 60)
        self.input_amount = QLineEdit(self)
        self.input_amount.setGeometry(150, 60, 200, 25)

        self.start_button = QPushButton("Start Watching", self)
        self.start_button.setGeometry(20, 100, 150, 40)
        self.start_button.clicked.connect(self.start_watcher_thread)

        self.balance_button = QPushButton("Показать баланс контракта", self)
        self.balance_button.setGeometry(200, 100, 200, 40)
        self.balance_button.clicked.connect(self.show_contract_balances)

        self.fund_button = QPushButton("Пополнить контракт", self)
        self.fund_button.setGeometry(420, 100, 150, 40)
        self.fund_button.clicked.connect(self.fund_contract)

        self.show_clients_button = QPushButton("Показать клиентов", self)
        self.show_clients_button.setGeometry(20, 150, 150, 30)
        self.show_clients_button.clicked.connect(self.show_clients)

        self.log_output = QTextEdit(self)
        self.log_output.setGeometry(20, 190, 550, 200)
        self.log_output.setReadOnly(True)

    def log(self, message):
        self.log_output.append(message)

    def start_watcher_thread(self):
        token_address = self.input_token.text().strip()
        amount = self.input_amount.text().strip()

        if not token_address or not amount:
            self.log("❌ Укажите адрес токена и количество.")
            return

        def run():
            start_watching_swaps(w3, token_address, float(amount), self.log)

        thread = threading.Thread(target=run)
        thread.start()

    def show_contract_balances(self):
        token_address = self.input_token.text().strip()
        if not token_address:
            self.log("❌ Укажите адрес токена.")
            return

        try:
            token = w3.eth.contract(address=w3.to_checksum_address(token_address), abi=erc20_abi)
            symbol = get_token_symbol(token)
            decimals = get_token_decimals(token)
            token_balance = token.functions.balanceOf(contract_address).call() / (10 ** decimals)

            matic_balance = w3.eth.get_balance(contract_address) / (10 ** 18)

            self.log(f"📊 Баланс контракта:")
            self.log(f"- {symbol}: {token_balance:.4f}")
            self.log(f"- MATIC: {matic_balance:.4f}")
        except Exception as e:
            self.log(f"❌ Ошибка при получении баланса: {e}")

    def fund_contract(self):
        token_address = self.input_token.text().strip()
        amount_str = self.input_amount.text().strip()

        if not token_address or not amount_str:
            self.log("❌ Укажите адрес токена и количество для пополнения.")
            return

        try:
            token = w3.eth.contract(address=w3.to_checksum_address(token_address), abi=erc20_abi)
            decimals = get_token_decimals(token)
            amount = int(float(amount_str) * (10 ** decimals))

            tx = token.functions.transfer(contract_address, amount).build_transaction({
                'from': public_address,
                'nonce': w3.eth.get_transaction_count(public_address),
                'gas': 100000,
                'gasPrice': w3.to_wei('50', 'gwei'),
                'chainId': CHAIN_ID
            })

            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            self.log(f"🚀 Пополнение отправлено! TxHash: {tx_hash.hex()}")
        except Exception as e:
            self.log(f"❌ Ошибка при пополнении: {e}")

    def show_clients(self):
        try:
            with open("clients.json", "r") as f:
                clients = json.load(f)
            if not clients:
                self.log("⚠️ Нет клиентов.")
                return
            self.log("📬 Подключенные клиенты:")
            for addr in clients:
                self.log(f"- {addr}")
        except Exception as e:
            self.log(f"❌ Ошибка при чтении клиентов: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SwapWatcherApp()
    window.show()
    sys.exit(app.exec_())
