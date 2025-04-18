from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
from paddleocr import PaddleOCR
from ultralytics import YOLO
from utils import correct_plate, process_plate_detection
import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://anpr-production.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# YOLO + OCR
model = YOLO("yolov8n.pt")
ocr = PaddleOCR(use_angle_cls=True, lang='en')

# DB config from .env
DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME")
}

def get_abonament_info(numar_inmatriculare):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query = """
            SELECT nume_proprietar, data_achizitie, data_expirare
            FROM abonamente
            WHERE LOWER(numar_inmatriculare) = LOWER(%s)
        """
        cursor.execute(query, (numar_inmatriculare,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            nume, achizitie, expirare = result
            acum = datetime.utcnow()
            timp_ramas = expirare - acum
            return {
                "nume_proprietar": nume,
                "data_achizitie": achizitie,
                "data_expirare": expirare,
                "timp_ramas": str(timp_ramas) if timp_ramas.total_seconds() > 0 else "Expirat"
            }
    except Exception as e:
        print(f"DB Error: {e}")
    return None

@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image_array = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    print("Running YOLO detection...")
    results = model(frame)
    plates_detected = []

    for result in results:
        for box in result.boxes.xyxy:
            x1, y1, x2, y2 = map(int, box[:4])
            crop = frame[y1:y2, x1:x2]

            if crop.size > 0:
                print("Running OCR on detected region...")
                ocr_result = ocr.ocr(crop, cls=True)
                if ocr_result and ocr_result[0]:
                    for line in ocr_result[0]:
                        raw_text, conf = line[1]
                        print(f"OCR raw: {raw_text}")
                        plate = correct_plate(raw_text)
                        if plate:
                            print(f"Valid plate: {plate}")
                            abonament = get_abonament_info(plate)
                            plates_detected.append({
                                "text": plate,
                                "confidence": conf,
                                "abonament_info": abonament
                            })

    plates_detected = process_plate_detection(plates_detected)
    return {"plates": plates_detected}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
