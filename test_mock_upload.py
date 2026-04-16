import urllib.request
import json
import urllib.error

# login to get cookie
data = json.dumps({"email": "admin@example.com", "password": "AdminPassword123"}).encode()
req = urllib.request.Request('http://localhost:8000/auth/login', data=data, headers={"Content-Type": "application/json"})
try:
    res = urllib.request.urlopen(req)
    headers = res.info()
    cookies = []
    for header in headers.get_all('Set-Cookie', []):
        cookies.append(header.split(';')[0])
    cookie_str = '; '.join(cookies)
    print("Login OK")
except urllib.error.HTTPError as e:
    print("Login error:", e.read().decode())
    exit(1)

# upload
boundary = '---011000010111000001101001'
file_bytes = open('/app/test_mock.xlsx', 'rb').read()
data = (
    b'--' + boundary.encode() + b'\r\n'
    b'Content-Disposition: form-data; name="file"; filename="test_mock.xlsx"\r\n'
    b'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n'
    + file_bytes +
    b'\r\n--' + boundary.encode() + b'--\r\n'
)

req = urllib.request.Request(
    'http://localhost:8000/uploads/excel',
    data=data,
    headers={
        'Cookie': cookie_str,
        'Content-Type': 'multipart/form-data; boundary=' + boundary
    }
)
try:
    res = urllib.request.urlopen(req)
    print("Upload result:", res.read().decode())
except Exception as e:
    print("Upload error:", e.read().decode())
