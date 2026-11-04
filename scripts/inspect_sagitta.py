import pandas as pd

df = pd.read_csv("results/stable_6T_fixed.csv")
df = df[df.fit_status == "ok"]

cols = [
    "chord_length_mm",
    "sagitta_mid_mm",
    "sagitta_mid_fraction",
    "max_abs_sagitta_mm",
    "expected_sagitta_mm",
]

print(df[cols].describe(percentiles=[0.1, 0.5, 0.9]))