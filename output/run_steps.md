# Reproduction steps

The public task image provides Python 3.11 and the input files under `/app/data/`.
From any working directory, rebuild every scored artifact with one command:

```bash
python /app/output/src/run_analysis.py --data-dir /app/data --output-dir /app/output
```

For a fresh compatible Python 3.11 environment outside the task image:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r /app/output/requirements.txt
python /app/output/src/run_analysis.py --data-dir /app/data --output-dir /app/output
```

The script never writes to `/app/data/`. It overwrites only the generated CSV,
PNG, Markdown, and JSON artifacts under `/app/output/`.
