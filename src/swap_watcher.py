import json
import logging
import time
from web3 import Web3


class SwapWatcher:
    def __init__(self, config_path='config/swapper_masssender_abi.json'):
        self.web3 = Web3(Web3.HTTPProvider("https://polygon-mainnet.infura.io/v3/e516cbd5e1d443ff94ba24a98ff0ce99"))
        self.contract_address = self.web3.to_checksum_address("0x67f067df06821666877D9EF7fdDad5A796898068")

        with open(config_path) as abi_file:
            ABI = json.load(abi_file)["abi"]

        self.contract = self.web3.eth.contract(address=self.contract_address, abi=ABI)

    def print_events(self):
        try:
            print("Events in contract ABI:")
            for event in self.contract.events:
                print(f"Event: {event}")
        except Exception as e:
            logging.error(f"Error printing events: {e}")

    def run(self):
        logging.basicConfig(level=logging.INFO)
        logging.info("SwapWatcher started watching Swap events...")

        self.print_events()

        try:
            swap_event = self.contract.events.Swap
            event_filter = swap_event.create_filter(from_block='latest')
        except Exception as e:
            logging.error(f"Error creating event filter: {e}")
            return

        while True:
            try:
                for event in event_filter.get_new_entries():
                    self.handle_swap_event(event)
                time.sleep(2)
            except Exception as e:
                logging.error(f"Error in event loop: {e}")
                time.sleep(5)

    def handle_swap_event(self, event):
        try:
            from_address = event['args']['from']
            amount = event['args']['amount']
            fee = event['args']['fee']
            self.log_swap_event(from_address, amount, fee)
        except Exception as e:
            logging.error(f"Error handling Swap event: {e}")

    def log_swap_event(self, from_address, amount, fee):
        logging.info(f"Swap event: from {from_address}, amount: {amount}, fee: {fee}")


# Дополнительные функции для использования в GUI

def get_token_symbol(token_contract):
    try:
        return token_contract.functions.symbol().call()
    except:
        return "UNKNOWN"


def get_token_decimals(token_contract):
    try:
        return token_contract.functions.decimals().call()
    except:
        return 18
