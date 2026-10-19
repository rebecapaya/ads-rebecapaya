import os
import time

import pandas as pd

df = pd.read_parquet("data/yellow_tripdata_2024-01.parquet")
print("rows, columns:", df.shape)

df.to_csv("data/trips.csv", index=False)
df.to_json("data/trips.json", orient="records", lines=True, date_format="iso")
df.to_parquet("data/trips.parquet", compression="zstd")

for name in ["trips.csv", "trips.json", "trips.parquet"]:
    size_mb = os.path.getsize(f"data/{name}") / 1_000_000
    print(f"{name:15} {size_mb:8.0f} MB")


def timed(label, read):
    start = time.perf_counter()
    result = read()
    print(f"{label:30} {time.perf_counter() - start:6.2f} s")
    return result


csv = timed("CSV, all columns", lambda: pd.read_csv("data/trips.csv"))
timed("JSON, all columns", lambda: pd.read_json("data/trips.json", lines=True))
parquet = timed("Parquet, all columns", lambda: pd.read_parquet("data/trips.parquet"))

columns = ["passenger_count", "total_amount"]
timed("CSV, 2 columns", lambda: pd.read_csv("data/trips.csv", usecols=columns))
timed("Parquet, 2 columns", lambda: pd.read_parquet("data/trips.parquet", columns=columns))

print("pickup time from CSV:    ", csv["tpep_pickup_datetime"].dtype)
print("pickup time from Parquet:", parquet["tpep_pickup_datetime"].dtype)