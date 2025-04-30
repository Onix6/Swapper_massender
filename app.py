import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from web3 import Web3
import logging
import json

# === Загрузка ABI и адреса контракта ===
with open("swapper_abi.json") as f:
    abi = json.load(f)["abi"]

with open("contract_address.txt") as f:
    contract_address = f.read().strip()

TOKENS = {
    "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    # другие токены...
}

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    }
]

# === Инициализация логгера ===
class GUIHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.after(0, self.text_widget.insert, tk.END, msg + "\n")
        self.text_widget.after(0, self.text_widget.see, tk.END)

logger = logging.getLogger("SwapperLogger")
logger.setLevel(logging.INFO)

# === Переменные ===
web3 = None
contract = None
address = None
private_key = None
token_balances = {}

# === GUI ===
root = tk.Tk()
root.title("Swapper GUI")
root.geometry("650x850")
root.configure(bg="#1e1e1e")

style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background="#1e1e1e")
style.configure("TLabel", background="#1e1e1e", foreground="white", font=("Segoe UI", 10))
style.configure("TButton", background="#333333", foreground="white", font=("Segoe UI", 10), padding=6)
style.configure("TEntry", fieldbackground="#333333", foreground="white")
style.configure("TCombobox", fieldbackground="#333333", background="#333333", foreground="white")

main_frame = ttk.Frame(root)
main_frame.pack(padx=20, pady=20, fill="both", expand=True)

# === Обработчики ===
def get_erc20_balance(token_address, user_address):
    try:
        token_contract = web3.eth.contract(address=token_address, abi=ERC20_ABI)
        decimals = token_contract.functions.decimals().call()
        balance = token_contract.functions.balanceOf(user_address).call()
        return balance / (10 ** decimals)
    except Exception as e:
        logger.error(f"Ошибка получения баланса: {e}")
        return None

def send_tx(func):
    try:
        tx = func.build_transaction({
            'from': address,
            'nonce': web3.eth.get_transaction_count(address),
            'gas': 500000,
            'gasPrice': web3.to_wei('10', 'gwei')
        })
        signed = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Tx sent: {web3.to_hex(receipt.transactionHash)}")
        return web3.to_hex(receipt.transactionHash)
    except Exception as e:
        logger.error(f"Ошибка транзакции: {e}")
        return f"Ошибка: {e}"

def handle_set_private_key():
    global private_key, web3, address, contract
    private_key = entry_private_key.get()
    web3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
    account = web3.eth.account.from_key(private_key)
    address = account.address
    contract = web3.eth.contract(address=contract_address, abi=abi)
    logger.info(f"Адрес подключён: {address}")
    messagebox.showinfo("Успех", f"Кошелёк подключён: {address}")
    update_token_list()

def update_token_list():
    token_dropdown['values'] = []
    token_balances.clear()
    items = []
    for symbol, token_address in TOKENS.items():
        balance = get_erc20_balance(token_address, address)
        if balance is not None and balance > 0:
            label = f"{symbol} ({balance:.4f})"
            items.append(label)
            token_balances[label] = token_address
    token_dropdown['values'] = items
    token_dropdown.set(items[0] if items else "Нет токенов")

def handle_swap():
    selected = token_dropdown.get()
    token = token_balances.get(selected)
    to = entry_to.get()
    try:
        amount = int(float(entry_amount.get()) * 1e6)
        tx_hash = send_tx(contract.functions.swap(token, to, amount))
        messagebox.showinfo("Swap", f"Tx Hash: {tx_hash}")
    except Exception as e:
        logger.error(f"Swap error: {e}")
        messagebox.showerror("Ошибка", str(e))

def handle_send_batch():
    recipients = entry_batch_addresses.get().split(",")
    try:
        amounts = [int(float(a.strip()) * 1e6) for a in entry_batch_amounts.get().split(",")]
        tx_hash = send_tx(contract.functions.sendBatchUSDT(recipients, amounts))
        messagebox.showinfo("Batch", f"Tx Hash: {tx_hash}")
    except Exception as e:
        logger.error(f"Batch error: {e}")
        messagebox.showerror("Ошибка", str(e))

