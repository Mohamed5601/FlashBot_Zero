import asyncio
import os
import datetime
import warnings
from colorama import Fore, Style, init
from dotenv import load_dotenv

# ==============================================================================
# 1. إعدادات المكتبات (حل مشكلة جهازك)
# ==============================================================================
try:
    from web3 import AsyncWeb3, AsyncHTTPProvider
except ImportError:
    from web3.providers.async_rpc import AsyncHTTPProvider
    from web3 import AsyncWeb3

# تهيئة الألوان
init(autoreset=True)
warnings.filterwarnings("ignore")
load_dotenv()

# ==============================================================================
# 2. الاتصال والإعدادات
# ==============================================================================
RPC_URL = os.getenv("RPC_URL")
if not RPC_URL:
    print(Fore.RED + "❌ خطأ: RPC_URL غير موجود.")
    exit()

# الاتصال السريع
w3_async = AsyncWeb3(AsyncHTTPProvider(RPC_URL))

QUOTER_V2 = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"

# ✅ تم تحديث عنوان PRIME هنا
TOKENS = {
    "USDC":    "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "WETH":    "0x4200000000000000000000000000000000000006",
    "USDbC":   "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
    "AERO":    "0x940181a94a35A4569E4529A3CDfB74e38FD98631",
    "PRIME":   "0x1238534330608D72634211B385653c21c90637A2", 
    "VIRTUAL": "0x0b3e328455c4059eeb9e3f84b5543f74e24e7e1b",
}

QUOTER_ABI = '[{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct IQuoterV2.QuoteExactInputSingleParams","name":"params","type":"tuple"}],"name":"quoteExactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceX96After","type":"uint160"},{"internalType":"uint32","name":"initializedTicksCrossed","type":"uint32"},{"internalType":"uint256","name":"gasEstimate","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]'

# متغيرات للمراقبة
total_profit = 0.0

def log_trade(message):
    try:
        with open("sim_results.txt", "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass

async def get_quote(contract, token_in, token_out, amount_in, fee=500):
    try:
        data = await contract.functions.quoteExactInputSingle((
            token_in, token_out, int(amount_in), fee, 0
        )).call()
        return data[0]
    except Exception:
        return 0

async def scan_triangle(contract, t_a_name, t_b_name, t_c_name, amount_in):
    global total_profit
    
    try:
        t_a = TOKENS[t_a_name]
        t_b = TOKENS[t_b_name]
        t_c = TOKENS[t_c_name]
        
        # 1. الضلع الأول
        out_b = await get_quote(contract, t_a, t_b, amount_in)
        if out_b == 0: return

        # 2. الضلع الثاني
        out_c = await get_quote(contract, t_b, t_c, out_b)
        if out_c == 0: return

        # 3. الضلع الثالث
        final_out = await get_quote(contract, t_c, t_a, out_c)
        
        # الحساب
        profit = (final_out - amount_in) / 10**6
        net_profit = profit # عرض صافي الفرق بدون خصم غاز للمراقبة

        if net_profit > 0.5: # لو الربح أكبر من 0.5 دولار (صيدة حقيقية)
            total_profit += net_profit
            msg = f"\n🔥 صيدة! {t_b_name} | ربح: ${net_profit:.4f}"
            print(Fore.GREEN + msg)
            log_trade(msg)
        else:
            # عرض الخسارة الحالية باللون الرمادي (عشان تتطمن إنه شغال)
            # الـ end="\r" بتخلي السطر يتكتب فوق القديم
            print(f"{Fore.LIGHTBLACK_EX}.. فحص {t_b_name}: {net_profit:.4f}$     ", end="\r")

    except Exception:
        pass

async def main():
    print(Fore.CYAN + "==================================================")
    print(Fore.YELLOW + "🧪 بدء المحاكاة (الوضع الحي - Live Monitor)")
    print(Fore.WHITE + "ستظهر الأرقام تتغير أمامك الآن...")
    print(Fore.CYAN + "==================================================")

    if not await w3_async.is_connected():
        print(Fore.RED + "❌ لا يوجد اتصال بالإنترنت.")
        return

    quoter = w3_async.eth.contract(address=QUOTER_V2, abi=QUOTER_ABI)
    
    # 50 دولار للتجربة
    amount_in = 50 * (10**6) 

    # تنظيف السجل
    with open("sim_results.txt", "w", encoding="utf-8") as f:
        f.write(f"=== بدء الجلسة: {datetime.datetime.now()} ===\n")

    while True:
        # تشغيل الفحص بالتوازي (هنا كان الخطأ السابق وتم إصلاحه)
        await asyncio.gather(
            scan_triangle(quoter, "USDC", "AERO", "WETH", amount_in),
            scan_triangle(quoter, "USDC", "VIRTUAL", "WETH", amount_in),
            scan_triangle(quoter, "USDC", "PRIME", "WETH", amount_in),
            scan_triangle(quoter, "USDC", "USDbC", "WETH", amount_in),
        )
        
        # انتظار بسيط
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    try:
        if os.name == 'nt':
            os.system('chcp 65001 >nul')
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Fore.RED + "\n🛑 تم الإيقاف يدوياً.")