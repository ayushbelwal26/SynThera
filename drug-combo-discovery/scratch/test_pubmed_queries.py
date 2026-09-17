import urllib.request
import json
import urllib.parse
import xml.etree.ElementTree as ET

def test_query(q):
    url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=' + urllib.parse.quote(q) + '&retmode=json&retmax=5'
    req = urllib.request.Request(url, headers={'User-Agent': 'SynThera/1.0'})
    try:
        data = json.loads(urllib.request.urlopen(req).read().decode())
        ids = data.get('esearchresult', {}).get('idlist', [])
        print(f"Query: {q} -> {len(ids)} hits: {ids[:3]}")
        return ids
    except Exception as e:
        print(f"Query: {q} -> Error: {e}")
        return []

ids1 = test_query('("Procarbazine" AND "Carmustine") AND (glioblastoma OR glioma OR brain)')
ids2 = test_query('"Procarbazine" AND "Carmustine"')
ids3 = test_query('"Procarbazine" AND glioblastoma')
ids4 = test_query('"Carmustine" AND glioblastoma')

# Fetch details for the combination ids
combo_ids = ids1 if ids1 else ids2
if combo_ids:
    fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={','.join(combo_ids[:3])}&retmode=xml"
    req = urllib.request.Request(fetch_url, headers={'User-Agent': 'SynThera/1.0'})
    root = ET.fromstring(urllib.request.urlopen(req).read().decode())
    for article in root.findall('.//PubmedArticle'):
        pmid = article.findtext('.//MedlineCitation/PMID')
        title = article.findtext('.//ArticleTitle')
        journal = article.findtext('.//Journal/Title')
        abstract_elements = article.findall('.//AbstractText')
        abstract = ' '.join([elem.text for elem in abstract_elements if elem.text])
        print(f"\nPMID: {pmid}")
        print(f"Title: {title}")
        print(f"Journal: {journal}")
        print(f"Abstract: {abstract[:150]}...")
