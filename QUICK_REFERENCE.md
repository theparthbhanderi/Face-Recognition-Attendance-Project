# Quick Reference - Face Recognition Implementation

## 🔍 Core Components

### 1. FaceRecognitionManager Class

```python
from face_recognition_manager import FaceRecognitionManager

# Initialize
manager = FaceRecognitionManager()

# Load all faces from database
manager.load_faces_from_database()

# Recognize face in image
results, message = manager.recognize_face_in_image('path/to/image.jpg')

# Recognize faces in video frame
results = manager.recognize_faces_in_frame(frame)

# Mark attendance
success, message = manager.mark_attendance(user_id, name)

# Get stats
stats = manager.get_attendance_stats()

# Get daily report
report = manager.get_daily_report()
```

### 2. Save Face Encoding to Database

```python
# When registering a new user
user_id = 123
image_path = 'faces/john_doe.jpg'

success, msg = manager.save_face_encoding_to_database(user_id, image_path)

# The encoding is now stored in users.face_encoding_data
# Next time system starts, it will automatically load this face
```

### 3. Adjust Recognition Settings

```python
# Stricter matching (lower tolerance = more strict)
manager.tolerance = 0.4  # Default: 0.5

# Higher confidence requirement
manager.confidence_threshold = 0.75  # Default: 0.6 (60%)

# Change cooldown between markings
manager.recognition_cooldown = 120  # seconds, Default: 60

# Reload after changes
manager.load_faces_from_database()
```

---

## 🌐 API Endpoints Reference

### Real-time Recognition
```javascript
// Send video frame for recognition
const imageData = canvas.toDataURL('image/jpeg');

fetch('/api/recognize_stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'image_data=' + encodeURIComponent(imageData)
}).then(res => res.json()).then(data => {
    console.log(data.results);
    // Example result:
    // {
    //   name: "John Doe",
    //   confidence: 95.5,
    //   known: true,
    //   user_id: 123,
    //   location: [top, right, bottom, left]
    // }
});
```

### Mark Attendance
```javascript
fetch('/api/mark_attendance_auto', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        user_id: 123,
        name: 'John Doe'
    })
}).then(res => res.json())
.then(data => {
    if (data.success) {
        console.log('Attendance marked!');
    }
});
```

### Get Statistics
```javascript
fetch('/api/attendance/stats')
    .then(res => res.json())
    .then(data => {
        console.log(data.data);
        // {
        //   total_entries: 45,
        //   unique_users: 18,
        //   today_present: [array of names],
        //   known_faces_count: 25
        // }
    });
```

### Get Daily Report
```javascript
fetch('/api/attendance/daily_report')
    .then(res => res.json())
    .then(data => {
        // Array of attendance records:
        // {
        //   user_id: 123,
        //   name: 'John Doe',
        //   status: 'Present',
        //   time: '2024-01-15T09:30:45'
        // }
        data.data.forEach(record => {
            console.log(`${record.name} - ${record.time}`);
        });
    });
```

### Reload Faces
```javascript
fetch('/api/faces/reload', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
        console.log(`Reloaded ${data.faces_count} faces`);
    });
```

### Get Configuration
```javascript
fetch('/api/faces/config')
    .then(res => res.json())
    .then(data => {
        console.log(`Known faces: ${data.known_faces_count}`);
        console.log(`Tolerance: ${data.tolerance}`);
        console.log(`Confidence threshold: ${data.confidence_threshold}`);
    });
```

---

## 🎬 Video Processing Example

```javascript
// Complete real-time recognition example
let video = document.getElementById('video');
let canvas = document.getElementById('canvas');
let ctx = canvas.getContext('2d');

async function processVideo() {
    // Draw current frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Send for recognition (every 3rd frame for performance)
    if (frameCount % 3 === 0) {
        const imageData = canvas.toDataURL('image/jpeg');
        
        try {
            const response = await fetch('/api/recognize_stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'image_data=' + encodeURIComponent(imageData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Draw boxes around detected faces
                result.results.forEach(face => {
                    const [top, right, bottom, left] = face.location;
                    
                    // Draw rectangle
                    const color = face.known ? '#27ae60' : '#e74c3c';
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 3;
                    ctx.strokeRect(left, top, right - left, bottom - top);
                    
                    // Draw label
                    ctx.fillStyle = color;
                    ctx.fillRect(left, bottom - 30, right - left, 30);
                    ctx.fillStyle = 'white';
                    ctx.font = 'bold 14px Arial';
                    ctx.fillText(`${face.name} (${face.confidence}%)`, 
                                 (left + right) / 2, bottom - 10);
                    
                    // Auto-mark if known
                    if (face.known && face.user_id) {
                        markAttendance(face.user_id, face.name);
                    }
                });
            }
        } catch (error) {
            console.error('Recognition error:', error);
        }
    }
    
    frameCount++;
    requestAnimationFrame(processVideo);
}

// Start processing
processVideo();
```

---

## 💾 Database Queries

