FROM python:3.10

# Actualizează sistemul și instalează librării necesare pentru OpenCV și OCR
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Setează directorul de lucru
WORKDIR /app

# Copiază fișierele proiectului în container
COPY . .

# Upgrade la pip, setuptools și wheel
RUN pip install --upgrade pip setuptools wheel

# Instalează toate dependințele din requirements.txt
RUN pip install -r requirements.txt

# Expune portul pe care va rula aplicația
EXPOSE 8000

# Comandă de pornire a aplicației FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
