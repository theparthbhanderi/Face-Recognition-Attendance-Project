import cv2

# Try to access the camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open camera.")
    print("Make sure your camera is connected and not being used by another application.")
else:
    print("Camera opened successfully!")
    ret, frame = cap.read()
    if ret:
        print("Successfully captured a frame!")
    else:
        print("Could not read frame from camera.")
    cap.release()
    print("Camera released.")

print("Test complete.")
