import argparse
import sys
from typing import Optional, Dict

import joblib
import pandas as pd


LITE_FEATURES = [
    "TRIP_DAYS",
    "GENDER",
    "AGE_GRP",
    "ACTIVITY_TYPE_CD",
]


def load_model(path: str):
    try:
        return joblib.load(path)
    except Exception as e:
        print(f"[ERROR] Failed to load model from {path}: {e}", file=sys.stderr)
        sys.exit(1)


ACT_LABEL_TO_CODE: Dict[str, str] = {
    # Canonical Korean labels -> ACT cd_b code (as string)
    "취식": "1",
    "쇼핑": "2",
    "쇼핑/구매": "2",
    "체험": "3",
    "체험 활동": "3",
    "입장": "3",
    "관람": "3",
    "산책": "4",
    "단순 구경": "4",
    "걷기": "4",
    "휴식": "5",
    "기타": "6",
    "이동": "7",  # 환승/경유 의미
    "환승": "7",
    "경유": "7",
    "없음": "99",
}


def _normalize_gender(value: Optional[str]) -> int:
    if value is None:
        v = input("GENDER (M/F 또는 남/여): ").strip()
    else:
        v = str(value).strip()
    v_lower = v.lower()
    mapping = {
        "m": 1, "남": 1, "남자": 1, "male": 1,
        "f": 2, "여": 2, "여자": 2, "female": 2,
    }
    if v in mapping:
        return mapping[v]
    if v_lower in mapping:
        return mapping[v_lower]
    # Try numeric
    try:
        return int(float(v))
    except Exception:
        print("[WARN] Unknown gender, defaulting to 1(남)")
        return 1


def _normalize_age_grp(value: Optional[str]) -> int:
    if value is None:
        v = input("AGE_GRP (예: 20, 30대): ").strip()
    else:
        v = str(value).strip()
    # Accept '30대' -> 30, '30' -> 30
    try:
        # extract leading digits
        digits = "".join(ch for ch in v if ch.isdigit())
        if digits:
            return int(digits)
        return int(float(v))
    except Exception:
        print("[WARN] Unknown AGE_GRP, defaulting to 30")
        return 30


def _normalize_activity_type(value: Optional[str]) -> str:
    choices = [
        "취식", "쇼핑", "체험", "산책", "휴식", "기타", "이동", "없음",
    ]
    if value is None:
        print("ACTIVITY_TYPE (아래 중 선택):")
        print(", ".join(choices))
        v = input("> ").strip()
    else:
        v = str(value).strip()

    # If user enters a known label
    if v in ACT_LABEL_TO_CODE:
        return ACT_LABEL_TO_CODE[v]

    # Accept variants: '쇼핑 / 구매' etc.
    vv = v.replace(" ", "").replace("/", "")
    for k in list(ACT_LABEL_TO_CODE.keys()):
        kk = k.replace(" ", "").replace("/", "")
        if vv == kk:
            return ACT_LABEL_TO_CODE[k]

    # Accept raw code like '1','2','99'
    if v.isdigit():
        return v

    # Accept pattern like 'A01' -> '1'
    if (len(v) >= 2) and (v[0] in ("A", "a")) and v[1:].isdigit():
        return str(int(v[1:]))

    print("[WARN] Unknown ACTIVITY_TYPE; defaulting to '없음'(99)")
    return "99"


def build_input_row(
    trip_days: Optional[float],
    gender: Optional[str],
    age_grp: Optional[str],
    activity_type_cd: Optional[str],
):
    # If any field is missing, prompt interactively
    if trip_days is None:
        while True:
            v = input("TRIP_DAYS (ex. 3 or 3.0): ").strip()
            try:
                trip_days = float(v)
                break
            except ValueError:
                print("Please enter a valid number for TRIP_DAYS.")

    g = _normalize_gender(gender)
    a = _normalize_age_grp(age_grp)
    act = _normalize_activity_type(activity_type_cd)

    row = {
        "TRIP_DAYS": float(trip_days),  # numeric
        "GENDER": int(g),               # numeric
        "AGE_GRP": int(a),             # numeric (e.g., 20,30,...)
        "ACTIVITY_TYPE_CD": str(act),  # categorical code as string
    }
    X = pd.DataFrame([row], columns=LITE_FEATURES)
    return X


def main():
    parser = argparse.ArgumentParser(
        description="Predict IS_FAILED_TRIP using the lite CatBoost model (4 features)."
    )
    parser.add_argument(
        "--model-path",
        default="ML/outputs/01_Catboost/catboost_best_model_lite.joblib",
        help="Path to the saved lite model.",
    )
    parser.add_argument("--trip-days", type=float, default=None, help="Trip days (float)")
    parser.add_argument("--gender", type=str, default=None, help="Gender (M/F/남/여 or numeric)")
    parser.add_argument("--age-grp", type=str, default=None, help="Age group (e.g., 30, 30대)")
    parser.add_argument(
        "--activity-type",
        type=str,
        default=None,
        help="One of [취식, 쇼핑, 체험, 산책, 휴식, 기타, 이동, 없음] or code (1..7,99 or A01..A99)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Decision threshold for positive class (default: 0.5)",
    )

    args = parser.parse_args()

    model = load_model(args.model_path)
    X = build_input_row(args.trip_days, args.gender, args.age_grp, args.activity_type)

    proba = float(model.predict_proba(X)[:, 1][0])
    pred = int(proba >= args.threshold)

    print("Input:")
    print(X.to_dict(orient="records")[0])
    print(f"Predicted proba (class=1=failed): {proba:.4f}")
    print(f"Predicted label @threshold={args.threshold:.2f}: {pred}")


if __name__ == "__main__":
    main()
