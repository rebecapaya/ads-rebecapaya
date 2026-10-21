# Storage practice session for Agile Data Science class

This small project shows where data can live and in which format: the same
dataset as CSV, JSON and [Parquet](https://parquet.apache.org/), stored on
your disk and on S3-compatible object storage running on your laptop
([RustFS](https://rustfs.com/)), and read by a small app running in Docker.

## Create a GitHub repository

As seen on class create a new GitHub Repository.

Name it `ub-agile-data-science-storage`.

Clone the repository locally via the following command:

- note: substitute `${YOUR_USER}` for your username on GitHub (you can copy and paste the URL from GitHub)

```bash
git clone git@github.com:rebecapaya/ub-agile-data-science-storage.git
cd ub-agile-data-science-storage
```

## Python environment

With your text editor or your IDE (Visual Studio Code for example) create a file `requirements.txt` with:

```
pandas==3.0.6
pyarrow==26.0.0
```

`pandas` 3 needs Python 3.11 or newer. Check with `python --version`.

I recommend you to use a virtual environment, a conda environment or any other tool you use to manage your Python environments.
Example with virtualenv:

```bash
python -m venv .venv
```

Activate the virtual environment on Linux or macOS:

```bash
source .venv/bin/activate
```

For Windows you might need to use from `git bash`:

```bash
source .venv/Scripts/activate
```

Install `requirements.txt`:

```bash
pip install -r requirements.txt
```

Create a `.gitignore` file so Git does not track your virtual environment
or the data:

```
.venv/
__pycache__/
data/
```

Add, commit and push to GitHub:

```bash
git add requirements.txt .gitignore
git commit -m "Add requirements and gitignore"
git push
```

## Get the data

New York City yellow taxi trips for January 2024, around 50 MB:

```bash
mkdir data
curl -L -o data/yellow_tripdata_2024-01.parquet \
  https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
```

Check `git status`. The `data` folder does not show up: we told Git to
ignore it. Data does not belong in Git, the same way it did not belong in
the Docker image last session. By the end of this session it will live in a
bucket.

## Exercise 1: file formats

Create a file called `formats.py` with the following contents:

```python
import os
import time

import pandas as pd

df = pd.read_parquet("data/yellow_tripdata_2024-01.parquet")
print("rows, columns:", df.shape)

df.to_csv("data/trips.csv", index=False)
df.to_json("data/trips.json", orient="records", lines=True, date_format="iso")
df.to_parquet("data/trips.parquet")

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
```

Run it. It takes around a minute, the JSON file is the slow one:

```bash
python formats.py
```

You should see something like this. Your times will be different, the
ratios should not:

```
rows, columns: (2964624, 19)
trips.csv            311 MB
trips.json          1271 MB
trips.parquet         61 MB
CSV, all columns                 2.45 s
JSON, all columns               15.35 s
Parquet, all columns             0.06 s
CSV, 2 columns                   0.72 s
Parquet, 2 columns               0.03 s
pickup time from CSV:     str
pickup time from Parquet: datetime64[us]
```

You will also see a `DtypeWarning` about `store_and_fwd_flag` when reading the
CSV. Read it: what is pandas complaining about?

Questions:


- Why is the JSON file 20 times bigger than the Parquet file?

  JSON repeats every column name in every row (about 3 million times) and stores everything as text. Parquet stores the schema once, uses binary types and compresses each column.

- Why is reading 2 columns from the CSV still so much slower than from Parquet?

  CSV is row-oriented: pandas must read and parse every row, with all 19 columns, to extract 2 of them. Parquet is columnar, so it reads only those 2 columns, already typed and compressed (1.68 s vs 0.03 s in my run).

- Change `df.to_parquet("data/trips.parquet")` to use `compression="zstd"`. What is the size now?

  49.3 MB with zstd, against 61 MB with the default Snappy.
Commit and push:

```bash
git add formats.py
git commit -m "Compare CSV, JSON and Parquet"
git push
```

## Exercise 2: object storage on your laptop

Create a file `compose.yaml` that starts an S3-compatible server:

```yaml
services:
  storage:
    image: rustfs/rustfs:1.0.1
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      RUSTFS_ACCESS_KEY: student
      RUSTFS_SECRET_KEY: student-secret
    volumes:
      - s3data:/data

volumes:
  s3data:
```

Start it:

```bash
docker compose up -d
```

- Port `9000` is the S3 API, what your code talks to.
- Port `9001` is a web console. Open http://localhost:9001/rustfs/console/
  and log in with `student` / `student-secret`. There are no buckets yet.

Your code finds the credentials and the server address in environment
variables. Set them in the terminal where you will run Python.

Linux, macOS or `git bash`:

```bash
export AWS_ACCESS_KEY_ID=student
export AWS_SECRET_ACCESS_KEY=student-secret
export AWS_REGION=us-east-1
export S3_ENDPOINT=http://localhost:9000
```

Windows PowerShell:

```powershell
$env:AWS_ACCESS_KEY_ID="student"
$env:AWS_SECRET_ACCESS_KEY="student-secret"
$env:AWS_REGION="us-east-1"
$env:S3_ENDPOINT="http://localhost:9000"
```

`S3_ENDPOINT` is our own variable. On real AWS you would not set it, and
the same code would talk to Amazon.

Create a file `upload.py`:

```python
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
```

Run it:

```bash
python upload.py
```

```
taxi/raw/trips.csv File 310608360
taxi/raw/trips.parquet File 60840464
```

Refresh the web console. Open the `taxi` bucket and look inside `by_day`:
one folder per day, `pickup_day=2024-01-01` and so on.

Now read it back. Create a file `read_remote.py`:

```python
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
```

Run it:

```bash
python read_remote.py
```

```
Parquet, all columns             0.12 s
Parquet, 2 columns               0.03 s
CSV, all columns                 4.67 s
One day, partitioned             0.06 s
trips on 2024-01-15: 77033
```

The server is on your own laptop, so there is almost no network in between.
Against a real bucket in another country every request costs tens of
milliseconds, and reading less data matters even more.

Questions:

- Compare `read_remote.py` with `formats.py`. What changed in the pandas calls?
In read_remote.py, the pandas functions read the data directly from S3-compatible object storage instead of reading local files. A PyArrow S3 filesystem is passed through the filesystem=s3 argument, allowing pandas to access remote objects. The Parquet calls remain almost identical, while the CSV file is read through an input stream opened from the bucket.

- Run `docker compose down` and `docker compose up -d`. Is the data still in the console? And after `docker compose down -v`?
After running docker compose down followed by docker compose up -d, the data was still available in the RustFS console because the Docker volume was preserved. However, after running docker compose down -v, the volume was deleted and all stored data disappeared. A new empty volume was created when the services were started again.

- Unset `S3_ENDPOINT` (`unset S3_ENDPOINT`) and run `read_remote.py`. Read the error. Who are you talking to now?
After removing S3_ENDPOINT, the application no longer knew that it should connect to the local RustFS server. Instead, PyArrow attempted to use the default AWS S3 endpoint. This resulted in an ACCESS_DENIED error because the credentials were not valid for Amazon S3. Therefore, the application was trying to talk to Amazon S3 instead of the local S3-compatible storage service.

Set `S3_ENDPOINT` again, run `python upload.py` if you deleted the data, then
commit and push:

```bash
git add compose.yaml upload.py read_remote.py
git commit -m "Store and read the data on S3-compatible storage"
git push
```

## Exercise 3: an app that reads from the bucket

Same app idea as last session, now answering questions about taxi trips.
Create a folder `app` with three files.

`app/requirements.txt`:

```
flask==3.1.3
pandas==3.0.6
pyarrow==26.0.0
```

`app/Dockerfile`:

```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

`app/app.py`:

```python
import os

import pandas as pd
import pyarrow.fs as fs
from flask import Flask

app = Flask(__name__)

s3 = fs.S3FileSystem(endpoint_override=os.environ.get("S3_ENDPOINT"))
BUCKET = os.environ.get("S3_BUCKET", "taxi")


@app.route('/trips/<day>')
def trips(day):
    df = pd.read_parquet(
        f"{BUCKET}/by_day",
        filesystem=s3,
        columns=["total_amount"],
        filters=[("pickup_day", "==", day)],
    )
    return f"{day}: {len(df)} trips, {df['total_amount'].mean():.2f} USD on average"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

The app reads one partition and one column: a couple of hundred KB, not the
whole dataset.

Add a `web` service to `compose.yaml`. The whole file:

```yaml
services:
  storage:
    image: rustfs/rustfs:1.0.1
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      RUSTFS_ACCESS_KEY: student
      RUSTFS_SECRET_KEY: student-secret
    volumes:
      - s3data:/data

  web:
    build: ./app
    ports:
      - "5001:5000"
    environment:
      S3_ENDPOINT: http://storage:9000
      AWS_ACCESS_KEY_ID: student
      AWS_SECRET_ACCESS_KEY: student-secret
      AWS_REGION: us-east-1
    depends_on:
      - storage

volumes:
  s3data:
```

Notice `S3_ENDPOINT`: from your laptop it is `http://localhost:9000`, from
the `web` container it is `http://storage:9000`, the service name. Inside a
container, `localhost` is the container itself. Same code, different
configuration.

Start everything:

```bash
docker compose up -d --build
```

Open http://localhost:5001/trips/2024-01-15 in your browser:

```
2024-01-15: 77033 trips, 28.11 USD on average
```

Questions:

- Which day of January had the most trips?
- Change `S3_ENDPOINT` for `web` to `http://localhost:9000` and run `docker compose up -d` again. What happens, and why? Check with `docker compose logs web`.
- The credentials are written in `compose.yaml`, and that file is in Git. Fine for a local test server. What would you do for real credentials?

Put `S3_ENDPOINT` back to `http://storage:9000`, then commit and push:

```bash
git add app compose.yaml
git commit -m "Add app that reads trips from object storage"
git push
```

## What would change on a real cloud

| | This repository | AWS S3 |
|---|---|---|
| `S3_ENDPOINT` | `http://localhost:9000` or `http://storage:9000` | not set |
| Credentials | `student` / `student-secret` | an IAM access key, or a role on the machine |
| `AWS_REGION` | anything | the region of the bucket |
| `S3_BUCKET` | `taxi` | a globally unique name |
| The Python code | | unchanged |

If you want to try it on a real cloud without a credit card,
[Azure for Students](https://azure.microsoft.com/en-us/free/students) gives
you credit with your university email. pyarrow talks to Azure Blob Storage
with `pyarrow.fs.AzureFileSystem`, and the pandas calls stay the same.

## Clean up

Stop the containers and delete the stored data:

```bash
docker compose down -v
```

The `data` folder is around 1.7 GB with the CSV and JSON files. Delete it
when you are done.
