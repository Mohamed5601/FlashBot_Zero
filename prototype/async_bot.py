import asyncio
import json
import os
import time
import requests
from requests.adapters import HTTPAdapter
from web3 import Web3, AsyncWeb3
from web3.providers import AsyncHTTPProvider
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)
load_dotenv()

# ==============================================================================
# 1. إعدادات الاتصال (Base Network)
# ==============================================================================
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

if not RPC_URL or not PRIVATE_KEY:
    print(Fore.RED + "❌ خطأ: ملف .env غير مكتمل.")
    exit()

session = requests.Session()
adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
session.mount('https://', adapter)
w3_sync = Web3(Web3.HTTPProvider(RPC_URL, session=session))

# ==============================================================================
# 2. العناوين (Base Mainnet)
# ==============================================================================
QUOTER_V2 = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"
FACTORY   = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"

TOKENS = {
    # العمالقة (يستحملوا قروض ضخمة)
    "USDC":    "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "WETH":    "0x4200000000000000000000000000000000000006",
    "USDbC":   "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
    
    # القناصة (تذبذب عالي وسقف سيولة محدد)
    "AERO":    "0x940181a94a35A4569E4529A3CDfB74e38FD98631",
    "PRIME":   "0xfA980cEd6895AC314E7dE34Ef1bFAE90a5AdD21b",
    "VIRTUAL": "0x0b3e328455c4059eeb9e3f84b5543f74e24e7e1b",
}

# ABIs
QUOTER_ABI = '[{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct IQuoterV2.QuoteExactInputSingleParams","name":"params","type":"tuple"}],"name":"quoteExactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceX96After","type":"uint160"},{"internalType":"uint32","name":"initializedTicksCrossed","type":"uint32"},{"internalType":"uint256","name":"gasEstimate","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]'
FACTORY_ABI = '[{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"}],"name":"getPool","outputs":[{"internalType":"address","name":"pool","type":"address"}],"stateMutability":"view","type":"function"}]'

# تحميل العقد
try:
    with open("bot_contract_info.json", "r") as f:
        data = json.load(f)
        BOT_ADDRESS = data['address']
        BOT_ABI = data['abi']
    contract_sync = w3_sync.eth.contract(address=BOT_ADDRESS, abi=BOT_ABI)
    factory_sync = w3_sync.eth.contract(address=FACTORY, abi=FACTORY_ABI)
    acct = w3_sync.eth.account.from_key(PRIVATE_KEY)
    print(Fore.GREEN + f"✅ تم الاتصال (Base Max Power) | البوت: {BOT_ADDRESS}")
except Exception:
    print(Fore.RED + "❌ شغل deploy.py الأول!")
    exit()

# ==============================================================================
# 3. المنطق الذكي (High Stakes)
# ==============================================================================

async def get_quote(contract, token_in, token_out, amount_in, fee=500):
    try:
        data = await contract.functions.quoteExactInputSingle((
            token_in, token_out, int(amount_in), fee, 0
        )).call()
        return data[0]
    except Exception:
        return 0

