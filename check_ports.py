#!/usr/bin/env python3
"""
Проверка занятости портов
"""

import socket

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("localhost", port))
        sock.close()
        return True  # Порт свободен
    except OSError:
        return False  # Порт занят

print("🔍 Проверка портов 5000-5010:")
for port in range(5000, 5011):
    if check_port(port):
        print(f"   ✅ Порт {port}: СВОБОДЕН")
    else:
        print(f"   ❌ Порт {port}: ЗАНЯТ")