from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
from paddleocr import PaddleOCR
from ultralytics import YOLO
from utils import correct_plate
import os

app = FastAPI()

# CORS pentru Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://anpr-production.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inițializare modele
model = YOLO("yolov8n.pt")  # ⚠️ vezi nota despre modelul corect
ocr = PaddleOCR(use_angle_cls=True, lang='en')

@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image_array = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    print("Running YOLO detection...")
    results = model.predict(source=frame, verbose=True)
    plates_detected = []

    print(f"YOLO returned {len(results)} result(s)")

    for result in results:
        boxes = result.boxes
        if boxes is None or boxes.xyxy is None or len(boxes.xyxy) == 0:
            print("No bounding boxes found.")
            continue

        for i, box in enumerate(boxes.xyxy):
            x1, y1, x2, y2 = map(int, box[:4])
            crop = frame[y1:y2, x1:x2]

            print(f"Cropping region {i}: x1={x1}, y1={y1}, x2={x2}, y2={y2}")

            if crop.size > 0:
                # Opțional: salvează crop pentru debugging
                cv2.imwrite(f"/tmp/crop_{i}.jpg", crop)

                print("Running OCR on detected region...")
                ocr_result = ocr.ocr(crop, cls=True)

                if ocr_result and ocr_result[0]:
                    for line in ocr_result[0]:
                        if len(line) >= 2:
                            raw_text, conf = line[1]
                            print(f"OCR raw result: {raw_text}, confidence: {conf}")
                            plate = correct_plate(raw_text)
                            if plate:
                                print(f"Valid plate detected: {plate}")
                                plates_detected.append({"text": plate, "confidence": conf})
                            else:
                                print("Text ignored (not a valid plate).")
                else:
                    print("No text detected in crop.")
            else:
                print("Invalid crop.")

    print(f"Returning {len(plates_detected)} plate(s)")
    return {"plates": plates_detected}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
