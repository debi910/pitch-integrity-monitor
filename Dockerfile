# docker build -t pim . && docker run -p 8501:8501 pim          (the app)
# docker run pim python -m pim data/slim/statcast_2025.parquet   (the monitor on a season)
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest
COPY . .
RUN python -m pytest -q
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
