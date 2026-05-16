import time
from web3 import Web3
import os
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)
load_dotenv()

rpc_url = os.getenv("RPC_URL")
w3 = Web3(Web3.HTTPProvider(rpc_url))

UNIVERSAL_ROUTER = "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD".lower()
UNISWAP_V3_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564".lower()

KNOWN_METHODS = {
    "0xb6f9de95": "execute (Universal - عملية شراء/بيع حديثة)",
    "0x3593564c": "execute (اصدار قديم)",
    "0x414bf389": "exactInputSingle (شراء مباشر زوج واحد)",
    "0xdb3e2198": "exactInput (شراء عبر عدة عملات)",
    "0xac9650d8": "multicall (عدة عمليات مجمعة)",
    "0x5ae401dc": "multicall (اصدار اخر)",
    "0x095ea7b3": "approve (موافقة على صرف عملة)"
}

def start_decoding():
    print(Fore.YELLOW + "🔓 نسخة المترجم V2... جاري فك الشفرات...")
    
    last_block_number = w3.eth.block_number

    while True:
        try:
            current_block_number = w3.eth.block_number

            if current_block_number > last_block_number:
                block = w3.eth.get_block(current_block_number, full_transactions=True)
                print(f"{Fore.WHITE}📦 بلوك {current_block_number} | {len(block['transactions'])} معاملة")

                for tx in block['transactions']:
                    if tx['to']:
                        to_addr = tx['to'].lower()
                        
                        if to_addr == UNIVERSAL_ROUTER or to_addr == UNISWAP_V3_ROUTER:
                            
                            # --- التعديل: تحويل مباشر للهيكس ---
                            # نحول المدخلات بالكامل لنص هيكس
                            input_hex = w3.to_hex(tx['input'])
                            
                            # نأخذ أول 10 خانات (0x + 8 أرقام)
                            method_id = input_hex[:10]
                            
                            method_name = KNOWN_METHODS.get(method_id, "غير معروف")

                            # نلون النتيجة
                            if method_name != "غير معروف":
                                print(f"    {Fore.GREEN}🦄 كشف تداول Uniswap")
                                print(f"    🔑 ID: {Fore.YELLOW}{method_id}")
                                print(f"    📝 النوع: {Fore.CYAN}{method_name}")
                                print(f"    🔗 Hash: {tx['hash'].hex()}")
                                print(f"    --------------------------------")

                last_block_number = current_block_number
            
            time.sleep(0.5)

        except Exception as e:
            print(Fore.RED + f"⚠️ خطأ: {e}")
            time.sleep(1)

if __name__ == "__main__":
    start_decoding()