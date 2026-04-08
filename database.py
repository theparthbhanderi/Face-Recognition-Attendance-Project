import sqlite3
import os
from datetime import datetime
import json

class Database:
    def __init__(self, db_path='face_recognition.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE,
                department TEXT,
                phone TEXT,
                employee_id TEXT UNIQUE,
                status TEXT DEFAULT 'active',
                role TEXT DEFAULT 'user',
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                face_image_path TEXT,
                face_encoding_data TEXT,
                age INTEGER
            )
        ''')
        
        # Create attendance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"Database initialized at {self.db_path}")
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def add_user(self, full_name, email=None, department=None, phone=None, 
                 employee_id=None, status='active', role='user', notes=None,
                 face_image_path=None, face_encoding_data=None, age=None):
        """Add a new user to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (full_name, email, department, phone, employee_id, 
                               status, role, notes, face_image_path, face_encoding_data, age)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (full_name, email, department, phone, employee_id, 
                   status, role, notes, face_image_path, face_encoding_data, age))
            
            user_id = cursor.lastrowid
            conn.commit()
            return user_id, "User added successfully"
        except sqlite3.IntegrityError as e:
            conn.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            conn.rollback()
            return None, f"Error adding user: {str(e)}"
        finally:
            conn.close()
    
    def get_all_users(self):
        """Get all users from database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, full_name, email, department, phone, employee_id, 
                   status, role, registered_at, notes, face_image_path
            FROM users 
            ORDER BY registered_at DESC
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'full_name': row[1],
                'email': row[2],
                'department': row[3],
                'phone': row[4],
                'employee_id': row[5],
                'status': row[6],
                'role': row[7],
                'registered_at': row[8],
                'notes': row[9],
                'face_image_path': row[10]
            })
        
        conn.close()
        return users
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, full_name, email, department, phone, employee_id, 
                   status, role, registered_at, notes, face_image_path
            FROM users WHERE id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'full_name': row[1],
                'email': row[2],
                'department': row[3],
                'phone': row[4],
                'employee_id': row[5],
                'status': row[6],
                'role': row[7],
                'registered_at': row[8],
                'notes': row[9],
                'face_image_path': row[10]
            }
        return None

    def get_user_by_full_name(self, full_name):
        """Get user by full name (exact match)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, full_name, email, department, phone, employee_id, 
                   status, role, registered_at, notes, face_image_path
            FROM users WHERE full_name = ? LIMIT 1
        ''', (full_name,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row[0],
                'full_name': row[1],
                'email': row[2],
                'department': row[3],
                'phone': row[4],
                'employee_id': row[5],
                'status': row[6],
                'role': row[7],
                'registered_at': row[8],
                'notes': row[9],
                'face_image_path': row[10]
            }
        return None
    
    def update_user(self, user_id, **kwargs):
        """Update user information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build dynamic update query
        update_fields = []
        values = []
        
        for field, value in kwargs.items():
            if field in ['full_name', 'email', 'department', 'phone', 'employee_id', 
                        'status', 'role', 'notes', 'face_image_path']:
                update_fields.append(f"{field} = ?")
                values.append(value)
        
        if not update_fields:
            return False, "No valid fields to update"
        
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        
        try:
            cursor.execute(query, values)
            conn.commit()
            return True, "User updated successfully"
        except Exception as e:
            conn.rollback()
            return False, f"Error updating user: {str(e)}"
        finally:
            conn.close()
    
    def delete_user(self, user_id):
        """Delete user from database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            return True, "User deleted successfully"
        except Exception as e:
            conn.rollback()
            return False, f"Error deleting user: {str(e)}"
        finally:
            conn.close()
    
    def add_attendance(self, user_id, name, status):
        """Add attendance record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO attendance (user_id, name, status)
                VALUES (?, ?, ?)
            ''', (user_id, name, status))
            
            conn.commit()
            return True, "Attendance recorded successfully"
        except Exception as e:
            conn.rollback()
            return False, f"Error recording attendance: {str(e)}"
        finally:
            conn.close()
    
    def delete_attendance(self, record_id):
        """Delete attendance record from database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM attendance WHERE id = ?', (record_id,))
            conn.commit()
            return True, "Attendance record deleted successfully"
        except Exception as e:
            conn.rollback()
            return False, f"Error deleting attendance: {str(e)}"
        finally:
            conn.close()
    
    def get_attendance_history(self, limit=100):
        """Get attendance history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT a.id, a.user_id, a.name, a.status, a.timestamp, u.email, u.department, u.employee_id
            FROM attendance a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        attendance = []
        for row in cursor.fetchall():
            attendance.append({
                'id': row[0],
                'user_id': row[1],
                'name': row[2],
                'status': row[3],
                'timestamp': row[4],
                'email': row[5],
                'department': row[6],
                'employee_id': row[7]
            })
        
        conn.close()
        return attendance
    
    def search_users(self, search_term='', department='', status='', role=''):
        """Search users with filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT id, full_name, email, department, phone, employee_id, 
                   status, role, registered_at, notes, face_image_path
            FROM users WHERE 1=1
        '''
        params = []
        
        if search_term:
            query += ' AND (full_name LIKE ? OR email LIKE ? OR employee_id LIKE ?)'
            params.extend([f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'])
        
        if department:
            query += ' AND department = ?'
            params.append(department)
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        if role:
            query += ' AND role = ?'
            params.append(role)
        
        query += ' ORDER BY registered_at DESC'
        
        cursor.execute(query, params)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'full_name': row[1],
                'email': row[2],
                'department': row[3],
                'phone': row[4],
                'employee_id': row[5],
                'status': row[6],
                'role': row[7],
                'registered_at': row[8],
                'notes': row[9],
                'face_image_path': row[10]
            })
        
        conn.close()
        return users

# Initialize global database instance
db = Database()
