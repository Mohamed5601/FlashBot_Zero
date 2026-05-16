import time
from web3 import Web3
import pandas as pd
from colorama import Fore, Style, init
from decimal import Decimal

init(autoreset=True)

# ==========================================
# ⚙️ إعدادات الصيد
# ==========================================

# RPC مجاني (يدعم 1000 بلوك في الطلب الواحد)
RPC_URL = "https://eth.llamarpc.com" 
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# 🎯 العملة الهدف (PEPE كمثال - غيرها للعملة التي تريد صيد حيتانها)
TARGET_TOKEN = web3.to_checksum_address("0x6982508145454Ce325dDbE47a25d4ec3d2311933") 

# 🏊‍♂️ عنوان الـ Pool (لمعرفة البيع والشراء)
POOL_ADDRESS = web3.to_checksum_address("0xA43fe16908251ee70EF74718545e4FE6C5cCEc9f") 

# سنفحص 5000 بلوك (حوالي 15 ساعة) لزيادة فرصة العثور على محترفين
BLOCKS_TO_SCAN = 5000 
CHUNK_SIZE = 800 # سنطلب 800 بلوك في المرة الواحدة لتجنب الخطأ

# ==========================================
# 🛠️ الدوال المساعدة
# ==========================================

ERC20_ABI = '[{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"}, {"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}]'

def get_events_in_batches(contract, start_block, end_block):
    """دالة لجلب الأحداث على دفعات لتجنب حظر الـ RPC"""
    all_events = []
    current_start = start_block
    
    print(f"{Fore.YELLOW}📡 جاري سحب البيانات بنظام الدفعات (Chunks)...{Style.RESET_ALL}")
    
    while current_start < end_block:
        current_end = min(current_start + CHUNK_SIZE, end_block)
        
        try:
            print(f"   ⏳ فحص من {current_start} إلى {current_end}...", end="\r")
            batch = contract.events.Transfer.get_logs(fromBlock=current_start, toBlock=current_end)
            all_events.extend(batch)
        except Exception as e:
            print(f"\n{Fore.RED}⚠️ خطأ في الدفعة {current_start}-{current_end}: {e}{Style.RESET_ALL}")
            # يمكن الانتظار قليلاً وإعادة المحاولة إذا لزم الأمر
            time.sleep(1) 
        
        current_start = current_end + 1
    
    print(f"\n{Fore.GREEN}✅ تم اكتمال السحب! إجمالي العمليات: {len(all_events)}{Style.RESET_ALL}")
    return all_events

def find_best_trader():
    if not web3.is_connected():
        print(f"{Fore.RED}❌ لا يوجد اتصال بالإنترنت.{Style.RESET_ALL}")
        return

    try:
        token_contract = web3.eth.contract(address=TARGET_TOKEN, abi=ERC20_ABI)
        try:
            DECIMALS = token_contract.functions.decimals().call()
        except:
            DECIMALS = 18

        current_block = web3.eth.block_number
        start_block = current_block - BLOCKS_TO_SCAN
        
        print(f"{Fore.CYAN}🔎 بدأ البحث عن 'الحوت الذكي' في آخر {BLOCKS_TO_SCAN} بلوك...{Style.RESET_ALL}")
        
        # استخدام دالة الدفعات الجديدة بدلاً من الطلب المباشر
        events = get_events_in_batches(token_contract, start_block, current_block)

        wallets = {}

        # تحليل السلوك
        print(f"{Fore.MAGENTA}🧠 جاري تحليل ذكاء المحافظ...{Style.RESET_ALL}")
        
        for event in events:
            args = event['args']
            sender = args['from']
            receiver = args['to']
            amount = Decimal(args['value']) / Decimal(10**DECIMALS)
            
            if sender == "0x0000000000000000000000000000000000000000": continue

            # شراء
            if sender == POOL_ADDRESS:
                w = receiver
                if w not in wallets: wallets[w] = {'bought': 0, 'sold': 0, 'tx_count': 0}
                wallets[w]['bought'] += amount
                wallets[w]['tx_count'] += 1
            
            # بيع
            elif receiver == POOL_ADDRESS:
                w = sender
                if w in wallets:
                    wallets[w]['sold'] += amount
                    wallets[w]['tx_count'] += 1

        # فلترة واستخراج "الأفضل"
        candidates = []
        
        for w, data in wallets.items():
            if data['bought'] < 100: continue # تجاهل الكميات الصغيرة

            remaining = data['bought'] - data['sold']
            
            if data['bought'] > 0:
                # حساب النسبة المئوية للبيع
                sold_ratio = (data['sold'] / data['bought']) * 100
            else:
                continue

            # المعايير الذهبية:
            # 1. ليس بوت (عدد العمليات قليل نسبياً)
            # 2. باع جزءاً ليؤمن الربح (بين 10% و 90%)
            # 3. لا يزال يحتفظ بجزء (Moonbag)
            
            is_bot = data['tx_count'] > 60
            
            score = 0
            label = "Normal"

            if not is_bot:
                if 20 <= sold_ratio <= 80: 
                    label = "💎 SMART TRADER"
                    score = 100 # أعلى تقييم: جنى أرباحاً وما زال في السوق
                elif sold_ratio < 20 and sold_ratio > 0:
                    label = "🐂 BULLISH HOLDER"
                    score = 70 

                if score > 0:
                    candidates.append({
                        "Address": w,
                        "Type": label,
                        "Bought": data['bought'],
                        "Sold %": f"{sold_ratio:.1f}%",
                        "Tx": data['tx_count'],
                        "Score": score
                    })

        # فرز النتائج
        df = pd.DataFrame(candidates)
        
        if not df.empty:
            # نرتب حسب السكور ثم حجم الشراء
            best_wallets = df.sort_values(by=['Score', 'Bought'], ascending=False).head(3)
            
            top_wallet = best_wallets.iloc[0]
            
            print("\n" + "="*60)
            print(f"{Fore.YELLOW}🏆 الفائز: أفضل محفظة للنسخ في هذه الفترة{Style.RESET_ALL}")
            print("="*60)
            print(f"👤 العنوان:  {Fore.GREEN}{top_wallet['Address']}{Style.RESET_ALL}")
            print(f"📊 التصنيف:  {top_wallet['Type']}")
            print(f"💰 اشترى بـ:  {top_wallet['Bought']:,.2f} عملة")
            print(f"📉 باع نسبة:  {top_wallet['Sold %']} (جني أرباح ذكي)")
            print(f"🔢 العمليات:  {top_wallet['Tx']}")
            print("-" * 60)
            
            print(f"\n🥈 المرشح الثاني: {best_wallets.iloc[1]['Address']} (Score: {best_wallets.iloc[1]['Score']})" if len(best_wallets) > 1 else "")
            
        else:
            print(f"\n{Fore.RED}❌ لم يتم العثور على محافظ تطابق معايير 'المتداول الذكي' تماماً.{Style.RESET_ALL}")
            print("قد يكون السوق راكداً أو العملة جديدة جداً.")

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    find_best_trader()