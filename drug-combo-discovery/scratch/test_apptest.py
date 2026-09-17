import sys
from streamlit.testing.v1 import AppTest

print("Initializing AppTest for app/demo.py...")
at = AppTest.from_file("../app/demo.py", default_timeout=30)
at.run()

print(f"Initial run completed. Total selectboxes: {len(at.selectbox)}, Total sidebar buttons: {len(at.sidebar.button)}")
print(f"Initial Drug A: {at.selectbox[0].value}")
print(f"Initial Drug B: {at.selectbox[1].value}")
print(f"Initial Cell Line: {at.selectbox[2].value}")

print("\n--- Clicking Button 0 (Synergy) ---")
at.sidebar.button[0].click().run()
print(f"After Button 0 click -> Drug A: {at.selectbox[0].value}")
print(f"After Button 0 click -> Drug B: {at.selectbox[1].value}")
print(f"After Button 0 click -> Cell Line: {at.selectbox[2].value}")

print("\n--- Clicking Button 1 (Antagonism) ---")
at.sidebar.button[1].click().run()
print(f"After Button 1 click -> Drug A: {at.selectbox[0].value}")
print(f"After Button 1 click -> Drug B: {at.selectbox[1].value}")
print(f"After Button 1 click -> Cell Line: {at.selectbox[2].value}")

print("\n--- Clicking Button 2 (Additive) ---")
at.sidebar.button[2].click().run()
print(f"After Button 2 click -> Drug A: {at.selectbox[0].value}")
print(f"After Button 2 click -> Drug B: {at.selectbox[1].value}")
print(f"After Button 2 click -> Cell Line: {at.selectbox[2].value}")
