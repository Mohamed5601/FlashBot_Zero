from web3 import Web3

# ABI قياسي لجلب الرموز والكسور العشرية لأي عملة (ERC20)
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "payable": False, "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "payable": False, "stateMutability": "view", "type": "function"}
]

def get_token_details(w3, token_address):
    """
    تقوم هذه الدالة بجلب رمز العملة (Symbol) وعدد الكسور (Decimals).
    """
    try:
        # التأكد من صحة العنوان (Checksum)
        token_address = w3.to_checksum_address(token_address)
        
        # إنشاء اتصال بالعقد
        token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        symbol = token_contract.functions.symbol().call()
        decimals = token_contract.functions.decimals().call()
        
        return {'symbol': symbol, 'decimals': decimals}
    except Exception as e:
        # في حالة العملات الغريبة أو الخطأ، نرجع قيم افتراضية
        return {'symbol': 'UNKNOWN', 'decimals': 18}

def get_real_amount(w3, token_address, raw_amount):
    """
    تقوم هذه الدالة بتحويل الرقم الخام (Wei) إلى رقم مقروء بناءً على كسور العملة.
    """
    try:
        details = get_token_details(w3, token_address)
        decimals = details['decimals']
        
        # المعادلة: المبلغ الحقيقي = المبلغ الخام / (10 أس عدد الكسور)
        real_amount = raw_amount / (10 ** decimals)
        return real_amount
    except Exception:
        return 0