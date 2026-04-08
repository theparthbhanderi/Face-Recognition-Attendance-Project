import cv2
import time

def test_camera():
    # Try different camera backends
    for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
        print(f"\nTrying camera with backend: {backend}")
        cap = cv2.VideoCapture(0 + backend)
        
        if not cap.isOpened():
            print(f"Failed to open camera with backend {backend}")
            cap.release()
            continue
            
        print(f"Successfully opened camera with backend {backend}")
        print("Press 'q' to quit the camera preview")
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Error: Couldn't read frame")
                    break
                    
                # Display the frame
                cv2.imshow('Camera Test - Press q to quit', frame)
                
                # Break the loop on 'q' key press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except Exception as e:
            print(f"Error: {e}")
            
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("Camera released")
            
    print("\nCamera test completed.")

if __name__ == "__main__":
    test_camera()
