import time
import os
from dotenv import load_dotenv
from colorama import Fore, Style, init
from web3 import Web3
from executor import execute_flash_loan 

try:
    from web3 import WebsocketProvider
except ImportError:
    from web3.providers.websocket import WebsocketProvider

from token_utils import get_real_amount, get_token_details 

init(autoreset=True)
load_dotenv()

ws_url = os.getenv("WS_URL") 
if not ws_url or not ws_url.startswith("ws"):
    print(Fore.RED + "❌ خطأ: تأكد من وجود WS_URL")
    exit()

try:
    w3 = Web3(WebsocketProvider(ws_url, websocket_timeout=60))
    if not w3.is_connected(): raise Exception("Not Connected")
    print(Fore.GREEN + "✅ تم الاتصال بنجاح!")
except Exception as e:
    print(Fore.RED + f"🚨 خطأ: {e}")
    exit()

UNISWAP_V3_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
ROUTER_ABI = '[{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct ISwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}]'

router_contract = w3.eth.contract(address=UNISWAP_V3_ROUTER, abi=ROUTER_ABI)

def start_parsing():
    print(Fore.YELLOW + "🕵️  المراقبة المباشرة (Live Monitor)...")
    try:
        block_filter = w3.eth.filter('latest')
    except: return

    while True:
        try:
            for block_hash in block_filter.get_new_entries():
                try:
                    block = w3.eth.get_block(block_hash, full_transactions=True)
                    
                    for tx in block['transactions']:
                        if tx.get('to') and tx['to'].lower() == UNISWAP_V3_ROUTER.lower():
                            try:
                                func_obj, func_params = router_contract.decode_function_input(tx['input'])
                                
                                if func_obj.fn_name == "exactInputSingle":
                                    params = func_params['params']
                                    token_in = params['tokenIn']
                                    token_out = params['tokenOut']
                                    amount_in = params['amountIn']
                                    fee = params['fee'] # ✅ استخراج الرسوم (مهم جداً لتحديد المسبح)
                                    
                                    real_amount = get_real_amount(w3, token_in, amount_in)
                                    
                                    if real_amount > 10: 
                                        in_info = get_token_details(w3, token_in)
                                        out_info = get_token_details(w3, token_out)
                                        
                                        print(f"\n{Fore.GREEN}🎯 صيد ثمين!")
                                        print(f"    📥 {in_info['symbol']} -> 📤 {out_info['symbol']}")
                                        print(f"    💰 الكمية: {real_amount:,.2f}")
                                        print(f"    🔗 Hash: {tx['hash'].hex()}")
                                        
                                        # ✅ إرسال كل المعلومات الضرورية للمحرك
                                        print(f"    ⚡ استدعاء المحرك...")
                                        execute_flash_loan(token_in, token_out, amount_in, fee)

                            except Exception: continue
                except Exception: continue
            time.sleep(0.1) 
        except Exception:
            time.sleep(2)
            try: block_filter = w3.eth.filter('latest')
            except: pass

if __name__ == "__main__":
    start_parsing()