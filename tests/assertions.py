CURRENCY_TOL = 0.01
PCT_TOL = 0.0001

def almost_equal_currency(a, b, tol=CURRENCY_TOL):
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False

def assert_filename(actual_name, expected_exact):
    import os
    assert os.path.basename(actual_name) == expected_exact, f"Filename mismatch: {actual_name} != {expected_exact}"

def assert_bookmark_present(found, name):
    assert name in found, f"Missing bookmark: {name}"
