from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
from paddleocr import PaddleOCR
from ultralytics import YOLO
from utils import correct_plate, process_plate_detection
import os
import re

app = FastAPI()

# Permite CORS pentru toate originile (pentru testare locală)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://anpr-production.up.railway.app"],  # Atenție: în producție setează domenii sigure
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inițializare modele
model = YOLO("yolov8n.pt")
ocr = PaddleOCR(use_angle_cls=True, lang='en')


# Endpoint-ul pentru procesarea imaginii
@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image_array = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    print("Running YOLO detection...")
    results = model(frame)  # Detectarea obiectelor cu YOLO
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
                            plates_detected.append({"text": plate, "confidence": conf})

    # Procesăm plăcuțele pentru a elimina duplicatele și valorile None
    plates_detected = process_plate_detection(plates_detected)

    return {"plates": plates_detected}

# Pornirea aplicației FastAPI
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
