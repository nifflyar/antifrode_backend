import urllib.request
import json

boundary = '---011000010111000001101001'
file_bytes = open('Выгрузка 22.xlsx', 'rb').read()
data = (
    b'--' + boundary.encode() + b'\r\n'
    b'Content-Disposition: form-data; name="file"; filename="file.xlsx"\r\n'
    b'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n'
    + file_bytes +
    b'\r\n--' + boundary.encode() + b'--\r\n'
)

req = urllib.request.Request(
    'http://localhost:8000/uploads/excel',
    data=data,
    headers={
        'Authorization': 'Bearer 123',
        'Content-Type': 'multipart/form-data; boundary=' + boundary
    }
)
res = urllib.request.urlopen(req)
print(res.read().decode())
