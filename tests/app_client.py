import requests

class AppClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def health(self):
        try:
            r = requests.get(self.base_url + "/health", timeout=10)
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def compute_quote(self, payload: dict):
        """
        Expected payload keys (example):
        {
          "quote_number": "12345",
          "customer": "EPF",
          "margin": 0.24 or "RESET",
          "spares": 0|10|50,
          "guard": "Standard|Tall|TallNet",
          "usl": "None|Front|Side|BadgerSide",
          "xfmr": "None|Canada|StepUp",
          "train": "EN|EN+ES"
        }
        """
        r = requests.post(self.base_url + "/api/quote/compute", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()

    def generate_outputs(self, payload: dict):
        """
        Same inputs plus output_dir; returns file paths for:
          - costing_xlsb
          - proposal_docx
          - proposal_pdf
        """
        r = requests.post(self.base_url + "/api/quote/generate", json=payload, timeout=180)
        r.raise_for_status()
        return r.json()
