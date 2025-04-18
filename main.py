from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
from paddleocr import PaddleOCR
from ultralytics import YOLO
from utils import correct_plate, process_plate_detection
from database import database, Subscription
from datetime import date
import os
import re

app = FastAPI()

# CORS (poți modifica domeniul pentru siguranță în producție)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # sau ["https://anpr-production.up.railway.app"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inițializare modele
model = YOLO("yolov8n.pt")
ocr = PaddleOCR(use_angle_cls=True, lang='en')

# Conectare / Deconectare la baza de date
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

    results = model(frame)  # YOLO
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

        # Căutare în baza de date
        query = Subscription.__table__.select().where(Subscription.plate == plate_text)
        record = await database.fetch_one(query)

        if record:
            days_left = (record["end_date"] - date.today()).days
            plate_info.update({
                "owner": record["owner"],
                "start_date": str(record["start_date"]),
                "end_date": str(record["end_date"]),
                "days_left": days_left
            })
        else:
            plate_info.update({
                "owner": None,
                "start_date": None,
                "end_date": None,
                "days_left": None
            })

        results.append(plate_info)

    return {"plates": results}


# Pentru rulare locală
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
