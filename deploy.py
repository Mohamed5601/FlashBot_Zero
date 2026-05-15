import os
import json
from web3 import Web3
from dotenv import load_dotenv
from solcx import compile_standard, install_solc
from colorama import Fore, Style, init

# تهيئة الألوان
init(autoreset=True)
load_dotenv()

def deploy_contract():
    print(Fore.YELLOW + "⚙️  جاري تجهيز بيئة النشر...")

    # 1. التحقق من المتغيرات البيئية
    # للنشر نفضل استخدام HTTP RPC لأنه أكثر استقراراً للمعاملات الفردية من WebSocket
    rpc_url = os.getenv("RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")

    if not rpc_url or not private_key:
        print(Fore.RED + "❌ خطأ: تأكد من وجود RPC_URL و PRIVATE_KEY في ملف .env")
        return

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print(Fore.RED + "❌ فشل الاتصال بمزود الخدمة (RPC).")
        return

    account = w3.eth.account.from_key(private_key)
    my_address = account.address
    
    balance = w3.from_wei(w3.eth.get_balance(my_address), 'ether')
    print(Fore.CYAN + f"👤 الحساب المستخدم: {my_address}")
    print(Fore.CYAN + f"💰 الرصيد الحالي: {balance:.4f} ETH")

    if float(balance) < 0.001:
        print(Fore.RED + "⚠️ تحذير: رصيدك قد لا يكفي لدفع رسوم الغاز للنشر!")

    # 2. ترجمة كود Solidity
    print(Fore.YELLOW + "🔨 جاري تثبيت المترجم وترجمة العقد (Solidity Compile)...")
    
    # تثبيت النسخة المطلوبة تلقائياً
    install_solc('0.8.20')

    with open("ArbFlashBot.sol", "r", encoding="utf-8") as file:
        flash_loan_file = file.read()

    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {"ArbFlashBot.sol": {"content": flash_loan_file}},
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                    }
                }
            },
        },
        solc_version="0.8.20",
    )

    # استخراج البيانات الضرورية
    bytecode = compiled_sol["contracts"]["ArbFlashBot.sol"]["ArbFlashBot"]["evm"]["bytecode"]["object"]
    abi = json.loads(compiled_sol["contracts"]["ArbFlashBot.sol"]["ArbFlashBot"]["metadata"])["output"]["abi"]

    # 3. بناء معاملة النشر
    print(Fore.YELLOW + "🚀 جاري إرسال العقد إلى البلوك تشين...")
    
    ArbFlashBot = w3.eth.contract(abi=abi, bytecode=bytecode)

    # الحصول على رقم المعاملة (Nonce)
    nonce = w3.eth.get_transaction_count(my_address)

    # بناء المعاملة
    # لا نحدد الغاز يدوياً، نترك w3 يقدره تلقائياً لضمان الدقة
    transaction = ArbFlashBot.constructor().build_transaction({
        "chainId": w3.eth.chain_id,
        "from": my_address,
        "nonce": nonce,
        "gasPrice": w3.eth.gas_price  # استخدام سعر الغاز الحالي للشبكة
    })

    # 4. التوقيع والإرسال
    signed_tx = w3.eth.account.sign_transaction(transaction, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print(Fore.WHITE + f"⏳ تم الإرسال! الهاش: {tx_hash.hex()}")
    print("ننتظر التأكيد...")

    # انتظار التأكيد (Receipt)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # 5. النجاح والحفظ
    contract_address = tx_receipt.contractAddress
    print(Fore.GREEN + f"\n✅ تم النشر بنجاح!")
    print(Fore.GREEN + f"📍 عنوان العقد الجديد: {contract_address}")
    
    # حفظ المعلومات لاستخدامها لاحقاً
    data_to_save = {
        "address": contract_address,
        "abi": abi
    }
    
    with open("bot_contract_info.json", "w") as outfile:
        json.dump(data_to_save, outfile)
        
    print(Fore.CYAN + "💾 تم حفظ العنوان والـ ABI في ملف 'bot_contract_info.json'")

if __name__ == "__main__":
    try:
        deploy_contract()
    except Exception as e:
        print(Fore.RED + f"حدث خطأ غير متوقع: {e}")