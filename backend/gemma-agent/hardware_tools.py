import cv2

def get_hardware_diagnostics(device_id: str):
    # Retrieves real-time voltage and thermal data for a specific device
    mock_data = {
        "HW-99": {"temp": "42°C", "load": "12%", "status": "Stable"},
        "HW-ERR-01": {"temp": "88°C", "load": "98%", "status": "CRITICAL_OVERHEAT"}
    }
    return mock_data.get(device_id, {"error": "Device not found"})

def scan_qr_from_webcam():
    # Scans the webcam for a QR code and returns the string
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()
    print("Webcam active... looking for QR code.")
    
    while True:
        _, img = cap.read()
        data, _, _ = detector.detectAndDecode(img)
        if data:
            cap.release()
            return data
        if cv2.waitKey(1) == ord('q'): 
            cap.release()
            return "Scan cancelled."
