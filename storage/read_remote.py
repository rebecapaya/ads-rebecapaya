import os
import time

import pandas as pd
import pyarrow.fs as fs

s3 = fs.S3FileSystem(endpoint_override=os.environ.get("S3_ENDPOINT"))
bucket = os.environ.get("S3_BUCKET", "taxi")


def timed(label, read):
    start = time.perf_counter()
    result = read()
    print(f"{label:30} {time.perf_counter() - start:6.2f} s")
    return result


timed("Parquet, all columns",
      lambda: pd.read_parquet(f"{bucket}/raw/trips.parquet", filesystem=s3))
timed("Parquet, 2 columns",
      lambda: pd.read_parquet(f"{bucket}/raw/trips.parquet", filesystem=s3,
                              columns=["passenger_count", "total_amount"]))


def read_csv():
    with s3.open_input_stream(f"{bucket}/raw/trips.csv") as f:
        return pd.read_csv(f)


timed("CSV, all columns", read_csv)

one_day = timed("One day, partitioned",
                lambda: pd.read_parquet(f"{bucket}/by_day", filesystem=s3,
                                        filters=[("pickup_day", "==", "2024-01-15")]))
print("trips on 2024-01-15:", len(one_day))
