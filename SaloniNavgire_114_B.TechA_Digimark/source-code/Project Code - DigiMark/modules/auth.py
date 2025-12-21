import bcrypt
from modules.database import teachers_collection
from datetime import datetime

class AuthManager:
    
    @staticmethod
    def hash_password(password):
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt(rounds=10)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password, hashed_password):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    @staticmethod
    def register_teacher(email, full_name, password, school_name, subject):
        """Register a new teacher"""
        try:
            # Check if teacher already exists
            existing_teacher = teachers_collection.find_one({'email': email})
            if existing_teacher:
                return False, "Email already registered"
            
            # Hash password
            hashed_password = AuthManager.hash_password(password)
            
            # Create teacher document
            teacher_data = {
                'email': email,
                'full_name': full_name,
                'password': hashed_password,
                'school_name': school_name,
                'subject': subject,
                'created_at': datetime.utcnow(),
                'is_active': True,
                'evaluations_count': 0
            }
            
            # Insert into database
            result = teachers_collection.insert_one(teacher_data)
            return True, "Registration successful"
        
        except Exception as e:
            return False, f"Registration error: {str(e)}"
    
    @staticmethod
    def login_teacher(email, password):
        """Login teacher with email and password"""
        try:
            teacher = teachers_collection.find_one({'email': email})
            
            if not teacher:
                return False, None, "Email not registered"
            
            if not teacher['is_active']:
                return False, None, "Account is inactive"
            
            if not AuthManager.verify_password(password, teacher['password']):
                return False, None, "Incorrect password"
            
            return True, teacher, "Login successful"
        
        except Exception as e:
            return False, None, f"Login error: {str(e)}"
    
    @staticmethod
    def get_teacher_by_id(teacher_id):
        """Get teacher details by MongoDB ObjectId"""
        try:
            from bson.objectid import ObjectId
            teacher = teachers_collection.find_one({'_id': ObjectId(teacher_id)})
            return teacher
        except Exception as e:
            return None
    
    @staticmethod
    def update_teacher_evaluations(teacher_id):
        """Increment evaluations count for teacher"""
        try:
            from bson.objectid import ObjectId
            teachers_collection.update_one(
                {'_id': ObjectId(teacher_id)},
                {'$inc': {'evaluations_count': 1}}
            )
        except Exception as e:
            print(f"Error updating evaluations: {e}")