### Get User with Face Encoding
```python
from database import Database

db = Database()
conn = db.get_connection()
cursor = conn.cursor()

# Get user with face encoding
cursor.execute('''
    SELECT id, full_name, face_encoding_data
    FROM users
    WHERE id = ? AND status = 'active'
''', (user_id,))

user_id, name, encoding_json = cursor.fetchone()

# Decode encoding
import json
import numpy as np
encoding = np.array(json.loads(encoding_json))

conn.close()
```

### Get Today's Attendance
```python
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')

cursor.execute('''
    SELECT name, status, COUNT(*) as count
    FROM attendance
    WHERE DATE(timestamp) = ?
    GROUP BY name, status
''', (today,))

for row in cursor.fetchall():
    name, status, count = row
    print(f'{name}: {count} entries')
```

### Get Attendance for Date Range
```python
from datetime import datetime, timedelta

start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
end_date = datetime.now().strftime('%Y-%m-%d')

cursor.execute('''
    SELECT DATE(timestamp), COUNT(DISTINCT user_id)
    FROM attendance
    WHERE DATE(timestamp) BETWEEN ? AND ?
    GROUP BY DATE(timestamp)
    ORDER BY DATE(timestamp)
''', (start_date, end_date))

for row in cursor.fetchall():
    date, count = row
    print(f'{date}: {count} users')
```

---

## 🎯 Custom Implementation Example

```python
from face_recognition_manager import FaceRecognitionManager
from database import Database

# Initialize
manager = FaceRecognitionManager()
db = Database()

# Example: Process attendance report for specific department
department = 'Engineering'

# Get all users in department
conn = db.get_connection()
cursor = conn.cursor()

cursor.execute('''
    SELECT id, full_name FROM users WHERE department = ? AND status = 'active'
''', (department,))

users = cursor.fetchall()

# Get today's attendance
today = datetime.now().strftime('%Y-%m-%d')
cursor.execute('''
    SELECT DISTINCT user_id FROM attendance
    WHERE DATE(timestamp) = ?
''', (today,))

present_user_ids = [row[0] for row in cursor.fetchall()]

# Generate report
print(f"Department: {department}")
print(f"Date: {today}")
print(f"Total Users: {len(users)}")
print(f"Present: {len(present_user_ids)}")
print(f"Absent: {len(users) - len(present_user_ids)}")

print("\nPresent:")
for user_id, name in users:
    if user_id in present_user_ids:
        print(f"  ✓ {name}")

print("\nAbsent:")
for user_id, name in users:
    if user_id not in present_user_ids:
        print(f"  ✗ {name}")

conn.close()
```

---

## 📊 HTML Dashboard Example

```html
<!-- Real-time stats board -->
<div class="dashboard">
    <h2>Automatic Attendance</h2>
    
    <div class="stats">
        <div class="stat">
            <span class="number" id="total">0</span>
            <span class="label">Total Marked</span>
        </div>
        <div class="stat">
            <span class="number" id="unique">0</span>
            <span class="label">Unique Users</span>
        </div>
    </div>
    
    <div id="live-feed"></div>
</div>

<script>
    // Auto-refresh stats
    setInterval(async () => {
        const res = await fetch('/api/attendance/stats');
        const data = await res.json();
        
        if (data.success) {
            document.getElementById('total').textContent = data.data.total_entries;
            document.getElementById('unique').textContent = data.data.unique_users;
        }
    }, 5000); // Refresh every 5 seconds
</script>
```

---

## 🔧 Configuration Adjustments

### For High-Security (Strict Matching)
```python
manager.tolerance = 0.3          # Very strict
manager.confidence_threshold = 0.8  # Require 80%
manager.recognition_cooldown = 300  # 5 minutes
```

### For High-Speed (Lenient Matching)
```python
manager.tolerance = 0.6          # More lenient
manager.confidence_threshold = 0.5  # Require 50%
manager.recognition_cooldown = 30   # 30 seconds
```

### Balanced (Recommended)
```python
manager.tolerance = 0.5          # Default
manager.confidence_threshold = 0.6  # 60%
manager.recognition_cooldown = 60   # 1 minute
```

---

## 🚀 Performance Optimization

```python
# Process only every nth frame
frame_skip = 3  # Process every 3rd frame

# Reduce image size for faster processing
scale_factor = 0.25

# Use faster model
model = 'hog'  # vs 'cnn' (slower but more accurate)

# In recognize_faces_in_frame():
# small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
# face_locations = face_recognition.face_locations(small_frame, model=model)
```

---

## 📝 Testing Checklist

- [ ] Database initialized with users table
- [ ] Face images saved in `faces/` directory
- [ ] Face encodings stored in database
- [ ] Real-time video feed displays correctly
- [ ] Faces detected and shown with boxes
- [ ] Confidence scores calculated properly
- [ ] Attendance marked correctly
- [ ] Statistics updated in real-time
- [ ] Daily report generates correctly
- [ ] Cooldown preventing duplicate marking
- [ ] API endpoints responding properly
- [ ] CSV logs being created

---

This reference should cover most use cases!
