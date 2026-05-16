import time
from web3 import Web3
import os
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)
load_dotenv()

rpc_url = os.getenv("RPC_URL")
w3 = Web3(Web3.HTTPProvider(rpc_url))

# العناوين المستهدفة (نحولها لحروف صغيرة)
# 1. الموجه القديم
UNISWAP_V3_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564".lower()
# 2. الموجه الشامل (الأكثر استخداماً حالياً)
UNIVERSAL_ROUTER = "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD".lower()

def start_hunting():
    print(Fore.YELLOW + "🏹 تشغيل الصياد المطور... نراقب Uniswap + حركة الأموال...")
    
    last_block_number = w3.eth.block_number

    while True:
        try:
            current_block_number = w3.eth.block_number

            if current_block_number > last_block_number:
                # نجلب المعاملات
                block = w3.eth.get_block(current_block_number, full_transactions=True)
                print(f"{Fore.WHITE}📦 بلوك {current_block_number} | {len(block['transactions'])} معاملة")

                found_something = False

                for tx in block['transactions']:
                    if tx['to']:
                        to_addr = tx['to'].lower()
                        value_eth = float(w3.from_wei(tx['value'], 'ether'))

                        # الحالة 1: هل هي عملية تداول على Uniswap؟
                        if to_addr == UNISWAP_V3_ROUTER or to_addr == UNIVERSAL_ROUTER:
                            print(f"    {Fore.GREEN}🦄 كشف تداول (Uniswap Swap)!")
                            print(f"    🔗 Hash: {tx['hash'].hex()}")
                            found_something = True

                        # الحالة 2: هل هي حركة أموال كبيرة (أكثر من 0.01 ETH)؟
                        elif value_eth > 0.01: 
                            print(f"    {Fore.CYAN}💰 كشف أموال: شخص نقل {value_eth:.4f} ETH")
                            print(f"    🔗 Hash: {tx['hash'].hex()}")
                            found_something = True

                if not found_something:
                    # طباعة رسالة رمادية خافتة بدلاً من الأحمر المزعج
                    print(f"{Fore.LIGHTBLACK_EX}    ... هدوء ...")

                last_block_number = current_block_number
            
            time.sleep(0.5)

        except Exception as e:
            print(Fore.RED + f"⚠️ خطأ: {e}")
            time.sleep(1)

if __name__ == "__main__":
    start_hunting()