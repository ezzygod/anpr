FROM python:3.9.0

# Instalare dependențe sistem necesare pentru OpenCV și PaddleOCR
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Setez directorul de lucru
WORKDIR /app

# Copiez fisierele proiectului
COPY . .

# Actualizez pip, setuptools și wheel (important pentru build-ul unor pachete)
RUN pip install --upgrade pip setuptools wheel

# Instalează pachetele din requirements.txt
RUN pip install -r requirements.txt

# Expune portul aplicației FastAPI
EXPOSE 8000

# Comandă de rulare a aplicației
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
