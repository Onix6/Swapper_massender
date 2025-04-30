import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from web3 import Web3

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)
sender = account.address

with open("Swapper.json") as f:
    swapper_abi = json.load(f)

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=swapper_abi)

# --- Хелперы ---
async def reply(update, message):
    await update.message.reply_text(message)

# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, "👋 Привет! Я бот для управления swap-контрактом. Используй /help для команд.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, """
📖 Доступные команды:
/clients – список клиентов
/addclient <адрес> – добавить клиента
/removeclient <адрес> – удалить клиента
/swap <адрес> <процент> – свапнуть % для клиента
/stats – статистика контракта
    """)

async def clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        clients = contract.functions.getClients().call()
        if not clients:
            await reply(update, "🗃 Клиенты не найдены.")
        else:
            msg = "👥 Зарегистрированные клиенты:\n" + "\n".join(clients)
            await reply(update, msg)
    except Exception as e:
        await reply(update, f"Ошибка: {e}")

async def addclient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        return await reply(update, "⚠️ Использование: /addclient <адрес>")

    wallet = Web3.to_checksum_address(context.args[0])
    try:
        nonce = w3.eth.get_transaction_count(sender)
        txn = contract.functions.addClient(wallet).build_transaction({
            "from": sender,
            "nonce": nonce,
            "gas": 100000,
            "gasPrice": w3.to_wei("20", "gwei")
        })
        signed = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        await reply(update, f"✅ Клиент {wallet} добавлен. Tx: {tx_hash.hex()}")
    except Exception as e:
        await reply(update, f"❌ Ошибка: {e}")

async def removeclient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        return await reply(update, "⚠️ Использование: /removeclient <адрес>")

    wallet = Web3.to_checksum_address(context.args[0])
    try:
        nonce = w3.eth.get_transaction_count(sender)
        txn = contract.functions.removeClient(wallet).build_transaction({
            "from": sender,
            "nonce": nonce,
            "gas": 100000,
            "gasPrice": w3.to_wei("20", "gwei")
        })
        signed = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        await reply(update, f"🗑 Клиент {wallet} удалён. Tx: {tx_hash.hex()}")
    except Exception as e:
        await reply(update, f"❌ Ошибка: {e}")

async def swap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        return await reply(update, "⚠️ Использование: /swap <адрес> <процент>")

    wallet = Web3.to_checksum_address(context.args[0])
    percent = int(context.args[1])
    try:
        balance = contract.functions.getTokenBalance(USDT_ADDRESS).call()
        amount = balance * percent // 100

        nonce = w3.eth.get_transaction_count(sender)
        txn = contract.functions.swap(USDT_ADDRESS, wallet, amount).build_transaction({
            "from": sender,
            "nonce": nonce,
            "gas": 100000,
            "gasPrice": w3.to_wei("20", "gwei")
        })
        signed = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        await reply(update, f"✅ Swap на {percent}% ({amount} токенов). Tx: {tx_hash.hex()}")
    except Exception as e:
        await reply(update, f"❌ Ошибка: {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        balance = contract.functions.getTokenBalance(USDT_ADDRESS).call()
        clients = contract.functions.getClients().call()
        await reply(update, f"📊 Баланс контракта: {balance}\n👥 Клиентов: {len(clients)}")
    except Exception as e:
        await reply(update, f"Ошибка: {e}")

# --- Запуск ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("clients", clients))
app.add_handler(CommandHandler("addclient", addclient))
app.add_handler(CommandHandler("removeclient", removeclient))
app.add_handler(CommandHandler("swap", swap))
app.add_handler(CommandHandler("stats", stats))

if __name__ == "__main__":
    print("🤖 Бот запущен")
    app.run_polling()
