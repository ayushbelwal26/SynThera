import sys
import os
from streamlit.testing.v1 import AppTest

def test_sidebar_demo_buttons():
    print("==================================================================")
    print("  RUNNING OFFICIAL STREAMLIT AppTest FOR app/demo.py")
    print("==================================================================")

    # Resolve path to app/demo.py relative to workspace root
    script_path = os.path.join(os.path.dirname(__file__), "..", "app", "demo.py")
    script_path = os.path.abspath(script_path)
    print(f"[AppTest] Target script: {script_path}")

    # Ensure backend is healthy before running AppTest (in case uvicorn is reloading)
    import time
    import requests
    backend_url = "http://127.0.0.1:8000/health"
    print(f"[AppTest] Verifying backend availability at {backend_url}...")
    ready = False
    for _ in range(40):
        try:
            r = requests.get(backend_url, timeout=2)
            if r.status_code == 200:
                ready = True
                break
        except Exception:
            pass
        time.sleep(1)
    assert ready, f"FastAPI backend at {backend_url} was not ready within timeout."
    print(f"[AppTest] Backend is ready. Initializing AppTest...")

    at = AppTest.from_file(script_path, default_timeout=35)
    at.run(timeout=35)
    assert not at.exception, f"Initial run raised exception: {at.exception}"

    test_cases = [
        {
            "button_index": 0,
            "button_name": "Synergy: Temozolomide + Cyclophosphamide (T98G)",
            "expected_drug_a": "Temozolomide (DB00853)",
            "expected_drug_b": "Cyclophosphamide (DB00531)",
            "expected_cell_line": "T98G",
        },
        {
            "button_index": 1,
            "button_name": "Antagonism: Temozolomide + Docetaxel (OVCAR-5)",
            "expected_drug_a": "Temozolomide (DB00853)",
            "expected_drug_b": "Docetaxel (DB01248)",
            "expected_cell_line": "OVCAR-5",
        },
        {
            "button_index": 2,
            "button_name": "Additive: Docetaxel + Topotecan (A498)",
            "expected_drug_a": "Docetaxel (DB01248)",
            "expected_drug_b": "Topotecan (DB01030)",
            "expected_cell_line": "A498",
        },
    ]

    all_passed = True

    for tc in test_cases:
        btn_idx = tc["button_index"]
        btn_name = tc["button_name"]
        print(f"\n>>> [TEST] Clicking Button {btn_idx}: '{btn_name}'")
        
        # Click button and run with timeout=35
        at.sidebar.button[btn_idx].click().run(timeout=35)
        assert not at.exception, f"Run after clicking '{btn_name}' raised exception: {at.exception}"

        # Get actual selectbox widget values
        actual_drug_a = at.selectbox[0].value
        actual_drug_b = at.selectbox[1].value
        actual_cell_line = at.selectbox[2].value

        exp_drug_a = tc["expected_drug_a"]
        exp_drug_b = tc["expected_drug_b"]
        exp_cell_line = tc["expected_cell_line"]

        match_a = (actual_drug_a == exp_drug_a)
        match_b = (actual_drug_b == exp_drug_b)
        match_cl = (actual_cell_line == exp_cell_line)

        print(f"    Drug A:    Actual='{actual_drug_a}' | Expected='{exp_drug_a}' | MATCH={match_a}")
        print(f"    Drug B:    Actual='{actual_drug_b}' | Expected='{exp_drug_b}' | MATCH={match_b}")
        print(f"    Cell Line: Actual='{actual_cell_line}' | Expected='{exp_cell_line}' | MATCH={match_cl}")

        if not (match_a and match_b and match_cl):
            print(f"    [FAIL] Mismatch detected on '{btn_name}'!")
            all_passed = False
        else:
            print(f"    [PASS] '{btn_name}' successfully set all dropdowns to exact locked values.")

    print("\n==================================================================")
    if all_passed:
        print("  RESULT: ALL 3 DEMO BUTTON TESTS PASSED (100% MATCH)")
    else:
        print("  RESULT: ONE OR MORE BUTTON TESTS FAILED")
    print("==================================================================")

    assert all_passed, "One or more demo button tests failed to set exact locked values."

if __name__ == "__main__":
    test_sidebar_demo_buttons()
