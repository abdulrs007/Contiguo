# Territory Viewer (Streamlit)

A tiny Streamlit app to preview your **territories.geojson** and see quick stats.

## Run locally

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Upload your `out/run_001/territories.geojson` in the sidebar.

## Deploy on Hugging Face Spaces

1. Create a new **Space** → SDK: **Streamlit** → Public.
2. Add these files at the root:
   - `app.py`
   - `requirements.txt`
3. (Optional) Upload a sample to `out/run_001/territories.geojson` in the Space.
4. Commit — the Space will build automatically.
