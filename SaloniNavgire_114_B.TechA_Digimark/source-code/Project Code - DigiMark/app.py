from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, session
from flask_session import Session
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import json
import pandas as pd
from datetime import datetime
import uuid
from functools import wraps



# Import custom modules
from modules.ocr_engine import OCREngine
from modules.evaluation_engine import EvaluationEngine
from modules.report_generator import ReportGenerator
from modules.auth import AuthManager
from modules.database import teachers_collection



load_dotenv()



app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'digital_marking_secret_key_change_this')



# Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
Session(app)



# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'txt'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload



app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH



# Create upload directories if they don't exist
os.makedirs(os.path.join(UPLOAD_FOLDER, 'answer_sheets'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'answer_keys'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'results'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'reports'), exist_ok=True)



# Initialize engines
ocr_engine = OCREngine(languages='eng')
evaluation_engine = EvaluationEngine()
report_generator = ReportGenerator(UPLOAD_FOLDER)



# ==================== HELPER FUNCTIONS ====================



def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



def login_required(f):
    """Decorator to check if user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'teacher_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function



def calculate_score_for_question(matched_keywords, can_solve, marks_per_q):
    """
    Calculate score based on keyword matching
    Formula: (matched keywords / total keywords) * (can_solve * marks_per_q)
    """
    if len(matched_keywords) == 0:
        return 0
    
    max_possible = can_solve * marks_per_q
    # Award score proportional to keyword matches
    score = (len(matched_keywords) / max(1, len(matched_keywords))) * max_possible
    return min(score, max_possible)



# ==================== AUTHENTICATION ROUTES ====================



@app.route('/')
def index():
    """Home page"""
    if 'teacher_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register new teacher"""
    if request.method == 'POST':
        data = request.form
        
        email = data.get('email', '').strip()
        full_name = data.get('full_name', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        school_name = data.get('school_name', '').strip()
        subject = data.get('subject', '').strip()
        
        # Validation
        if not all([email, full_name, password, school_name, subject]):
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        # Register
        success, message = AuthManager.register_teacher(email, full_name, password, school_name, subject)
        
        if success:
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
            return render_template('register.html')
    
    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login teacher"""
    if request.method == 'POST':
        data = request.form
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            flash('Email and password required', 'error')
            return render_template('login.html')
        
        success, teacher, message = AuthManager.login_teacher(email, password)
        
        if success:
            session['teacher_id'] = str(teacher['_id'])
            session['teacher_email'] = teacher['email']
            session['teacher_name'] = teacher['full_name']
            session['teacher_school'] = teacher['school_name']
            session['teacher_subject'] = teacher['subject']
            session.permanent = True
            
            flash(f'Welcome back, {teacher["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'error')
            return render_template('login.html')
    
    return render_template('login.html')



@app.route('/logout')
def logout():
    """Logout teacher"""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))



# ==================== PROTECTED ROUTES ====================



@app.route('/dashboard')
@login_required
def dashboard():
    """Teacher dashboard"""
    try:
        teacher = AuthManager.get_teacher_by_id(session['teacher_id'])
        
        # Get recent evaluations
        recent_results = []
        results_folder = os.path.join(UPLOAD_FOLDER, 'results')
        
        if os.path.exists(results_folder):
            files = sorted(os.listdir(results_folder), reverse=True)[:5]
            for file in files:
                try:
                    with open(os.path.join(results_folder, file), 'r') as f:
                        data = json.load(f)
                        # Only show results from this teacher
                        if data.get('teacher_id') == session['teacher_id']:
                            recent_results.append({
                                'filename': file,
                                'student_name': data.get('student_name'),
                                'exam_title': data.get('exam_title'),
                                'timestamp': data.get('timestamp'),
                                'percentage': round(data.get('percentage', 0), 2)
                            })
                except:
                    pass
        
        return render_template('dashboard.html', 
                             teacher=teacher,
                             recent_results=recent_results)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('index'))



@app.route('/profile')
@login_required
def profile():
    """Teacher profile page"""
    try:
        teacher = AuthManager.get_teacher_by_id(session['teacher_id'])
        return render_template('profile.html', teacher=teacher)
    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'error')
        return redirect(url_for('dashboard'))



@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload and evaluate answer sheets"""
    if request.method == 'POST':
        try:
            # Check if the post request has the file parts
            if 'answer_sheet' not in request.files or 'answer_key' not in request.files:
                return jsonify({'error': 'Missing file part'}), 400
            
            answer_sheet = request.files['answer_sheet']
            answer_key = request.files['answer_key']
            
            # Check if files are selected
            if answer_sheet.filename == '' or answer_key.filename == '':
                return jsonify({'error': 'No selected files'}), 400
            
            # Get form data
            student_name = request.form.get('student_name', 'Unknown')
            student_id = request.form.get('student_id', 'Unknown')
            exam_title = request.form.get('exam_title', 'Exam')
            
            # ===== CRITICAL: Parse question pattern from JSON =====
            question_pattern_json = request.form.get('question_pattern_json', '[]')
            try:
                question_pattern = json.loads(question_pattern_json)
            except:
                return jsonify({'error': 'Invalid question pattern'}), 400
            
            if not question_pattern or len(question_pattern) == 0:
                return jsonify({'error': 'No question pattern configured'}), 400
            
            # Calculate total marks from pattern
            total_marks_config = sum(q['total_marks'] for q in question_pattern)
            total_marks_form = float(request.form.get('total_marks', 0))
            
            # Verify they match
            if abs(total_marks_config - total_marks_form) > 0.1:
                return jsonify({'error': f'Total marks mismatch: calculated {total_marks_config}, form has {total_marks_form}'}), 400
            
            # Check if files are allowed
            if not (allowed_file(answer_sheet.filename) and allowed_file(answer_key.filename)):
                return jsonify({'error': 'File type not allowed'}), 400
            
            # Generate unique filenames
            answer_sheet_filename = secure_filename(f"{uuid.uuid4()}_{answer_sheet.filename}")
            answer_key_filename = secure_filename(f"{uuid.uuid4()}_{answer_key.filename}")
            
            # Save files
            answer_sheet_path = os.path.join(UPLOAD_FOLDER, 'answer_sheets', answer_sheet_filename)
            answer_key_path = os.path.join(UPLOAD_FOLDER, 'answer_keys', answer_key_filename)
            
            answer_sheet.save(answer_sheet_path)
            answer_key.save(answer_key_path)
            
            # ==================== PROCESS ANSWER KEY ====================
            answer_key_text = ocr_engine.process_answer_sheet(answer_key_path, len(question_pattern))
            
            # Create model answers from OCR extraction
            model_answers = {}
            for question_id, text in answer_key_text.items():
                # Extract keywords (important words)
                words = text.split()
                keywords = [word for word in words if len(word) > 4]
                keywords = keywords[:min(5, len(keywords))]  # Take up to 5 keywords
                
                # Find corresponding question pattern
                max_score = 1
                for q_pattern in question_pattern:
                    if q_pattern['question_id'] == question_id:
                        max_score = q_pattern['total_marks']
                        break
                
                model_answers[question_id] = {
                    'answer': text,
                    'keywords': keywords,
                    'max_score': max_score
                }
            
            # ==================== PROCESS ANSWER SHEET ====================
            extracted_texts = ocr_engine.process_answer_sheet(answer_sheet_path, len(question_pattern))
            
            # ==================== EVALUATE ANSWERS ====================
            evaluation_results = {}
            total_score = 0
            max_score = 0
            
            for question_id, text in extracted_texts.items():
                if question_id in model_answers:
                    model = model_answers[question_id]
                    
                    # Evaluate answer
                    score, feedback = evaluation_engine.evaluate_answer(
                        student_answer=text,
                        model_answer=model['answer'],
                        keywords=model['keywords'],
                        max_score=model.get('max_score', 1)
                    )
                    
                    matched_keywords, keyword_ratio = evaluation_engine.keyword_matching(
                        text, 
                        model['keywords']
                    )
                    
                    # Find question pattern details
                    q_pattern_details = None
                    for q_p in question_pattern:
                        if q_p['question_id'] == question_id:
                            q_pattern_details = q_p
                            break
                    
                    evaluation_results[question_id] = {
                        'extracted_text': text,
                        'model_answer': model['answer'],
                        'score': score,
                        'max_score': model['max_score'],
                        'feedback': feedback,
                        'matched_keywords': matched_keywords,
                        'total_keywords': len(model['keywords']),
                        'keyword_ratio': keyword_ratio,
                        'all_keywords': model['keywords'],
                        'question_pattern': q_pattern_details if q_pattern_details else {}
                    }
                    
                    total_score += score
                    max_score += model['max_score']
                else:
                    # Question not in answer key, mark as not evaluated
                    evaluation_results[question_id] = {
                        'extracted_text': text,
                        'model_answer': 'Not in answer key',
                        'score': 0,
                        'max_score': 0,
                        'feedback': 'Question not found in answer key',
                        'matched_keywords': 0,
                        'total_keywords': 0,
                        'keyword_ratio': 0,
                        'all_keywords': [],
                        'question_pattern': {}
                    }
            
            # ==================== CREATE RESULTS DATAFRAME ====================
            results_df = pd.DataFrame([
                {
                    'Question': question_id,
                    'Score': result['score'],
                    'Max Score': result['max_score'],
                    'Percentage': (result['score'] / result['max_score']) * 100 if result['max_score'] > 0 else 0,
                    'Keywords Matched': f"{result['matched_keywords']}/{result['total_keywords']}"
                }
                for question_id, result in evaluation_results.items()
            ])
            
            # ==================== GENERATE PDF REPORT ====================
            report_filename = report_generator.generate_pdf_report(
                student_name=student_name,
                student_id=student_id,
                exam_title=exam_title,
                teacher_name=session['teacher_name'],
                results_df=results_df,
                evaluation_results=evaluation_results,
                total_score=total_score,
                max_score=max_score
            )
            
            # ==================== SAVE RESULTS TO JSON ====================
            result_data = {
                'teacher_id': session['teacher_id'],
                'teacher_name': session['teacher_name'],
                'student_name': student_name,
                'student_id': student_id,
                'exam_title': exam_title,
                'question_pattern': question_pattern,  # STORE PATTERN
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'evaluation_results': evaluation_results,
                'total_score': round(total_score, 2),
                'max_score': round(max_score, 2),
                'percentage': round((total_score / max_score * 100) if max_score > 0 else 0, 2),
                'report_filename': report_filename
            }
            
            result_filename = f"result_{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            result_path = os.path.join(UPLOAD_FOLDER, 'results', result_filename)
            
            with open(result_path, 'w') as f:
                json.dump(result_data, f, indent=4)
            
            # Update teacher evaluation count in MongoDB
            AuthManager.update_teacher_evaluations(session['teacher_id'])
            
            # Clean up temporary files
            try:
                os.remove(answer_sheet_path)
                os.remove(answer_key_path)
            except:
                pass
            
            # Return success response
            return jsonify({
                'success': True,
                'result_file': result_filename,
                'redirect_url': url_for('results', result_file=result_filename)
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': f"Error: {str(e)}"}), 500
    
    return render_template('upload.html')



@app.route('/results/<result_file>')
@login_required
def results(result_file):
    """Display evaluation results"""
    try:
        # Load results from JSON file
        result_path = os.path.join(UPLOAD_FOLDER, 'results', result_file)
        
        if not os.path.exists(result_path):
            flash('Result file not found', 'error')
            return redirect(url_for('upload'))
        
        with open(result_path, 'r') as f:
            result_data = json.load(f)
        
        # Verify that this result belongs to the logged-in teacher
        if result_data.get('teacher_id') != session['teacher_id']:
            flash('You do not have permission to view this result', 'error')
            return redirect(url_for('dashboard'))
        
        # Create results list for display
        results_list = []
        for question_id, result in result_data['evaluation_results'].items():
            results_list.append({
                'question_id': question_id,
                'extracted_text': result['extracted_text'],
                'model_answer': result['model_answer'],
                'score': result['score'],
                'max_score': result['max_score'],
                'percentage': round((result['score'] / result['max_score']) * 100, 2) if result['max_score'] > 0 else 0,
                'feedback': result['feedback'],
                'keywords_matched': f"{result['matched_keywords']}/{result['total_keywords']}",
                'question_type': result.get('question_type', 'Unknown'),
                'question_details': result.get('question_details', '')
            })
        
        return render_template(
            'results.html',
            student_name=result_data['student_name'],
            student_id=result_data['student_id'],
            exam_title=result_data['exam_title'],
            timestamp=result_data['timestamp'],
            total_score=result_data['total_score'],
            max_score=result_data['max_score'],
            percentage=result_data['percentage'],
            results=results_list,
            report_filename=result_data['report_filename'],
            result_file=result_file
        )
    
    except Exception as e:
        flash(f'Error loading results: {str(e)}', 'error')
        return redirect(url_for('upload'))



@app.route('/my-evaluations')
@login_required
def my_evaluations():
    """View all evaluations by logged-in teacher"""
    try:
        all_results = []
        results_folder = os.path.join(UPLOAD_FOLDER, 'results')
        
        if os.path.exists(results_folder):
            files = sorted(os.listdir(results_folder), reverse=True)
            
            for file in files:
                try:
                    with open(os.path.join(results_folder, file), 'r') as f:
                        data = json.load(f)
                        
                        # Only show results from this teacher
                        if data.get('teacher_id') == session['teacher_id']:
                            all_results.append({
                                'filename': file,
                                'student_name': data.get('student_name'),
                                'student_id': data.get('student_id'),
                                'exam_title': data.get('exam_title'),
                                'timestamp': data.get('timestamp'),
                                'percentage': round(data.get('percentage', 0), 2),
                                'total_score': data.get('total_score'),
                                'max_score': data.get('max_score')
                            })
                except:
                    pass
        
        return render_template('my_evaluations.html', evaluations=all_results)
    
    except Exception as e:
        flash(f'Error loading evaluations: {str(e)}', 'error')
        return redirect(url_for('dashboard'))



@app.route('/download/<filename>')
@login_required
def download_report(filename):
    """Download PDF report"""
    try:
        return send_from_directory(
            os.path.join(UPLOAD_FOLDER, 'reports'), 
            filename, 
            as_attachment=True
        )
    except Exception as e:
        flash(f'Error downloading report: {str(e)}', 'error')
        return redirect(url_for('dashboard'))



# ==================== STATIC PAGES ====================



@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')



@app.route('/help')
def help():
    """Help page"""
    return render_template('help.html')



# ==================== ERROR HANDLERS ====================



@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404



@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500



@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    flash('File size too large. Maximum allowed: 50MB', 'error')
    return redirect(url_for('upload'))



# ==================== RUN APPLICATION ====================



if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)