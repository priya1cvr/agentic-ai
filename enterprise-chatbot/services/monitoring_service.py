import psutil


def get_cpu():

    return psutil.cpu_percent(
        interval=1
    )


def get_memory():

    return psutil.virtual_memory().percent


def get_disk():

    return psutil.disk_usage(
        "/"
    ).percent


def get_ollama_process():

    for process in psutil.process_iter():

        try:

            if "ollama" in process.name().lower():

                return {
                    "pid": process.pid,
                    "memory_mb": round(
                        process.memory_info().rss
                        / 1024
                        / 1024,
                        2
                    ),
                    "cpu": process.cpu_percent()
                }

        except Exception:

            pass

    return None