def handle_withdraw_usdt():
    tx_hash = send_tx(contract.functions.withdrawAllUSDT())
    messagebox.showinfo("Withdraw USDT", f"Tx Hash: {tx_hash}")

def handle_withdraw_token():
    token = entry_withdraw_token.get()
    tx_hash = send_tx(contract.functions.withdrawAllToken(token))
    messagebox.showinfo("Withdraw Token", f"Tx Hash: {tx_hash}")

def handle_get_balance():
    token = entry_balance_token.get()
    try:
        balance = contract.functions.getTokenBalance(token).call()
        messagebox.showinfo("Баланс токена", f"Баланс: {balance}")
    except Exception as e:
        logger.error(f"Ошибка получения баланса токена: {e}")
        messagebox.showerror("Ошибка", str(e))

def handle_add_client():
    client_address = entry_add_client.get()
    try:
        tx_hash = send_tx(contract.functions.addClient(client_address))
        messagebox.showinfo("Добавить клиента", f"Tx Hash: {tx_hash}")
    except Exception as e:
        logger.error(f"Ошибка добавления клиента: {e}")
        messagebox.showerror("Ошибка", str(e))

def handle_get_clients():
    try:
        clients = contract.functions.getAllClients().call()
        messagebox.showinfo("Клиенты", f"Клиенты: {', '.join(clients)}")
    except Exception as e:
        logger.error(f"Ошибка получения клиентов: {e}")
        messagebox.showerror("Ошибка", str(e))

# === Виджеты ===
# Добавление клиента
ttk.Label(main_frame, text="🔑 Приватный ключ").pack(anchor="w", pady=(0, 5))
entry_private_key = ttk.Entry(main_frame, show="*", width=60)
entry_private_key.pack(fill="x", pady=(0, 10))
ttk.Button(main_frame, text="Подключить кошелек", command=handle_set_private_key).pack(pady=(0, 20))

# Swap токен
ttk.Label(main_frame, text="🔄 Swap токен").pack(anchor="w")
token_dropdown = ttk.Combobox(main_frame, state="readonly")
token_dropdown.pack(fill="x", pady=5)
entry_to = ttk.Entry(main_frame)
entry_to.insert(0, "0x...получатель")
entry_to.pack(fill="x", pady=5)
entry_amount = ttk.Entry(main_frame)
entry_amount.insert(0, "0.15")
entry_amount.pack(fill="x", pady=(0, 10))
ttk.Button(main_frame, text="Выполнить swap", command=handle_swap).pack(pady=(0, 15))

# Массовая отправка
ttk.Label(main_frame, text="📤 Массовая отправка USDT").pack(anchor="w")
entry_batch_addresses = ttk.Entry(main_frame)
entry_batch_addresses.insert(0, "0x...,0x...")
entry_batch_addresses.pack(fill="x", pady=5)
entry_batch_amounts = ttk.Entry(main_frame)
entry_batch_amounts.insert(0, "0.1,0.2")
entry_batch_amounts.pack(fill="x", pady=5)
ttk.Button(main_frame, text="Отправить USDT", command=handle_send_batch).pack(pady=(0, 20))

# Управление клиентами
ttk.Label(main_frame, text="👥 Добавить клиента").pack(anchor="w", pady=(10, 5))
entry_add_client = ttk.Entry(main_frame)
entry_add_client.insert(0, "0x...адрес клиента")
entry_add_client.pack(fill="x", pady=5)
ttk.Button(main_frame, text="Добавить клиента", command=handle_add_client).pack(pady=(0, 15))
ttk.Button(main_frame, text="Получить список клиентов", command=handle_get_clients).pack(pady=(0, 15))

# Логи
ttk.Label(main_frame, text="📜 Логи").pack(anchor="w", pady=(10, 5))
log_text = scrolledtext.ScrolledText(main_frame, height=10, bg="#1e1e1e", fg="white", insertbackground="white", wrap="word")
log_text.pack(fill="both", expand=True, pady=(0, 10))

# === Логирование в файл и GUI ===
file_handler = logging.FileHandler("swapper_gui.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
gui_handler = GUIHandler(log_text)
gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
logger.addHandler(gui_handler)

# === Запуск ===
root.mainloop()
