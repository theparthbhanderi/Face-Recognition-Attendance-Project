from database import db

users = db.get_all_users()
print('=== REGISTERED USERS IN DATABASE ===')
for u in users:
    print(f'ID: {u["id"]}')
    print(f'Name: {u["full_name"]}')
    print(f'Email: {u["email"]}')
    print(f'Department: {u["department"]}')
    print(f'Employee ID: {u["employee_id"]}')
    print(f'Status: {u["status"]}')
    print(f'Role: {u["role"]}')
    print(f'Photo: {u["face_image_path"]}')
    print(f'Registered: {u["registered_at"]}')
    print('---')
