# Drop this into your backend (e.g., backend/app/core/mapping_constants.py)

SUMMARY_FORCE_ONES = ["H18","H19","H20","H32","H33","H38","H39","H40","H45","H46","H47"]

WRITE_TO_SUMMARY = {
    # Summary cell -> RDS source (sheet, cell)
    "H38": ("Sheet1", "B4"),
    "H39": ("Sheet1", "B5"),
    "H40": ("Sheet1", "B6"),
    "H32": ("Sheet3", "C6"),
    "H33": ("Sheet3", "C7"),
    "H18": ("Sheet3", "C8"),
    "H19": ("Sheet3", "C9"),
    "H20": ("Sheet3", "C10"),
    "H45": ("Sheet3", "C11"),
    "H46": ("Sheet3", "C12"),
    "H47": ("Sheet3", "C13"),
    "M4":  ("Sheet1", "B12"),
}

READ_BACK_TO_RDS = {
    # RDS Sheet3 targets from Summary!Jxx
    ("Sheet3","B3"): "J38",
    ("Sheet3","B4"): "J39",
    ("Sheet3","B5"): "J40",
    ("Sheet3","B6"): "J32",
    ("Sheet3","B7"): "J33",
    ("Sheet3","B8"): "J18",
    ("Sheet3","B9"): "J19",
    ("Sheet3","B10"): "J20",
    ("Sheet3","B11"): "J45",
    ("Sheet3","B12"): "J46",
    ("Sheet3","B13"): "J47",
    # Margin echo
    ("Sheet1","B12"): "M4",
}

BASE_SUMMARY_TERMS = ["J4","J5","J6","J7","J8","J9","J10","J14","J17","J24","J31"]
