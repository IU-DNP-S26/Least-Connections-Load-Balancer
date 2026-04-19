import time
from datetime import datetime
import requests

BASE_URL = "http://localhost:8080/stats"
REFRESH_SECONDS = 1
TIMEOUT_SECONDS = 3

def clear_screen() -> None:
    print("\033[2J\033[H", end="")


def print_header(proxy_timestamp: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("Least Connections Monitor")
    print(f"Local time   : {now}")
    print(f"Proxy time   : {proxy_timestamp}")
    print(f"Refresh every: {REFRESH_SECONDS}s")
    print("-" * 56)


def print_table(servers: list[dict]) -> None:
    if not servers:
        print("No backend servers in /stats response.")
        return

    name_w = max(len("SERVER"), *(len(str(s.get("name", "-"))) for s in servers))
    status_w = len("STATUS")
    req_w = len("REQS")
    check_w = max(len("LAST CHECK"), *(len(str(s.get("last_check", "-"))) for s in servers))

    header = (
        f"{'SERVER':<{name_w}} | "
        f"{'STATUS':<{status_w}} | "
        f"{'REQS':>{req_w}} | "
        f"{'LAST CHECK':<{check_w}}"
    )
    print(header)
    print("-" * len(header))

    for server in servers:
        name = str(server.get("name", "-"))
        alive = bool(server.get("is_alive", False))
        status = "UP" if alive else "DOWN"
        serving_requests = server.get("serving_requests", 0)
        last_check = str(server.get("last_check", "-"))

        print(
            f"{name:<{name_w}} | "
            f"{status:<{status_w}} | "
            f"{serving_requests:>{req_w}} | "
            f"{last_check:<{check_w}}"
        )


def render_error(error: Exception) -> None:
    clear_screen()
    print_header(proxy_timestamp="-")
    print(f"Could not fetch /stats: {error}")
    print("Make sure reverse proxy is running on http://localhost:8080")


def main() -> None:
    while True:
        try:
            response = requests.get(BASE_URL, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()

            servers = data.get("servers", [])
            proxy_timestamp = str(data.get("timestamp", "-"))

            clear_screen()
            print_header(proxy_timestamp=proxy_timestamp)
            print_table(servers)
        except (requests.RequestException, ValueError) as e:
            render_error(e)

        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
