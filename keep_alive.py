import requests
import threading
import time

def ping_self():
    """Периодически пингует сам себя"""
    url = "https://splitsellsbot.onrender.com"
    while True:
        try:
            requests.get(url, timeout=10)
            print("✅ Пинг отправлен")
        except:
            print("⚠️ Пинг не прошел")
        time.sleep(240)  # Каждые 4 минуты

# Запускаем в отдельном потоке
ping_thread = threading.Thread(target=ping_self)
ping_thread.daemon = True
ping_thread.start()