import requests
import openpyxl
from datetime import datetime
import io
import time

API_URL = "http://localhost:8000"
EMAIL = "admin@example.com"
PASSWORD = "AdminPassword123"

def create_broken_excel(filename, rows_count=1000):
    wb = openpyxl.Workbook()
    ws = wb.active
    # Headers
    headers = ["Операция", "Дата операции", "Цена", "Ф.И.О. пассажира", "Номер телефона, ИИН", " документа"]
    ws.append(headers)
    
    for i in range(rows_count):
        # 10th row is broken (no op_type)
        if i == 10:
            ws.append([None, "2026-04-15 12:00:00", 100.0, "BROKEN_FIO", "123", "DOC123"])
            continue
        # 20th row is broken (bad date)
        if i == 20:
            ws.append(["sale", "NOT_A_DATE", 100.0, "BAD_DATE_FIO", "123", "DOC123"])
            continue
            
        ws.append(["sale", "2026-04-15 12:00:00", 100.0 + i, f"PASSENGER_{i}", f"990101000{i:03d}", f"DOC{i}"])
    
    wb.save(filename)
    print(f"Created {filename} with {rows_count} rows (2 intentional errors)")

def test_upload():
    session = requests.Session()
    # 1. Login
    resp = session.post(f"{API_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        return
        
    print("Login OK")
    
    # 2. Upload
    filename = "test_large_broken.xlsx"
    create_broken_excel(filename)
    
    with open(filename, "rb") as f:
        resp = session.post(f"{API_URL}/uploads/excel", files={"file": f})
    
    print("Upload response:", resp.json())
    upload_id = resp.json()["id"]
    
    # 3. Wait and check
    print("Waiting for processing...")
    for _ in range(15):
        time.sleep(2)
        status_resp = session.get(f"{API_URL}/uploads/{upload_id}")
        data = status_resp.json()
        status = data["status"]
        print(f"Status: {status}")
        if status in ("done", "failed"):
            print("Final upload data:", data)
            break

if __name__ == "__main__":
    test_upload()
