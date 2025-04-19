from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
from paddleocr import PaddleOCR
from ultralytics import YOLO
from utils import correct_plate, process_plate_detection
from database import database, Subscription
from datetime import datetime, timezone, timedelta
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://anpr-production.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = YOLO("yolov8n.pt")
ocr = PaddleOCR(use_angle_cls=True, lang='en')

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image_array = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    results = model(frame)
    plates_detected = []

    for result in results:
        for box in result.boxes.xyxy:
            x1, y1, x2, y2 = map(int, box[:4])
            crop = frame[y1:y2, x1:x2]

            if crop.size > 0:
                ocr_result = ocr.ocr(crop, cls=True)
                if ocr_result and ocr_result[0]:
                    for line in ocr_result[0]:
                        raw_text, conf = line[1]
                        plate = correct_plate(raw_text)
                        if plate:
                            plates_detected.append({"text": plate, "confidence": conf})

    plates_detected = process_plate_detection(plates_detected)

    results = []
    for plate_info in plates_detected:
        plate_text = plate_info["text"]

        query = Subscription.__table__.select().where(Subscription.numar_inmatriculare == plate_text)
        record = await database.fetch_one(query)

        if record:
            acum = datetime.utcnow() + timedelta(hours=3) # România = UTC+3
            data_expirare = record["data_expirare"]
            delta = data_expirare - acum
            total_secunde = int(delta.total_seconds())

            if total_secunde > 0:
                zile = delta.days
                ore = delta.seconds // 3600
                minute = (delta.seconds % 3600) // 60

                parts = []
                if zile > 0:
                    parts.append(f"{zile} zi{'le' if zile > 1 else ''}")
                if ore > 0:
                    parts.append(f"{ore} or{'e' if ore > 1 else 'ă'}")
                if minute > 0:
                    parts.append(f"{minute} minut{'e' if minute > 1 else ''}")

                if len(parts) > 0:
                    status = " și ".join(parts) + " rămase"
                else:
                    status = "mai puțin de un minut rămas"
            elif total_secunde == 0:
                status = "tocmai a expirat abonamentul"
            else:
                status = "expirat"

            plate_info.update({
                "nume_complet": f"{record['nume']} {record['prenume']}",
                "data_achizitie": str(record["data_achizitie"]),
                "data_expirare": str(record["data_expirare"]),
                "status": status
            })
        else:
            plate_info = {
                "text": plate_info["text"],
                "confidence": plate_info["confidence"],
                "status": "neînregistrat"
            }

        results.append(plate_info)

    return {"plates": results}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
