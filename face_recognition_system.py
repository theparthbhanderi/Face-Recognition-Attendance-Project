import os
from datetime import datetime
import pickle

try:
    import cv2
    import face_recognition
    import numpy as np
    DEP_AVAILABLE = True
except Exception as _err:
    DEP_AVAILABLE = False
    print(f"Warning: face-recognition dependencies not available ({_err}). Running in degraded mode.")


class FaceRecognitionSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.encodings_file = 'face_encodings.pkl'
        if DEP_AVAILABLE:
            try:
                # Try to load a Haar cascade only if cv2 is available
                self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            except Exception:
                self.face_cascade = None

        # Load any saved encodings
        self.load_encodings()

    def load_encodings(self):
        if os.path.exists(self.encodings_file):
            try:
                with open(self.encodings_file, 'rb') as f:
                    data = pickle.load(f)
                    self.known_face_encodings = data.get('encodings', [])
                    self.known_face_names = data.get('names', [])
            except Exception:
                # If load fails, start with empty lists
                self.known_face_encodings = []
                self.known_face_names = []

    def save_encodings(self):
        try:
            with open(self.encodings_file, 'wb') as f:
                pickle.dump({
                    'encodings': self.known_face_encodings,
                    'names': self.known_face_names
                }, f)
        except Exception as e:
            print(f"Warning: could not save encodings: {e}")

    def add_new_face(self, image_path, name):
        if not DEP_AVAILABLE:
            return False, 'Face-recognition functionality is not available in this environment.'

        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            if not face_locations:
                return False, 'No face found in the image'

            face_encoding = face_recognition.face_encodings(image, [face_locations[0]])[0]
            self.known_face_encodings.append(face_encoding)
            self.known_face_names.append(name)
            self.save_encodings()
            return True, f"Successfully added {name} to the system"
        except Exception as e:
            return False, str(e)

    def recognize_faces(self, frame):
        if not DEP_AVAILABLE:
            return [], []

        try:
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small_frame, model='hog')
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            face_names = []
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
                name = 'Unknown'
                if len(self.known_face_encodings) > 0:
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index] and face_distances[best_match_index] < 0.6:
                        name = self.known_face_names[best_match_index]
                face_names.append(name)

            if face_locations:
                face_locations = np.array(face_locations) * 4
            else:
                face_locations = []

            return face_locations, face_names
        except Exception as e:
            print(f"Error in recognize_faces: {e}")
            return [], []

    def capture_face(self, name):
        if not DEP_AVAILABLE:
            return False, 'Face capture is not available in this environment.'

        try:
            # Try different camera indices and backends
            camera_sources = [
                (0, cv2.CAP_DSHOW),
                (0, cv2.CAP_MSMF),
                (0, cv2.CAP_ANY)
            ]

            cap = None
            for cam_idx, api_pref in camera_sources:
                try:
                    cap = cv2.VideoCapture(cam_idx + api_pref)
                    if cap.isOpened():
                        time.sleep(1.0)
                        ret, _ = cap.read()
                        if ret:
                            break
                        cap.release()
                except Exception:
                    if cap:
                        cap.release()

            if not cap or not cap.isOpened():
                return False, 'Could not access any camera.'

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 15)

            success = False
            message = ''

            try:
                window_name = 'Capture Face - Press SPACE to take a photo or Q to quit'
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                while True:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        continue
                    cv2.imshow(window_name, frame)
                    key = cv2.waitKey(10) & 0xFF
                    if key == ord('q') or cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                        message = 'Face capture cancelled.'
                        break
                    if key == 32:
                        if not os.path.exists('faces'):
                            os.makedirs('faces')
                        filename = f"faces/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        cv2.imwrite(filename, frame)
                        success, message = self.add_new_face(filename, name)
                        break
            finally:
                try:
                    if 'window_name' in locals():
                        cv2.destroyWindow(window_name)
                    if cap and cap.isOpened():
                        cap.release()
                    cv2.destroyAllWindows()
                except Exception:
                    pass

            return success, message
        except Exception as e:
            return False, str(e)
