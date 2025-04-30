import asyncio
from web3 import Web3
from eth_abi import decode_abi
import logging
import requests
import json
import time

# Настройки Web3 и контракта
web3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_INFURA_KEY"))
contract_address = "0xYourContractAddress"
ABI = json.loads(open('swapper_abi.json').read())["abi"]
contract = web3.eth.contract(address=contract_address, abi=ABI)

# Вспомогательная функция для отслеживания событий Swap
def monitor_swap_events():
    event_filter = contract.events.Swap.createFilter(fromBlock='latest')
    while True:
        for event in event_filter.get_new_entries():
            handle_swap_event(event)
        time.sleep(2)

# Обработка события Swap
def handle_swap_event(event):
    try:
        data = decode_abi(
            ['address', 'uint256', 'uint256'], bytes.fromhex(event['data'][2:])
        )
        from_token = data[0]
        amount_in = data[1]
        amount_out = data[2]
        log_swap_event(from_token, amount_in, amount_out)
    except Exception as e:
        logging.error(f"Error handling swap event: {e}")

# Логирование события Swap
def log_swap_event(from_token, amount_in, amount_out):
    logging.info(f"Swap event: {from_token} swapped {amount_in} for {amount_out}")

# Запуск мониторинга
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting Swap Watcher...")
    monitor_swap_events()
