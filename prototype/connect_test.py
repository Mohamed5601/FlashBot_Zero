import sys
import web3
import aiohttp

print("--- تقرير الفحص الجنائي ---")
print(f"1. Python Version: {sys.version}")
print(f"2. Web3 Version:   {web3.__version__}")
print(f"3. aiohttp Version: {aiohttp.__version__}")
print(f"4. Web3 File Path: {web3.__file__}")

# محاولة استدعاء الجزء المفقود يدوياً
try:
    from web3 import AsyncHTTPProvider
    print("✅ الحالة: AsyncHTTPProvider موجود ومتاح!")
except ImportError:
    print("❌ الحالة: AsyncHTTPProvider غير موجود (المشكلة هنا).")
    
    # فحص عميق: هل هو موجود داخل providers؟
    try:
        from web3.providers import AsyncHTTPProvider
        print("   ⚠️ تنبيه: هو موجود داخل providers لكن ليس في القائمة الرئيسية.")
    except ImportError:
        print("   ❌ تأكيد: هو غير موجود نهائياً في ملفات المكتبة.")