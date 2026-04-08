"""
Enhanced Face Recognition Manager with Automatic Attendance
Handles face recognition, database integration, and attendance logging
"""

import numpy as np
import json
from datetime import datetime, timedelta
from database import Database
import threading
import time

try:
    import face_recognition
    import cv2
    FACE_RECOGNITION_AVAILABLE = True
except Exception as e:
    print(f"Warning: Face recognition not available ({e}). Running in basic mode.")
    FACE_RECOGNITION_AVAILABLE = False

class FaceRecognitionManager:
    """Manager for face recognition with database integration"""
    
    def __init__(self):
        self.db = Database()
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []  # Store user IDs
        self.known_face_details = {}  # Store full user details
        self.last_recognized = {}  # Track last recognition time for each person
        self.recognition_cooldown = 60  # seconds - prevent duplicate attendance
        self.tolerance = 0.6
        self.confidence_threshold = 0.4  # Lowered to 40% for easier initial detection
        
        # Load all faces from database
        self.load_faces_from_database()
        
    def load_faces_from_database(self):
        """Load all face encodings from database"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, full_name, face_encoding_data
                FROM users
                WHERE face_encoding_data IS NOT NULL AND status = 'active'
            ''')
            
            self.known_face_encodings = []
            self.known_face_names = []
            self.known_face_ids = []
            self.known_face_details = {}
            
            for row in cursor.fetchall():
                user_id = row[0]
                name = row[1]
                encoding_json = row[2]
                
                try:
                    # Decode the face encoding
                    encoding = np.array(json.loads(encoding_json))
                    self.known_face_encodings.append(encoding)
                    self.known_face_names.append(name)
                    self.known_face_ids.append(user_id)
                    
                    # Store full user details
                    user = self.db.get_user_by_id(user_id)
                    if user:
                        self.known_face_details[name] = user
                        
                except Exception as e:
                    print(f"Error loading face encoding for {name}: {e}")
                    
            conn.close()
            print(f"Loaded {len(self.known_face_encodings)} faces from database")
            
        except Exception as e:
            print(f"Error loading faces from database: {e}")
    
    def save_face_encoding_to_database(self, user_id, image_path):
        """Extract and save face encoding to database"""
        if not FACE_RECOGNITION_AVAILABLE:
            return False, "Face recognition not available"
        
        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return False, "No face found in image"
            
            # Get the first face's encoding
            face_encoding = face_recognition.face_encodings(image, [face_locations[0]])[0]
            
            # Convert to JSON for storage
            encoding_json = json.dumps(face_encoding.tolist())
            
            # Update database
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET face_encoding_data = ?
                WHERE id = ?
            ''', (encoding_json, user_id))
            
            conn.commit()
            conn.close()
            
            # Reload faces
            self.load_faces_from_database()
            
            return True, "Face encoding saved successfully"
            
        except Exception as e:
            return False, f"Error saving face encoding: {str(e)}"
    
    def recognize_face_in_image(self, image_path):
        """Recognize face in a single image"""
        if not FACE_RECOGNITION_AVAILABLE:
            return None, "Face recognition not available"
        
        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image, model="hog")
            
            if not face_locations:
                return None, "No face detected"
            
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if not face_encodings:
                return None, "Could not extract face features"
            
            results = []
            for face_encoding in face_encodings:
                result = self._match_face_encoding(face_encoding)
                results.append(result)
            
            return results, "Success"
            
        except Exception as e:
            return None, str(e)
    
    def recognize_faces_in_frame(self, frame):
        """Recognize faces in video frame"""
        if not FACE_RECOGNITION_AVAILABLE:
            return []
        
        try:
            # Resize frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Find faces
            face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            results = []
            for face_encoding, face_location in zip(face_encodings, face_locations):
                result = self._match_face_encoding(face_encoding)
                # Scale face location back up
                top, right, bottom, left = face_location
                result['location'] = [int(top*4), int(right*4), int(bottom*4), int(left*4)]
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error in recognize_faces_in_frame: {e}")
            return []
    
    def _match_face_encoding(self, face_encoding):
        """Match a face encoding against known faces"""
        if len(self.known_face_encodings) == 0:
            return {
                'name': 'Unknown',
                'confidence': 0.0,
                'known': False,
                'user_id': None,
                'match': False
            }
        
        # Compare with all known faces
        matches = face_recognition.compare_faces(
            self.known_face_encodings,
            face_encoding,
            tolerance=self.tolerance
        )
        
        face_distances = face_recognition.face_distance(
            self.known_face_encodings,
            face_encoding
        )
        
        # Find best match
        best_match_index = np.argmin(face_distances)
        best_distance = face_distances[best_match_index]
        confidence = 1 - best_distance  # Convert distance to confidence
        
        if matches[best_match_index] and confidence >= self.confidence_threshold:
            name = self.known_face_names[best_match_index]
            user_id = self.known_face_ids[best_match_index]
            
            return {
                'name': name,
                'confidence': round(confidence * 100, 2),
                'known': True,
                'user_id': user_id,
                'match': True
            }
        else:
            return {
                'name': 'Unknown',
                'confidence': 0.0,
                'known': False,
                'user_id': None,
                'match': False
            }
    
    def mark_attendance(self, user_id, name):
        """Mark attendance for recognized person"""
        try:
            # Check if already marked in last N seconds
            if name in self.last_recognized:
                time_since_last = time.time() - self.last_recognized[name]
                if time_since_last < self.recognition_cooldown:
                    return False, f"Already marked. Wait {int(self.recognition_cooldown - time_since_last)}s"
            
            # Record attendance
            success, message = self.db.add_attendance(user_id, name, 'Present')
            
            if success:
                self.last_recognized[name] = time.time()
                print(f"Attendance marked for {name} at {datetime.now()}")
            
            return success, message
            
        except Exception as e:
            return False, f"Error marking attendance: {str(e)}"
    
    def get_attendance_stats(self, period='today'):
        """Get attendance statistics for a specific period"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            date_query = "DATE(timestamp) = DATE('now')"
            if period == 'week':
                date_query = "timestamp >= date('now', '-7 days')"
            elif period == 'month':
                date_query = "timestamp >= date('now', '-30 days')"
            elif period == 'year':
                date_query = "timestamp >= date('now', '-365 days')"
            
            # Count entries
            cursor.execute(f'''
                SELECT COUNT(*), COUNT(DISTINCT user_id)
                FROM attendance
                WHERE {date_query}
            ''')
            
            result = cursor.fetchone()
            total_entries = result[0] if result else 0
            unique_users = result[1] if result else 0
            
            # Get present users for the period
            cursor.execute(f'''
                SELECT DISTINCT name
                FROM attendance
                WHERE {date_query} AND status = 'Present'
                ORDER BY name
            ''', ())
            
            today_present = [row[0] for row in cursor.fetchall()]
            
            # Get trend data (entries per day for the last 7 days)
            cursor.execute('''
                SELECT DATE(timestamp), COUNT(*)
                FROM attendance
                WHERE timestamp >= date('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp)
            ''')
            trend_data = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get department distribution (real data from users table)
            cursor.execute('''
                SELECT u.department, COUNT(a.id)
                FROM attendance a
                JOIN users u ON a.user_id = u.id
                WHERE a.timestamp >= date('now', '-30 days')
                GROUP BY u.department
            ''')
            dept_dist = {row[0] or 'Other': row[1] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                'total_entries': total_entries,
                'unique_users': unique_users,
                'today_present': today_present,
                'known_faces_count': len(self.known_face_encodings),
                'trend_data': trend_data,
                'dept_dist': dept_dist
            }
            
        except Exception as e:
            print(f"Error getting attendance stats: {e}")
            return None
    
    def get_daily_report(self):
        """Get detailed daily attendance report"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            cursor.execute('''
                SELECT user_id, name, status, timestamp
                FROM attendance
                WHERE DATE(timestamp) = ?
                ORDER BY timestamp DESC
            ''', (today,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    'user_id': row[0],
                    'name': row[1],
                    'status': row[2],
                    'time': row[3]
                })
            
            conn.close()
            return records
            
        except Exception as e:
            print(f"Error getting daily report: {e}")
            return []
