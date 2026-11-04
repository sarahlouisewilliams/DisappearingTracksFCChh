import pandas as pd

df = pd.read_csv("results/stable_6T_fixed.csv")
df = df[df.fit_status == "ok"].copy()

df["pt_residual"] = (
    df["fitted_pt_gev"] - df["truth_pt_gev"]
) / df["truth_pt_gev"]

print(df[[
    "truth_pt_gev",
    "fitted_pt_gev",
    "fitted_radius_mm",
    "pt_residual",
    "chi2_ndof"
]].describe(percentiles=[0.1, 0.5, 0.9]))