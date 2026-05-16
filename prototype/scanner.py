import time
from web3 import Web3
import os
from dotenv import load_dotenv
from colorama import Fore, Style, init

# 1. تهيئة الإعدادات
init(autoreset=True)
load_dotenv()

# الاتصال بالشبكة
rpc_url = os.getenv("RPC_URL")
w3 = Web3(Web3.HTTPProvider(rpc_url))

def start_scanning():
    print(Fore.YELLOW + "📡 بدء تشغيل الرادار... ننتظر البلوكات الجديدة...")
    
    # حفظ آخر بلوك تم فحصه
    last_block_number = w3.eth.block_number

    while True:
        try:
            # جلب رقم البلوك الحالي من الشبكة
            current_block_number = w3.eth.block_number

            # إذا ظهر بلوك جديد (رقم أكبر من آخر واحد فحصناه)
            if current_block_number > last_block_number:
                
                # جلب تفاصيل البلوك (يأخذ بضعة ملي ثانية)
                block = w3.eth.get_block(current_block_number)
                tx_count = len(block['transactions'])
                
                # طباعة تقرير سريع
                print(f"{Fore.GREEN}📦 بلوك جديد: {current_block_number} | "
                      f"{Fore.CYAN}المعاملات: {tx_count} | "
                      f"{Fore.MAGENTA}الغاز المستهلك: {block['gasUsed']:,}")

                # تحديث آخر بلوك
                last_block_number = current_block_number
            
            # استراحة قصيرة جداً (0.5 ثانية) حتى لا نرهق المعالج
            time.sleep(0.5)

        except KeyboardInterrupt:
            print(Fore.RED + "\n🛑 تم إيقاف الرادار يدوياً.")
            break
        except Exception as e:
            print(Fore.RED + f"⚠️ خطأ في الاتصال: {e}")
            time.sleep(1)

if __name__ == "__main__":
    if w3.is_connected():
        start_scanning()
    else:
        print(Fore.RED + "❌ لا يوجد اتصال بالإنترنت أو الـ RPC")