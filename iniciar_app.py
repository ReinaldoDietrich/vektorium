import os
import threading
import time
import webbrowser
import uvicorn


def abrir_navegador():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8842/")


if __name__ == "__main__":
    if not os.environ.get("ELECTRON"):
        threading.Thread(target=abrir_navegador, daemon=True).start()
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8842)
