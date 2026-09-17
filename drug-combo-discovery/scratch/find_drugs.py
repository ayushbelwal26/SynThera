import requests
drugs = requests.get('http://localhost:8000/drugs').json()
labels = [f"{d['name']} ({d['id']})" for d in drugs]

for name in ['Temefos', 'Cycloleucine', 'Temozolomide', 'Cyclophosphamide', 'Docetaxel', 'Topotecan']:
    matches = [(i, l) for i, l in enumerate(labels) if name.lower() in l.lower()]
    print(f'Matches for {name}:', matches)
