import cv2
import torch
import numpy as np
from paddleocr import PaddleOCR
from ultralytics import YOLO
from utils import correct_plate, save_to_csv

# ✅ Încarcă modele O DATĂ (evită consumul excesiv de memorie)
device = "cuda" if torch.cuda.is_available() else "cpu"
model = YOLO("yolov8s.pt").to(device)  # Model YOLO mai mic
ocr = PaddleOCR(use_angle_cls=True, lang='en')

def process_frame(frame):
    with torch.no_grad():  # ✅ Evită consum inutil de memorie
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
                        text, conf = line[1]
                        text = correct_plate(text.upper().replace(" ", ""))
                        plates_detected.append((text, conf, (x1, y1, x2, y2)))
    
    return plates_detected

if __name__ == "__main__":
    # ✅ Test pe imagine în loc de webcam (evită erorile pe servere)
    frame = cv2.imread("test.jpg")
    if frame is None:
        print("Eroare: Nu s-a găsit imaginea 'test.jpg'")
    else:
        plates = process_frame(frame)
        save_to_csv([[text, conf, bbox] for text, conf, bbox in plates])
        
        for text, conf, (x1, y1, x2, y2) in plates:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{text} ({conf:.2f})", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        cv2.imwrite("output.jpg", frame)  # ✅ Salvează rezultatul
        print("Rezultatul a fost salvat ca 'output.jpg'")
