import os

import pandas as pd
import pyarrow.fs as fs

s3 = fs.S3FileSystem(
    endpoint_override=os.environ.get("S3_ENDPOINT"),
    allow_bucket_creation=True,
)
bucket = os.environ.get("S3_BUCKET", "taxi")

s3.create_dir(bucket)

fs.copy_files("data/trips.parquet", f"{bucket}/raw/trips.parquet",
              destination_filesystem=s3)
fs.copy_files("data/trips.csv", f"{bucket}/raw/trips.csv",
              destination_filesystem=s3)

# One folder per day. A few trips have wrong dates (2002, 2009): keep January.
df = pd.read_parquet("data/trips.parquet")
jan = df[df["tpep_pickup_datetime"].between("2024-01-01", "2024-02-01")].copy()
jan["pickup_day"] = jan["tpep_pickup_datetime"].dt.strftime("%Y-%m-%d")
jan.to_parquet(
    f"{bucket}/by_day",
    filesystem=s3,
    partition_cols=["pickup_day"],
    # Replace a day's files when re-running, instead of adding more next to them
    existing_data_behavior="delete_matching",
)

for info in s3.get_file_info(fs.FileSelector(f"{bucket}/raw")):
    print(info.path, info.type.name, info.size)
