import requests

url = "http://localhost:5000/parse"
file_path = "data/contract_05.414801.pdf"  # Replace with your file path

# Open the file in binary mode
with open(file_path, "rb") as f:
    files = {"contract": (file_path, f)}
    response = requests.post(url, files=files)

print(response.status_code)
print(response.json())
