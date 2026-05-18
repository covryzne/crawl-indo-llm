import requests

api_url = "https://e-regulasi.brin.go.id/api/v1/file/download/a19e0487-29be-4824-8221-ea5eced379c8"

# Bawa KTP hasil nyontek dari F12
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Referer": "https://jdih.brin.go.id/",
    "Origin": "https://jdih.brin.go.id",
    # MASUKIN TOKEN ATAU COOKIE LU DI SINI:
    "Authorization": "Bearer ljYjBFdyfWJe66hhZZwSpaswn4lWDyPHpUcOOhfYzJxh1ZLo6LzYziLkSe5OEFTeo6IYXyfsV5mODsSkG4v94L77roYL0xvOkCI0xFpOJws2Jn5RWDxeHzNDhN75hXRl",
    # Atau kalau pakainya Cookie:
    # "Cookie": "MASUKIN_COOKIE_DARI_F12_DISINI"
}

print(f"Mencoba nyogok satpam BRIN: {api_url}")
response = requests.get(api_url, headers=headers)

if response.status_code == 200:
    with open("Dokumen_BRIN_Hacked.pdf", "wb") as f:
        f.write(response.content)
    print("MANTAP! Satpam berhasil disogok, PDF ke-download! 🔥")
else:
    print(f"Yah ketahuan lagi: {response.status_code} - {response.text}")
