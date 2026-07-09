FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_servers/ mcp_servers/
COPY tests/ tests/
COPY main.py .

CMD ["python", "main.py"]
