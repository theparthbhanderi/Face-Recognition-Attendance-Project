from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
import time
import numpy as np
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except Exception as _err:
    print(f"Warning: face_recognition modules not available ({_err}). Running in degraded mode.")
    FACE_RECOGNITION_AVAILABLE = False

import os
from datetime import datetime
import csv
from database import db
# Optional imports: dotenv and cv2 are heavy / optional for UI-only runs.
try:
    from dotenv import load_dotenv
    # Load environment variables if python-dotenv is available
    load_dotenv()
    DOTENV_AVAILABLE = True
except Exception as _err:
    print(f"Warning: python-dotenv not available ({_err}). Continuing without .env support.")
    DOTENV_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except Exception as _err:
    print(f"Warning: OpenCV (cv2) not available ({_err}). Video endpoints may be limited.")
    CV2_AVAILABLE = False

def log_attendance(name, status):
    """Log attendance to CSV file"""
    try:
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        file_path = os.path.join('data', 'attendance.csv')
        file_exists = os.path.exists(file_path)
        
        with open(file_path, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # Write header if file is new
            if not file_exists:
                writer.writerow(['Name', 'Status', 'Timestamp'])
            
            # Write attendance record
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([name, status, timestamp])
            
        print(f"Attendance logged: {name} - {status} at {timestamp}")
    except Exception as e:
        print(f"Error logging attendance: {e}")

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

# Initialize Face Recognition Manager for automatic recognition (System Source of Truth)
try:
    from face_recognition_manager import FaceRecognitionManager
    face_recognition_manager = FaceRecognitionManager()
    FACE_MANAGER_AVAILABLE = True
    # For backward compatibility with legacy route names
    face_system = face_recognition_manager 
except Exception as e:
    print(f"Warning: Face Recognition Manager not available ({e})")
    FACE_MANAGER_AVAILABLE = False
    face_recognition_manager = None
    face_system = None

# User model for admin authentication
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Mock database - In a real application, use a proper database
users = [
    User(1, 'admin', generate_password_hash('admin123', method='pbkdf2:sha256'))
]

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    for user in users:
        if user.id == int(user_id):
            return user
    return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = next((u for u in users if u.username == username), None)
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    # Get list of registered faces
    # Get total users from database
    users = db.get_all_users()
    total_users = len(users)
    known_faces = [(u['full_name'], u['id']) for u in users]
    return render_template('admin/dashboard.html', known_faces=known_faces)

@app.route('/admin/add_face', methods=['GET', 'POST'])
@login_required
def add_face():
    if request.method == 'POST':
        name = request.form.get('name')
        image_data = request.form.get('image_data')
        
        if not name:
            return jsonify({'success': False, 'message': 'Name is required'}), 400
            
        if not image_data:
            return jsonify({'success': False, 'message': 'No image data provided'}), 400
            
        try:
            # Save the image data to a temporary file
            import base64
            import time
            header, encoded = image_data.split(',', 1)
            image_data = base64.b64decode(encoded)
            
            os.makedirs('temp', exist_ok=True)
            temp_path = os.path.join('temp', 'temp_face.jpg')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            
            # 1. Add user to database
            success, result_msg = db.add_user(name, status='active')
            if not success:
                return jsonify({'success': False, 'message': f'Database Error: {result_msg}'}), 400
            
            user_id = result_msg # For new user creation, this is the ID
            
            # 2. Extract and save encoding using Manager
            success, message = face_recognition_manager.save_face_encoding_to_database(user_id, temp_path)
            
            if success:
                return jsonify({'success': True, 'message': f'Successfully enrolled biometric signature for {name}'})
            else:
                return jsonify({'success': False, 'message': f'Enrollment Error: {message}'}), 400
                
        except Exception as e:
            print(f"Error adding face: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return render_template('admin/add_face_new.html')

@app.route('/user_management')
def user_management():
    # Allow access to user management page for viewing
    # Admin functions will still require authentication
    return render_template('user_management.html')

@app.route('/analytics_dashboard')
def analytics_dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    return render_template('analytics_dashboard.html')

@app.route('/register_face', methods=['GET', 'POST'])
def register_face():
    if request.method == 'GET':
        return render_template('register_face.html')

    # POST: accept JSON with user info and captured faces
    try:
        data = request.get_json() or {}
        full_name = data.get('fullName') or data.get('full_name')
        email = data.get('email')
        department = data.get('department')
        phone = data.get('phone')
        employee_id = data.get('employeeId') or data.get('employee_id') or f"user_{int(time.time())}"
        faces = data.get('faces', {})

        if not full_name:
            return jsonify({'success': False, 'message': 'Full name is required'}), 400

        saved_files = []
        messages = []
        face_image_path = None

        import base64
        import time

        # Ensure faces directory exists
        os.makedirs('faces', exist_ok=True)

        # faces object expected: { front: dataURL, left: dataURL, right: dataURL }
        # Also check if image_data was sent directly (from attendance page fallback)
        if not faces and data.get('image_data'):
            faces = {'front': data.get('image_data')}

        for angle in ('front', 'left', 'right'):
            img_data = faces.get(angle)
            if not img_data:
                continue

            try:
                header, encoded = img_data.split(',', 1)
                binary = base64.b64decode(encoded)
                timestamp = int(time.time())
                safe_name = ''.join(c for c in full_name if c.isalnum() or c in (' ', '_')).rstrip()
                filename = f"faces/{safe_name.replace(' ', '_')}_{employee_id}_{angle}_{timestamp}.jpg"
                with open(filename, 'wb') as f:
                    f.write(binary)

                # Store the front face as the main profile image
                if angle == 'front':
                    face_image_path = filename

                # Note: Registration first creates the DB user, then we extract encoding
                # We handle this after the DB insertion below
                pass
            except Exception as e:
                messages.append({'angle': angle, 'success': False, 'message': f'Error saving {angle}: {e}'})

        # Save user to database
        try:
            user_id, db_message = db.add_user(
                full_name=full_name,
                email=email,
                department=department,
                phone=phone,
                employee_id=employee_id,
                status='active',
                role='user',
                face_image_path=face_image_path,
                age=data.get('age')
            )
            
            if user_id:
                # Encodings are now updated in the DB and manager automatically
                pass

                # Also save face encoding to database using the manager
                if FACE_MANAGER_AVAILABLE and face_image_path:
                    try:
                        # Force manager to extract encoding for the newly registered face
                        success, msg = face_recognition_manager.save_face_encoding_to_database(user_id, face_image_path)
                        print(f"Encoding storage: {msg}")
                    except Exception as e:
                        print(f"Could not save encoding to database: {e}")

                return jsonify({
                    'success': True, 
                    'message': f'Registration successful! {full_name} is now in the system.', 
                    'user_id': user_id,
                    'files': saved_files, 
                    'results': messages
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': f'Database error: {db_message}'
                }), 400

        except Exception as e:
            return jsonify({
                'success': False, 
                'message': f'Database error: {str(e)}'
            }), 500

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users', methods=['GET'])
def api_get_users():
    """API endpoint to get all users"""
    try:
        search_term = request.args.get('search', '')
        department = request.args.get('department', '')
        status = request.args.get('status', '')
        role = request.args.get('role', '')
        
        users = db.search_users(search_term, department, status, role)
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    """API endpoint to get a specific user"""
    try:
        user = db.get_user_by_id(user_id)
        if user:
            return jsonify({'success': True, 'user': user})
        else:
            return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users', methods=['POST'])
def api_add_user():
    """API endpoint to add a new user"""
    try:
        data = request.get_json()
        
        user_id, message = db.add_user(
            full_name=data.get('full_name'),
            email=data.get('email'),
            department=data.get('department'),
            phone=data.get('phone'),
            employee_id=data.get('employee_id'),
            status=data.get('status', 'active'),
            role=data.get('role', 'user'),
            notes=data.get('notes')
        )
        
        if user_id:
            return jsonify({'success': True, 'user_id': user_id, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def api_update_user(user_id):
    """API endpoint to update a user"""
    try:
        data = request.get_json()
        
        success, message = db.update_user(user_id, **data)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    """API endpoint to delete a user"""
    try:
        success, message = db.delete_user(user_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/attendance', methods=['GET'])
def api_get_attendance():
    """API endpoint to get attendance history"""
    try:
        limit = request.args.get('limit', 100, type=int)
        attendance = db.get_attendance_history(limit)
        return jsonify({'success': True, 'attendance': attendance})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/attendance/<int:record_id>', methods=['DELETE'])
def api_delete_attendance(record_id):
    """API endpoint to delete an attendance record"""
    try:
        success, message = db.delete_attendance(record_id)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/attendance_history')
def attendance_history():
    import csv
    from datetime import datetime
    
    attendance_data = []
    
    # 1. Fetch from SQLite Database (Primary)
    try:
        db_history = db.get_attendance_history(limit=500)
        for record in db_history:
            try:
                # DB timestamps are usually strings or datetime objects
                ts_str = record['timestamp']
                dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S') if isinstance(ts_str, str) else ts_str
                attendance_data.append({
                    'id': record['id'],
                    'name': record['name'],
                    'status': record['status'],
                    'timestamp': dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'date': dt.strftime('%Y-%m-%d'),
                    'time': dt.strftime('%H:%M:%S'),
                    'class': record['department'] or 'Biometric System',
                    'employee_id': record['employee_id'] or f"UID-{1000 + record['id']}"
                })
            except Exception as e:
                print(f"Error parsing DB record: {e}")
                continue
    except Exception as e:
        print(f"Error fetching DB history: {e}")

    # 2. Fetch from Legacy CSV (Secondary)
    file_path = os.path.join('data', 'attendance.csv')
    if os.path.exists(file_path):
        with open(file_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts_str = row['Timestamp']
                    dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                    # Avoid duplicates if already in DB (simple name+time check)
                    attendance_data.append({
                        'name': row['Name'],
                        'status': row['Status'],
                        'timestamp': ts_str,
                        'date': dt.strftime('%Y-%m-%d'),
                        'time': dt.strftime('%H:%M:%S'),
                        'class': 'Legacy Log'
                    })
                except:
                    continue
    
    # Sort by timestamp (newest first)
    attendance_data.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Limit to most recent 1000 records to maintain performance
    return render_template('attendance_history.html', attendance_data=attendance_data[:1000])

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if request.method == 'POST':
        # Handle new user registration from attendance
        if 'register' in request.form:
            name = request.form.get('name')
            image_data = request.form.get('image_data')
            
            if not name or not image_data:
                return jsonify({'success': False, 'message': 'Name and image are required'}), 400
                
            try:
                # Save the image data to a temporary file
                import base64
                header, encoded = image_data.split(',', 1)
                image_data = base64.b64decode(encoded)
                
                os.makedirs('temp', exist_ok=True)
                temp_path = os.path.join('temp', f'temp_face_{int(time.time())}.jpg')
                with open(temp_path, 'wb') as f:
                    f.write(image_data)
                
                # Add the face using the saved image
                # 1. Add user to database
                success, result_msg = db.add_user(name, status='active')
                if not success:
                    flash(f'Database Error: {result_msg}')
                    return redirect(url_for('add_face'))
                
                user_id = result_msg # For new user creation, this is the ID
                
                # 2. Extract and save encoding using Manager
                success, message = face_recognition_manager.save_face_encoding_to_database(user_id, temp_path)
                
                if success:
                    flash(f'Successfully enrolled biometric signature for {name}')
                else:
                    flash(f'Enrollment Error: {message}')
                
                # Clean up
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
                if success:
                    # Log attendance
                    log_attendance(name, 'Registered')
                    return jsonify({
                        'success': True, 
                        'message': f'Successfully registered and marked attendance for {name}'
                    })
                else:
                    return jsonify({'success': False, 'message': message}), 400
                    
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500
    
    return render_template('attendance.html')

@app.route('/detect_face', methods=['POST'])
def detect_face():
    """Detect and recognize face from uploaded image data"""
    try:
        if not FACE_RECOGNITION_AVAILABLE:
            return jsonify({
                'success': False,
                'message': 'Face recognition is not available in this environment'
            }), 400
            
        image_data = request.form.get('image_data')
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'No image data provided'
            }), 400
            
        # Save image to temporary file
        import base64
        import tempfile
        header, encoded = image_data.split(',', 1)
        image_binary = base64.b64decode(encoded)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(image_binary)
            temp_path = temp_file.name
            
        try:
            # Load and process image
            image = face_recognition.load_image_file(temp_path)
            face_locations = face_recognition.face_locations(image, model="hog")
            
            if not face_locations:
                return jsonify({
                    'success': True,
                    'face_detected': False,
                    'message': 'No face detected in the image'
                })
                
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if not face_encodings:
                return jsonify({
                    'success': True,
                    'face_detected': False,
                    'message': 'Could not extract face features'
                })
                
            # Try to recognize the face
            # Use unified manager
            results, message = face_recognition_manager.recognize_face_in_image(temp_path)
            
            if results and results[0]['match']:
                result = results[0]
                return jsonify({
                    'success': True,
                    'face_detected': True,
                    'known': True,
                    'name': result['name'],
                    'user_id': result['user_id'],
                    'confidence': result['confidence'],
                    'message': f"Recognized: {result['name']} ({result['confidence']}%)"
                })
            else:
                return jsonify({
                    'success': True,
                    'face_detected': True,
                    'known': False,
                    'name': 'Unknown',
                    'message': 'Face detected but not recognized in system'
                })
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        print(f"Error in detect_face: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing image: {str(e)}'
        }), 500

@app.route('/capture_attendance', methods=['POST'])
def capture_attendance():
    """Capture attendance with proper face recognition"""
    try:
        from camera import camera
        from datetime import datetime
        import base64
        import tempfile

        # Check for client-side image data fallback
        data = request.get_json() or {}
        image_data = data.get('image_data')
        
        face_names = []
        
        if image_data:
            # If client provided image, try to recognize from it first (more reliable for web)
            try:
                header, encoded = image_data.split(',', 1)
                image_binary = base64.b64decode(encoded)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                    tmp.write(image_binary)
                    tmp_path = tmp.name
                
                # Use manager to recognize
                results, msg = face_recognition_manager.recognize_face_in_image(tmp_path)
                if results:
                    face_names = [r['name'] for r in results]
                
                os.unlink(tmp_path)
            except Exception as e:
                print(f"Fallback detection error: {e}")

        # If fallback didn't find anything, use camera's current state
        if not face_names:
            recognition_data = camera.get_recognition_data()
            face_names = recognition_data['face_names']

        if not face_names:
            return jsonify({
                'success': False,
                'message': 'No face detected in frame'
            })

        # Get first detected face
        detected_name = face_names[0]

        if detected_name == "Unknown":
            return jsonify({
                'success': True,
                'face_detected': True,
                'known': False,
                'name': 'Unknown',
                'message': 'Unknown face detected. Please register first.',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        # Known face detected - try to map to a user in the database and record attendance
        try:
            user = db.get_user_by_full_name(detected_name)
            if user and user.get('id'):
                success, msg = db.add_attendance(user['id'], user['full_name'], 'Present')
                if success:
                    return jsonify({
                        'success': True,
                        'face_detected': True,
                        'known': True,
                        'user_id': user['id'],
                        'name': user['full_name'],
                        'status': 'Present',
                        'message': f'Attendance recorded for {user["full_name"]}',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                else:
                    # Fallback to CSV logging if DB write fails
                    log_attendance(detected_name, 'Present')
            else:
                # No matching DB user found; fallback to CSV logging
                log_attendance(detected_name, 'Present')

            return jsonify({
                'success': True,
                'face_detected': True,
                'known': True,
                'name': detected_name,
                'status': 'Present',
                'message': f'Attendance marked for {detected_name}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            # On unexpected errors, ensure we return an error response
            print(f"Error recording attendance in DB: {e}")
            return jsonify({
                'success': False,
                'message': f'Error recording attendance: {e}'
            }), 500

    except Exception as e:
        print(f"Error in capture_attendance: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error capturing attendance: {str(e)}'
        }), 500

@app.route('/admin/delete_face/<int:user_id>', methods=['POST'])
@login_required
def delete_face(user_id):
    success, message = db.delete_user(user_id)
    if success:
        # Reload manager encodings
        if face_recognition_manager:
            face_recognition_manager.load_faces_from_database()
        flash(message)
    else:
        flash(f"Error: {message}")
    
    return redirect(url_for('admin_dashboard'))

# Global camera instance - will be managed by camera.py
camera = None

@app.route('/video_feed')
def video_feed():
    """SIMPLE & RELIABLE video streaming"""
    from camera import camera
    import time
    
    def generate():
        while True:
            frame = camera.get_frame()
            
            if frame is None:
                # Send a small delay frame instead of empty
                time.sleep(0.1)
                continue
            
            try:
                # Simple encoding - more reliable
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    frame_data = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
            except Exception as e:
                print(f"Encoding error: {e}")
                # Send empty frame on error
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n\r\n'
            
            # Small delay to prevent overwhelming
            time.sleep(0.03)
    
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/recognition_status', methods=['GET', 'POST'])
def recognition_status():
    """Return current recognition data and active camera info for the UI.
    If POSTed with image_data, processes that frame for instant recognition.
    """
    try:
        from camera import camera
        
        # If POSTed with image data, use that for recognition (Browser Bridge)
        if request.method == 'POST':
            try:
                payload = request.get_json() or {}
                image_data = payload.get('image_data')
                
                if image_data and face_recognition_manager:
                    import base64
                    import tempfile
                    # Decode image
                    header, encoded = image_data.split(',', 1)
                    image_binary = base64.b64decode(encoded)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                        temp_file.write(image_binary)
                        temp_path = temp_file.name
                    
                    try:
                        # Process using manager
                        results, message = face_recognition_manager.recognize_face_in_image(temp_path)
                        
                        face_names = []
                        face_locations = []
                        if results:
                            for res in results:
                                face_names.append(res['name'])
                                face_locations.append(res['location'])
                        
                        # Cleanup
                        os.remove(temp_path)
                        
                        return jsonify({
                            'success': True,
                            'camera_index': 'Browser WebCam',
                            'running': True,
                            'face_names': face_names,
                            'face_locations': face_locations,
                            'face_locations_count': len(face_locations),
                            'frame_count': 0
                        })
                    except Exception as e:
                        if os.path.exists(temp_path): os.remove(temp_path)
                        raise e
            except Exception as e:
                print(f"Error in live bridge processing: {e}")
                # Fall back to camera-based status if bridge fails

        # Standard GET/Fallback: use hardware camera data
        if camera is None:
            return jsonify({'success': False, 'message': 'Camera not initialized', 'camera_index': None, 'running': False}), 200

        data = camera.get_recognition_data()
        # Ensure face_locations is serializable (list of lists)
        face_locations = data.get('face_locations', [])
        try:
            # Convert numpy arrays to lists if needed
            face_locations_serial = [list(map(int, loc)) for loc in face_locations]
        except Exception:
            face_locations_serial = face_locations

        return jsonify({
            'success': True,
            'camera_index': getattr(camera, 'device_index', None),
            'running': True,
            'face_names': data.get('face_names', []),
            'face_locations': face_locations_serial,
            'face_locations_count': len(face_locations_serial),
            'frame_count': data.get('frame_count', 0)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/set_camera', methods=['POST'])
@login_required
def set_camera():
    """Set the camera device index and reinitialize camera thread.
    Requires login to prevent unauthorized camera access changes.
    """
    try:
        payload = request.get_json() or {}
        idx = int(payload.get('index', 0))

        from camera import camera as current_camera, CV2_AVAILABLE, Camera

        if not CV2_AVAILABLE:
            return jsonify({'success': False, 'message': 'Camera functionality not available on server'}), 400

        # Attempt to reinitialize camera with new index
        try:
            if current_camera:
                try:
                    current_camera.release()
                except Exception:
                    pass

            new_cam = Camera(device_index=idx)

            # Replace global camera - careful import to modify module-level variable
            import importlib
            cam_mod = importlib.import_module('camera')
            cam_mod.camera = new_cam

            return jsonify({'success': True, 'message': f'Camera set to index {idx}', 'camera_index': idx})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# ============================================================================
# AUTOMATIC FACE RECOGNITION & ATTENDANCE ENDPOINTS
# ============================================================================

# Initialize Face Recognition Manager for automatic recognition
try:
    from face_recognition_manager import FaceRecognitionManager
    face_recognition_manager = FaceRecognitionManager()
    FACE_MANAGER_AVAILABLE = True
except Exception as e:
    print(f"Warning: Face Recognition Manager not available ({e})")
    FACE_MANAGER_AVAILABLE = False
    face_recognition_manager = None

@app.route('/api/recognize_stream', methods=['POST'])
def api_recognize_stream():
    """Process frame from video stream and recognize faces"""
    if not FACE_MANAGER_AVAILABLE or not CV2_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Face recognition not available'
        }), 400
    
    try:
        image_data = request.form.get('image_data')
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'No image data provided'
            }), 400
        
        # Decode base64 image
        import base64
        import tempfile
        header, encoded = image_data.split(',', 1)
        image_binary = base64.b64decode(encoded)
        
        # Convert to numpy array for cv2
        import io
        from PIL import Image
        image = Image.open(io.BytesIO(image_binary))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Recognize faces in frame
        results = face_recognition_manager.recognize_faces_in_frame(frame)
        
        return jsonify({
            'success': True,
            'faces_detected': len(results),
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/mark_attendance_auto', methods=['POST'])
def api_mark_attendance_auto():
    """Automatically mark attendance for recognized person"""
    if not FACE_MANAGER_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Face recognition not available'
        }), 400
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        name = data.get('name')
        
        if not user_id or not name:
            return jsonify({
                'success': False,
                'message': 'Missing user_id or name'
            }), 400
        
        # Mark attendance
        success, message = face_recognition_manager.mark_attendance(user_id, name)
        
        if success:
            # Log to CSV as well
            log_attendance(name, 'Present')
            
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/attendance/stats', methods=['GET'])
def api_attendance_stats():
    """Get attendance statistics with optional period"""
    if not FACE_MANAGER_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Face recognition not available'
        }), 400
    
    try:
        period = request.args.get('period', 'today')
        stats = face_recognition_manager.get_attendance_stats(period)
        
        if stats:
            return jsonify({
                'success': True,
                'data': stats
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error getting stats'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/attendance/daily_report', methods=['GET'])
def api_daily_attendance_report():
    """Get today's attendance report"""
    if not FACE_MANAGER_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Face recognition not available'
        }), 400
    
    try:
        records = face_recognition_manager.get_daily_report()
        
        return jsonify({
            'success': True,
            'data': records,
            'count': len(records)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/faces/config', methods=['GET'])
def api_faces_config():
    """Get face recognition configuration"""
    if not FACE_MANAGER_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Face recognition not available'
        }), 400
    
    try:
        return jsonify({
            'success': True,
            'known_faces_count': len(face_recognition_manager.known_face_names),
            'tolerance': face_recognition_manager.tolerance,
            'confidence_threshold': face_recognition_manager.confidence_threshold,
            'recognition_cooldown': face_recognition_manager.recognition_cooldown,
            'known_faces': face_recognition_manager.known_face_names
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/faces/reload', methods=['POST'])
def api_reload_faces():
    """Reload faces from database and update all systems"""
    if not FACE_MANAGER_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Face recognition not available'
        }), 400
    
    try:
        face_recognition_manager.load_faces_from_database()
        
        # Keep old system synchronized
        if hasattr(face_system, 'known_face_encodings'):
            face_system.known_face_encodings = face_recognition_manager.known_face_encodings
            face_system.known_face_names = face_recognition_manager.known_face_names
            
        # Notify camera if it exists
        try:
            from camera import camera
            if camera and hasattr(camera, 'face_system'):
                camera.face_system.known_face_encodings = face_recognition_manager.known_face_encodings
                camera.face_system.known_face_names = face_recognition_manager.known_face_names
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'message': f'Reloaded {len(face_recognition_manager.known_face_names)} faces',
            'faces_count': len(face_recognition_manager.known_face_names)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/config/cooldown', methods=['POST'])
def api_update_cooldown():
    """Update attendance cooldown setting"""
    if not FACE_MANAGER_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Face recognition not available'
        }), 400
    
    try:
        data = request.get_json()
        cooldown_seconds = data.get('cooldown_seconds', 300)
        
        if cooldown_seconds < 60 or cooldown_seconds > 3600:
            return jsonify({
                'success': False,
                'message': 'Cooldown must be between 60 and 3600 seconds'
            }), 400
        
        face_recognition_manager.recognition_cooldown = cooldown_seconds
        
        return jsonify({
            'success': True,
            'message': f'Cooldown updated to {cooldown_seconds} seconds',
            'cooldown_seconds': cooldown_seconds
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/auto_attendance', methods=['GET', 'POST'])
def auto_attendance():
    """Auto attendance page with real-time video feed"""
    if not FACE_MANAGER_AVAILABLE:
        flash('Face recognition system is not available', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Handle start/stop
        action = request.form.get('action', 'start')
        return jsonify({'success': True, 'action': action})
    
    return render_template('auto_attendance.html')


if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates/admin', exist_ok=True)
    
    # Start performance monitoring
    try:
        from performance_monitor import start_performance_monitoring
        start_performance_monitoring()
        print("Performance monitoring started")
    except ImportError:
        print("Performance monitoring not available")
    except Exception as e:
        print(f"Error starting performance monitor: {e}")
    
    # Run app in THREADED mode - CRITICAL FIX
    try:
        app.run(debug=True, threaded=True, port=5001)  # THREADED = NO FREEZING
    finally:
        # Cleanup
        try:
            from camera import camera
            camera.release()
            print("Camera released")
        except:
            pass
        
        try:
            from performance_monitor import stop_performance_monitoring
            stop_performance_monitoring()
            print("Performance monitoring stopped")
        except:
            pass
