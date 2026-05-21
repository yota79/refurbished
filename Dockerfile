FROM python:3.11-slim

WORKDIR /app

# Copiamo i requisiti
COPY requirements.txt .

# Installiamo le dipendenze e esplicitamente streamlit
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt && \
    pip install --no-cache-dir --break-system-packages streamlit

COPY . .

# Installiamo la CLI locale
RUN pip install --no-cache-dir --break-system-packages .

# Esponiamo la porta standard di Streamlit
EXPOSE 8501

# Cambiamo l'entrypoint per avviare l'app web
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
