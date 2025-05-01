from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTextEdit, QMessageBox, QHBoxLayout
)
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt
from web3 import Web3
import logging
import json
import sys

# Загрузка ABI и адреса контракта
with open("config/swapper_masssender_abi.json") as f:
    abi = json.load(f)["abi"]

with open("contract_address.txt") as f:
    contract_address = f.read().strip()

TOKENS = {
    "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    "MATIC": "0x0000000000000000000000000000000000001010",
    "LINK": "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39",
    "XSGD": "0xDC3326e71D45186F113a2F448984CA0e8D201995",
    "AAVE": "0xD6DF932A45C0f255f85145f286eA0b292B21C90B",
    "DAI": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
    "SUSHI": "0x0b3F868E0BE5597D5DB7fEB59E1CADBb0fdDa50a",
    "BET": "0xbF7970D56a150cD0b60BD08388A4A75a27777777",
    "VPOL": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
    "GRT": "0x5fe2B58c013d7601147DcdD68C143A77499f5531",
    "FRAX": "0x45c32fA6DF82ead1e2EF74d17b76547EDdFaFF89",
    "WBTC": "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",
    "WETH": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
    "CRV": "0x172370d5Cd63279eFa6d502DAB29171933a610AF",
    "SOL": "0xd93f7E271cB87c23AaA73edC008A79646d1F9912",
    "LDO": "0xC3C7d422809852031b44ab29EEC9F1EfF2A58756",
}

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
]

web3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
address = None
private_key = None
contract = None
token_balances = {}

logger = logging.getLogger("SwapperLogger")
logger.setLevel(logging.INFO)

def apply_dark_theme(app):
    dark_style = """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
            font-family: Segoe UI, sans-serif;
            font-size: 14px;
        }
        QPushButton {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #5c5c5c;
            padding: 5px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #505357;
        }
        QLineEdit, QTextEdit, QComboBox {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #5c5c5c;
            border-radius: 4px;
        }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
            border: 1px solid #ffaa00;
        }
        QLabel {
            color: #dddddd;
        }
    """
    app.setStyleSheet(dark_style)

class SwapperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Swapper PyQt5")
        self.setGeometry(200, 100, 600, 800)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Ввод ключа
        self.private_key_input = QLineEdit()
        self.private_key_input.setPlaceholderText("🔑 Введите приватный ключ")
        self.private_key_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.private_key_input)

        self.connect_button = QPushButton("Подключить кошелек")
        self.connect_button.clicked.connect(self.connect_wallet)
        self.layout.addWidget(self.connect_button)

        # Swap
        self.token_selector = QComboBox()
        self.layout.addWidget(self.token_selector)

        self.to_input = QLineEdit("0x...получатель")
        self.layout.addWidget(self.to_input)

        self.amount_input = QLineEdit("0.15")
        self.layout.addWidget(self.amount_input)

        self.swap_button = QPushButton("Выполнить swap")
        self.swap_button.clicked.connect(self.swap_token)
        self.layout.addWidget(self.swap_button)

        # Массовая отправка
        self.batch_addr_input = QLineEdit("0x...,0x...")
        self.layout.addWidget(QLabel("📤 Массовая отправка USDT (адреса)"))
        self.layout.addWidget(self.batch_addr_input)

        self.batch_amt_input = QLineEdit("0.1,0.2")
        self.layout.addWidget(QLabel("Суммы через запятую"))
        self.layout.addWidget(self.batch_amt_input)

        self.batch_button = QPushButton("Отправить USDT")
        self.batch_button.clicked.connect(self.send_batch)
        self.layout.addWidget(self.batch_button)

        # Управление клиентами
        self.client_input = QLineEdit("0x...адрес клиента")
        self.layout.addWidget(QLabel("👥 Добавить клиента"))
        self.layout.addWidget(self.client_input)

        self.add_client_button = QPushButton("Добавить клиента")
        self.add_client_button.clicked.connect(self.add_client)
        self.layout.addWidget(self.add_client_button)

        self.get_clients_button = QPushButton("Получить список клиентов")
        self.get_clients_button.clicked.connect(self.get_clients)
        self.layout.addWidget(self.get_clients_button)

        # Логи
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.layout.addWidget(QLabel("📜 Логи"))
        self.layout.addWidget(self.log_output)

        handler = logging.StreamHandler(self)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

    def write(self, message):
        self.log_output.append(message.strip())

    def connect_wallet(self):
        global private_key, address, contract
        private_key = self.private_key_input.text()
        try:
            acct = web3.eth.account.from_key(private_key)
            address = acct.address
            contract = web3.eth.contract(address=contract_address, abi=abi)
            QMessageBox.information(self, "Успех", f"Кошелёк подключён: {address}")
            self.update_tokens()
            logger.info(f"Кошелек подключён: {address}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def update_tokens(self):
        self.token_selector.clear()
        token_balances.clear()
        for name, addr in TOKENS.items():
            try:
                token = web3.eth.contract(address=addr, abi=ERC20_ABI)
                dec = token.functions.decimals().call()
                bal = token.functions.balanceOf(address).call()
                if bal > 0:
                    human = bal / 10**dec
                    label = f"{name} ({human:.4f})"
                    self.token_selector.addItem(label)
                    token_balances[label] = addr
            except Exception as e:
                logger.error(f"Ошибка при обновлении токена {name}: {e}")

    def send_tx(self, func):
        try:
            tx = func.build_transaction({
                'from': address,
                'nonce': web3.eth.get_transaction_count(address),
                'gas': 500000,
                'gasPrice': web3.eth.gas_price
            })
            signed = web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            logger.info(f"Tx Hash: {receipt.transactionHash.hex()}")
            return receipt.transactionHash.hex()
        except Exception as e:
            logger.error(f"Ошибка транзакции: {e}")
            raise

    def swap_token(self):
        token_label = self.token_selector.currentText()
        token_addr = token_balances.get(token_label)
        to = self.to_input.text()

        try:
            token = web3.eth.contract(address=token_addr, abi=ERC20_ABI)
            decimals = token.functions.decimals().call()
            amount = int(float(self.amount_input.text()) * (10 ** decimals))

            tx_hash = self.send_tx(contract.functions.swap(token_addr, to, amount))
            QMessageBox.information(self, "Swap", f"Tx Hash: {tx_hash}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка swap", str(e))

    def send_batch(self):
        recipients = self.batch_addr_input.text().split(",")
        try:
            amounts = [int(float(x) * 1e6) for x in self.batch_amt_input.text().split(",")]
            tx_hash = self.send_tx(contract.functions.sendBatchUSDT(recipients, amounts))
            QMessageBox.information(self, "Batch", f"Tx Hash: {tx_hash}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка Batch", str(e))

    def add_client(self):
        addr = self.client_input.text()
        try:
            tx_hash = self.send_tx(contract.functions.addClient(addr))
            QMessageBox.information(self, "Клиент", f"Tx Hash: {tx_hash}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def get_clients(self):
        try:
            clients = contract.functions.getAllClients().call()
            QMessageBox.information(self, "Клиенты", "\n".join(clients))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


def run_gui():
    app = QApplication(sys.argv)
    apply_dark_theme(app)  # добавлено
    window = SwapperApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_gui()