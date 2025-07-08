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

ocr = PaddleOCR(use_angle_cls=True, lang='en')

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

class SubscriptionCreate(BaseModel):
    nume: str
    prenume: str
    numar_inmatriculare: str
    durata_minute: int

@app.post("/add-subscription")
async def add_subscription(data: SubscriptionCreate):
    query_check = select(Subscription).where(Subscription.c.numar_inmatriculare == data.numar_inmatriculare)
    existing_record = await database.fetch_one(query_check)

    if existing_record:
        return {
            "message": f"Abonament deja existent pe numele {existing_record['nume']} {existing_record['prenume']}",
            "numar_inmatriculare": data.numar_inmatriculare,
            "expira_pe": str(existing_record["data_expirare"])
        }

    data_achizitie = datetime.utcnow() + timedelta(hours=3)
    data_expirare = data_achizitie + timedelta(minutes=data.durata_minute)

    query = insert(Subscription).values(
        nume=data.nume,
        prenume=data.prenume,
        numar_inmatriculare=data.numar_inmatriculare,
        data_achizitie=data_achizitie,
        data_expirare=data_expirare
    )
    await database.execute(query)

    return {
        "message": "Abonament adaugat cu succes",
        "nume": data.nume,
        "prenume": data.prenume,
        "expira_pe": str(data_expirare)
    }

def formateaza_status(delta: timedelta) -> str:
    zile = delta.days
    ore = delta.seconds // 3600
    minute = (delta.seconds % 3600) // 60

    parts = []
    if zile > 0:
        parts.append((zile, "zi", "zile", "feminin"))
    if ore > 0:
        parts.append((ore, "oră", "ore", "feminin"))
    if minute > 0:
        parts.append((minute, "minut", "minute", "masculin"))

    if not parts:
        return "mai puțin de un minut rămas"

    if len(parts) == 1:
        valoare, singular, plural, gen = parts[0]
        forma = singular if valoare == 1 else plural
        if valoare == 1:
            return f"{valoare} {forma} {'rămasă' if gen == 'feminin' else 'rămas'}"
        else:
            return f"{valoare} {forma} rămase"
    else:
        fragmente = []
        for valoare, singular, plural, _ in parts:
            forma = singular if valoare == 1 else plural
            fragmente.append(f"{valoare} {forma}")
        return " și ".join(fragmente) + " rămase"

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
            if len(line) >= 2 and isinstance(line[1], (list, tuple)) and len(line[1]) >= 2:
                raw_text, conf = line[1]
                plate = correct_plate(raw_text)
                if plate:
                    plates_detected.append({"text": plate, "confidence": conf})

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

class AchitaParcareRequest(BaseModel):
    numar_inmatriculare: str
    data_expirare: datetime

class VerificaParcareRequest(BaseModel):
    numar_inmatriculare: str

@app.post("/achita-parcare")
async def achita_parcare(data: AchitaParcareRequest):
    acum = datetime.utcnow() + timedelta(hours=3)

    query_check = select(Subscription).where(
        Subscription.c.numar_inmatriculare == data.numar_inmatriculare,
        Subscription.c.data_expirare == None
    )
    record = await database.fetch_one(query_check)

    if not record:
        raise HTTPException(status_code=404, detail="Nu există o înregistrare activă fără expirare pentru această mașină")

    delta = data.data_expirare - acum
    durata_formatata = formateaza_status(delta)

    query_update = update(Subscription).where(
        Subscription.c.numar_inmatriculare == data.numar_inmatriculare,
        Subscription.c.data_expirare == None
    ).values(data_expirare=data.data_expirare)
    await database.execute(query_update)

    return {
        "message": f"Parcarea a fost achitată cu succes pentru {durata_formatata}",
        "expira_pe": str(data.data_expirare)
    }

@app.post("/verifica-parcare")
async def verifica_parcare(data: VerificaParcareRequest):
    numar_inmatriculare = data.numar_inmatriculare

    query = select(Subscription).where(
        Subscription.c.numar_inmatriculare == numar_inmatriculare
    )
    record = await database.fetch_one(query)

    if not record:
        return {"status": "neînregistrat"}

    acum = datetime.utcnow() + timedelta(hours=3)
    expirare = record["data_expirare"]

    if expirare is None:
        return {"status": "neachitat", "data_achizitie": str(record["data_achizitie"])}

    delta = expirare - acum
    total_secunde = int(delta.total_seconds())

    if total_secunde > 0:
        status = formateaza_status(delta)
    elif total_secunde == 0:
        status = "tocmai a expirat parcarea"
    else:
        status = "expirată"

    return {
        "status": status,
        "nume_complet": f"{record['nume']} {record['prenume']}" if record['nume'] else None,
        "data_achizitie": str(record["data_achizitie"]),
        "data_expirare": str(record["data_expirare"])
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
