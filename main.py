from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2
import numpy as np
from paddleocr import PaddleOCR
from utils import correct_plate, process_plate_detection
from database import database, Subscription
from sqlalchemy import insert, select, update
from datetime import datetime, timedelta
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://anpr-production.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ocr = PaddleOCR(use_angle_cls=True, lang='en')  # Fără YOLO

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ... clasele BaseModel rămân identice ...

@app.post("/process")
async def process_image(request: Request, file: UploadFile = File(...)):  
    image_bytes = await file.read()
    image_array = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return await detect_from_frame(frame, request)


async def detect_from_frame(frame, request: Request):
    add_if_not_found = request.query_params.get("add", "false").lower() == "true"
    plates_detected = []

    ocr_result = ocr.ocr(frame)
    if ocr_result and ocr_result[0]:
        for line in ocr_result[0]:
            try:
                raw_text, conf = line[1]
                plate = correct_plate(raw_text)
                if plate:
                    plates_detected.append({"text": plate, "confidence": conf})
            except Exception as e:
                print("Eroare OCR:", e)

    plates_detected = process_plate_detection(plates_detected)

    results = []
    for plate_info in plates_detected:
        plate_text = plate_info["text"]

        query = select(Subscription).where(Subscription.c.numar_inmatriculare == plate_text)
        record = await database.fetch_one(query)

        if record:
            acum = datetime.utcnow() + timedelta(hours=3)
            data_expirare = record["data_expirare"]
            delta = data_expirare - acum if data_expirare else timedelta(0)
            total_secunde = int(delta.total_seconds()) if data_expirare else 0

            if data_expirare is None:
                status = "neachitat"
            elif total_secunde > 0:
                status = formateaza_status(delta)
            elif total_secunde == 0:
                status = "tocmai a expirat abonamentul"
            else:
                status = "expirat"

            plate_info.update({
                "nume_complet": f"{record['nume']} {record['prenume']}" if record['nume'] else None,
                "data_achizitie": str(record["data_achizitie"]),
                "data_expirare": str(record["data_expirare"]) if record["data_expirare"] else None,
                "status": status
            })
        else:
            if add_if_not_found:
                data_intrare = datetime.utcnow() + timedelta(hours=3)
                query_insert = insert(Subscription).values(
                    numar_inmatriculare=plate_text,
                    data_achizitie=data_intrare,
                )
                await database.execute(query_insert)

            plate_info = {
                "text": plate_info["text"],
                "confidence": plate_info["confidence"],
                "status": "neînregistrat"
            }

        results.append(plate_info)

    return {"plates": results}