async def execute_trade_fast(t_a, t_b, t_c, amount):
    try:
        # تعديل جوهري: بما أن المبالغ كبيرة، نطلب ربحاً "محترماً"
        # 10 دولار كحد أدنى صافي (يغطي أي رسوم ويترك مكسب جيد)
        MIN_PROFIT = 10 * (10**6) 

        fee = 500
        pool_address = factory_sync.functions.getPool(t_a, t_b, fee).call()
        if pool_address == "0x0000000000000000000000000000000000000000": return

        # بناء المعاملة
        tx_func = contract_sync.functions.checkAndShoot(
            pool_address, t_a, t_b, t_c, fee, fee, fee, int(amount), int(MIN_PROFIT)
        )

        # 1. محاكاة (Safety Check)
        tx_func.call({'from': acct.address})

        # 2. تنفيذ فوري
        # حساب المبلغ بالدولار للطباعة
        amount_readable = amount / 10**6
        print(Fore.MAGENTA + f"🚀 هجوم كاسح! المبلغ: ${amount_readable:,.0f} | متوقع ربح > $10")
        
        tx_params = tx_func.build_transaction({
            'from': acct.address,
            'gas': 800000,  # زيادة الغاز قليلاً للأمان مع المبالغ الكبيرة
            'gasPrice': int(w3_sync.eth.gas_price * 1.1), # أولوية أعلى
            'nonce': w3_sync.eth.get_transaction_count(acct.address),
        })

        signed = w3_sync.eth.account.sign_transaction(tx_params, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        print(Fore.GREEN + f"💰 تم الإرسال! Hash: {tx_hash.hex()}")

    except Exception:
        pass

async def scan_triangle(w3_async, quoter, token_a_name, token_b_name, token_c_name, amount_in):
    try:
        t_a, t_b, t_c = TOKENS[token_a_name], TOKENS[token_b_name], TOKENS[token_c_name]
        
        # الفحص السريع
        out_b = await get_quote(quoter, t_a, t_b, amount_in)
        if out_b == 0: return
        out_c = await get_quote(quoter, t_b, t_c, out_b)
        if out_c == 0: return
        final_out = await get_quote(quoter, t_c, t_a, out_c)
        
        profit = final_out - amount_in
        
        # طباعة للمتابعة فقط لو فيه أمل في الربح
        if profit > 0:
            print(f"\n{Fore.CYAN}⚡ {token_b_name} [${amount_in/10**6:,.0f}] | Profit: ${profit/10**6:.2f}")
            await execute_trade_fast(t_a, t_b, t_c, amount_in)
            
    except Exception:
        pass

async def main():
    print(Fore.YELLOW + "🔥 تشغيل وضع الوحش (Max Power Mode)...")
    
    w3_async = AsyncWeb3(AsyncHTTPProvider(RPC_URL))
    if not await w3_async.is_connected():
        print(Fore.RED + "❌ لا يوجد اتصال.")
        return

    quoter = w3_async.eth.contract(address=QUOTER_V2, abi=QUOTER_ABI)
    
    # =========================================================
    # 💰 الأرقام النهائية (الحدود القصوى الآمنة)
    # =========================================================
    
    # 1. الدبابات (USDC, WETH): 50,000 دولار
    # هذا الرقم سيجعلك تنافس الحيتان المتوسطة
    AMOUNT_TANK = 50000 * (10**6)
    
    # 2. القوات الخاصة (AERO, PRIME): 5,000 دولار
    # رفعناها من 1000 لـ 5000. دي أقصى حاجة ممكنة حالياً.
    # أكثر من كده = انتحار
    AMOUNT_SPECIAL = 5000 * (10**6) 

    print(Fore.CYAN + f"📊 التوزيع: $50,000 للكبار | $5,000 للصغار")
    print(Fore.GREEN + "🚀 المحرك يعمل بأقصى طاقة...")

    while True:
        await asyncio.gather(
            # --- الكتيبة الثقيلة ($50k) ---
            scan_triangle(w3_async, quoter, "USDC", "USDbC", "WETH", AMOUNT_TANK),
            scan_triangle(w3_async, quoter, "USDC", "WETH", "USDbC", AMOUNT_TANK),
            
            # --- الكتيبة الخفيفة ($5k) ---
            scan_triangle(w3_async, quoter, "USDC", "AERO", "WETH", AMOUNT_SPECIAL),
            scan_triangle(w3_async, quoter, "USDC", "VIRTUAL", "WETH", AMOUNT_SPECIAL),
            scan_triangle(w3_async, quoter, "USDC", "PRIME", "WETH", AMOUNT_SPECIAL),
        )
        
        # سرعة قصوى (بدون توقف تقريباً)
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Fore.RED + "\n🛑 توقف.")