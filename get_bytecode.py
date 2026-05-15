from solcx import compile_standard, install_solc
import json
from colorama import init, Fore

init(autoreset=True)

def get_bytecode_only():
    print(Fore.YELLOW + "🔨 جاري استخراج الـ Bytecode...")
    
    # نفس الإصدار الذي استخدمته في النشر
    install_solc('0.8.20')

    with open("ArbFlashBot.sol", "r", encoding="utf-8") as file:
        flash_loan_file = file.read()

    # عملية الترجمة (Compile) فقط
    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {"ArbFlashBot.sol": {"content": flash_loan_file}},
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["evm.bytecode"]
                    }
                }
            },
        },
        solc_version="0.8.20",
    )

    # استخراج البايت كود
    bytecode = compiled_sol["contracts"]["ArbFlashBot.sol"]["ArbFlashBot"]["evm"]["bytecode"]["object"]
    
    print(Fore.GREEN + "\n✅ تم الاستخراج بنجاح!")
    print(Fore.CYAN + "انسخ الكود التالي وضعه في ملف .env أمام المتغير BOT_BYTECODE")
    print(Fore.WHITE + "="*50)
    print(bytecode) # <--- هذا هو ما تريده
    print(Fore.WHITE + "="*50)

if __name__ == "__main__":
    get_bytecode_only()