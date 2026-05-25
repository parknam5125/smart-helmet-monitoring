import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(BASE_DIR, "case_library2.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "Final_case.json")


def temp_risk(temp):
    if temp >= 37:
        return "HIGH"
    elif temp >= 33:
        return "MID"
    else:
        return "LOW"


def noise_risk(noise):
    if noise >= 90:
        return "HIGH"
    elif noise >= 85:
        return "MID"
    else:
        return "LOW"


def final_label(temp, noise):
    t = temp_risk(temp)
    n = noise_risk(noise)
    if t == "HIGH" or n == "HIGH":
        return "HIGH"
    if t == "MID" or n == "MID":
        return "MID"
    return "LOW"


with open(INPUT_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

case_list = []
for item in data:
    temp = float(item["temp"])
    noise = float(item["noise"])
    case_list.append({
        "helmet": item["helmet"],
        "temp": round(temp, 2),
        "noise": round(noise, 2),
        "Label": final_label(temp, noise),
    })

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(case_list, f, indent=4, ensure_ascii=False)

print(f"완료! 총 {len(case_list)}개 저장: {OUTPUT_PATH}")

label_counts = {"HIGH": 0, "MID": 0, "LOW": 0}
for c in case_list:
    label_counts[c["Label"]] += 1
print("라벨 분포:", label_counts)
