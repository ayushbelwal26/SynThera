import requests
drugs = requests.get('http://localhost:8000/drugs').json()
labels = [f"{d['name']} ({d['id']})" for d in drugs]

print("Drugs 7279..7284:")
for i in range(7278, 7285):
    print(f"  {i}: {labels[i]}")

print("\nDrugs 3018..3024:")
for i in range(3017, 3024):
    print(f"  {i}: {labels[i]}")
