import cv2
import torch
import numpy as np
from paddleocr import PaddleOCR
from ultralytics import YOLO
from utils import correct_plate, save_to_csv

# Inițializare modele
model = YOLO("yolov8n.pt")  # Modelul YOLOv8
ocr = PaddleOCR(use_angle_cls=True, lang='en')

def process_frame(frame):
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

def main():
    cap = cv2.VideoCapture(1)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        plates = process_frame(frame)
        save_to_csv([[text, conf, bbox] for text, conf, bbox in plates])
        
        for text, conf, (x1, y1, x2, y2) in plates:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{text} ({conf:.2f})", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        cv2.imshow("License Plate Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
