import os, json, csv
from pathlib import Path
from .excel_truth import _win32_available, compute_truth_with_com, compute_truth_fallback
from .app_client import AppClient
from .assertions import almost_equal_currency

HERE = Path(__file__).parent
CFG = json.loads(Path(HERE / "config.json").read_text()) if (HERE / "config.json").exists() else json.loads(Path(HERE / "config.example.json").read_text())

BASE_OUT = Path("./.artifacts/diffs")
BASE_OUT.mkdir(parents=True, exist_ok=True)

SCENARIOS = [
    {"name":"default_margin_24_spares0_guard_std_usl_none_xfmr_none_train_en", "margin":0.24, "spares":0,  "guard":"Standard", "usl":"None",       "xfmr":"None",  "train":"EN"},
    {"name":"margin_15_change_spares10_guard_tall_usl_front_xfmr_none_train_en", "margin":0.15, "spares":10, "guard":"Tall",     "usl":"Front",      "xfmr":"None",  "train":"EN"},
    {"name":"reset_margin_to_baseline_spares50_guard_tall_net_usl_side_xfmr_canada_train_enes", "margin":"RESET","spares":50,"guard":"TallNet",  "usl":"Side",       "xfmr":"Canada","train":"EN+ES"},
    {"name":"usl_side_badger", "margin":0.24, "spares":0, "guard":"Standard", "usl":"BadgerSide", "xfmr":"None", "train":"EN"},
    {"name":"xfmr_step_up",    "margin":0.24, "spares":0, "guard":"Standard", "usl":"None",       "xfmr":"StepUp","train":"EN"},
    {"name":"train_en_es",     "margin":0.24, "spares":0, "guard":"Standard", "usl":"None",       "xfmr":"None", "train":"EN+ES"},
    {"name":"spares_10",       "margin":0.24, "spares":10,"guard":"Standard", "usl":"None",       "xfmr":"None", "train":"EN"},
    {"name":"spares_50",       "margin":0.24, "spares":50,"guard":"Standard", "usl":"None",       "xfmr":"None", "train":"EN"},
]

def main():
    client = AppClient(CFG["app"]["base_url"])
    health = client.health()
    print("[health]", health)

    excel_truth_fn = compute_truth_with_com if _win32_available() and CFG["excel"].get("use_com_automation", True) else compute_truth_fallback

    report_rows = []

    for sc in SCENARIOS:
        truth = excel_truth_fn(CFG["excel"]["rds_sales_tool"], CFG["excel"]["costing_workbook"], sc)

        payload = {
            "quote_number": "Q12345",
            "customer": "EPF",
            "margin": sc["margin"],
            "spares": sc["spares"],
            "guard": sc["guard"],
            "usl": sc["usl"],
            "xfmr": sc["xfmr"],
            "train": sc["train"]
        }

        try:
            app_out = client.compute_quote(payload)
        except Exception as e:
            app_out = {"error": str(e)}

        fields = [
            ("base_cost", "base_cost"),
            ("spares.J38", ("spares","J38")),
            ("guard.J32",  ("guard","J32")),
            ("infeed.J18", ("infeed","J18")),
            ("misc.J45",   ("misc","J45")),
            ("margin",     "margin"),
        ]

        diffs = []
        for label, key in fields:
            tval = None
            aval = None
            if isinstance(key, tuple):
                tval = truth.get(key[0],{}).get(key[1])
                aval = app_out.get(key[0],{}).get(key[1]) if isinstance(app_out, dict) else None
            else:
                tval = truth.get(key)
                aval = app_out.get(key) if isinstance(app_out, dict) else None

            ok = (tval == aval) or (
                isinstance(tval,(int,float)) and isinstance(aval,(int,float)) and almost_equal_currency(tval, aval)
            )
            diffs.append({"field": label, "expected": tval, "actual": aval, "pass": ok})

        out_csv = BASE_OUT / f"{sc['name']}.csv"
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["field","expected","actual","pass"])
            w.writeheader()
            w.writerows(diffs)

        pass_rate = sum(1 for d in diffs if d["pass"]) / len(diffs) if diffs else 0.0
        report_rows.append({"scenario": sc["name"], "pass": f"{pass_rate*100:.0f}%"})

    (BASE_OUT / "summary.json").write_text(json.dumps(report_rows, indent=2), encoding="utf-8")
    print("Done. Results at", BASE_OUT)

if __name__ == "__main__":
    main()
