import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from web3 import Web3
import asyncio

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")
USDT_ADDRESS = Web3.to_checksum_address(os.getenv("USDT_ADDRESS"))

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)
sender = account.address

with open("config/swapper_masssender_abi.json") as f:
    swapper_abi = json.load(f)["abi"]

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
        clients = contract.functions.getAllClients().call()
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
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
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
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
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
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        await reply(update, f"✅ Swap на {percent}% ({amount} токенов). Tx: {tx_hash.hex()}")
    except Exception as e:
        await reply(update, f"❌ Ошибка: {e}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        clients = contract.functions.getAllClients().call()

        token_addresses = {
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
            "LDO": "0xC3C7d422809852031b44ab29EEC9F1EfF2A58756"
        }

        msg = f"📊 Баланс контракта по токенам:\n👥 Клиентов: {len(clients)}\n\n"
        for name, addr in token_addresses.items():
            try:
                balance = contract.functions.getTokenBalance(Web3.to_checksum_address(addr)).call()
                msg += f"• {name}: {balance}\n"
            except Exception as e:
                msg += f"• {name}: ошибка\n"

        await reply(update, msg)
    except Exception as e:
        await reply(update, f"❌ Ошибка: {e}")


# --- Запуск ---
async def start_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clients", clients))
    app.add_handler(CommandHandler("addclient", addclient))
    app.add_handler(CommandHandler("removeclient", removeclient))
    app.add_handler(CommandHandler("swap", swap))
    app.add_handler(CommandHandler("stats", stats))

    print("🤖 Бот запущен")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()  # блокируем навсегда

if __name__ == "__main__":
    main()
