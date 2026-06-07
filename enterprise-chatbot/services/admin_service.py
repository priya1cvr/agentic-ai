import subprocess
import os


def stop_ollama():

    os.system("pkill ollama")


def start_ollama():

    subprocess.Popen(
        ["ollama", "serve"]
    )


def restart_ollama():

    stop_ollama()

    start_ollama()
