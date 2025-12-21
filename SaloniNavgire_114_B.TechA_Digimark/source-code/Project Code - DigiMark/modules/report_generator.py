from fpdf import FPDF
import os
from datetime import datetime

class ReportGenerator:
    def __init__(self, upload_folder):
        """Initialize Report Generator"""
        self.upload_folder = upload_folder
        self.reports_dir = os.path.join(upload_folder, 'reports')
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def _sanitize_text(self, text):
        """Remove or replace special Unicode characters"""
        if not text:
            return ""
        
        # Convert to string if not already
        text = str(text)
        
        # Replace special Unicode characters with ASCII equivalents
        replacements = {
            '\u2713': '[OK]',       # ✓
            '\u2717': '[X]',        # ✗
            '\u2022': '*',          # •
            '\u2018': "'",          # '
            '\u2019': "'",          # '
            '\u201c': '"',          # "
            '\u201d': '"',          # "
            '\u2014': '-',          # —
            '\u2013': '-',          # –
            '\u2026': '...',        # …
        }
        
        for unicode_char, ascii_char in replacements.items():
            text = text.replace(unicode_char, ascii_char)
        
        # Remove any remaining non-latin characters
        text = text.encode('latin-1', errors='ignore').decode('latin-1')
        
        return text
    
    def generate_pdf_report(self, student_name, student_id, exam_title, teacher_name,
                           results_df, evaluation_results, total_score, max_score):
        """
        Generate a PDF report with evaluation results
        
        Parameters:
        student_name (str): Name of the student
        student_id (str): ID of the student
        exam_title (str): Title of the exam
        teacher_name (str): Name of the teacher
        results_df (DataFrame): Pandas DataFrame with results
        evaluation_results (dict): Dictionary with detailed evaluation results
        total_score (float): Total score obtained
        max_score (float): Maximum possible score
        
        Returns:
        str: Filename of generated PDF report
        """
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # ==================== HEADER ====================
            pdf.set_font('Arial', 'B', 18)
            pdf.cell(0, 15, "Answer Sheet Evaluation Report", 0, 1, 'C')
            
            pdf.set_font('Arial', '', 1)
            pdf.cell(0, 2, "", 0, 1)  # Divider line
            
            # ==================== STUDENT & EXAM INFO ====================
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, "Evaluation Details", 0, 1)
            
            pdf.set_font('Arial', '', 11)
            
            # Sanitize all text inputs
            student_name = self._sanitize_text(student_name)
            student_id = self._sanitize_text(student_id)
            exam_title = self._sanitize_text(exam_title)
            teacher_name = self._sanitize_text(teacher_name)
            
            # Create two columns for info
            col_width = pdf.w / 2.5
            
            pdf.cell(col_width, 8, "Student Name:")
            pdf.set_font('Arial', '', 11)
            pdf.cell(0, 8, student_name, 0, 1)
            
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(col_width, 8, "Student ID:")
            pdf.set_font('Arial', '', 11)
            pdf.cell(0, 8, student_id, 0, 1)
            
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(col_width, 8, "Exam Title:")
            pdf.set_font('Arial', '', 11)
            pdf.cell(0, 8, exam_title, 0, 1)
            
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(col_width, 8, "Teacher Name:")
            pdf.set_font('Arial', '', 11)
            pdf.cell(0, 8, teacher_name, 0, 1)
            
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(col_width, 8, "Evaluation Date:")
            pdf.set_font('Arial', '', 11)
            pdf.cell(0, 8, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0, 1)
            
            # ==================== OVERALL SCORE ====================
            pdf.ln(8)
            pdf.set_font('Arial', 'B', 13)
            pdf.cell(0, 10, "Overall Performance", 0, 1)
            
            pdf.set_font('Arial', '', 11)
            percentage = (total_score / max_score * 100) if max_score > 0 else 0
            
            # Score box
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(0, 10, f"Total Score: {total_score} / {max_score}", 0, 1, fill=True)
            pdf.set_fill_color(200, 255, 200)
            pdf.cell(0, 10, f"Percentage: {percentage:.2f}%", 0, 1, fill=True)
            
            # Grade assignment
            if percentage >= 80:
                grade = "A"
                remarks = "Excellent"
            elif percentage >= 60:
                grade = "B"
                remarks = "Good"
            elif percentage >= 40:
                grade = "C"
                remarks = "Satisfactory"
            else:
                grade = "D"
                remarks = "Needs Improvement"
            
            pdf.set_fill_color(255, 220, 200)
            pdf.cell(0, 10, f"Grade: {grade} ({remarks})", 0, 1, fill=True)
            
            # ==================== QUESTION-WISE RESULTS ====================
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, "Question-wise Results", 0, 1)
            
            # Table headers
            pdf.set_font('Arial', 'B', 10)
            pdf.set_fill_color(100, 150, 200)
            pdf.set_text_color(255, 255, 255)
            
            col1 = 20
            col2 = 30
            col3 = 30
            col4 = 40
            col5 = 70
            
            pdf.cell(col1, 8, "Q.No.", 1, 0, 'C', True)
            pdf.cell(col2, 8, "Score", 1, 0, 'C', True)
            pdf.cell(col3, 8, "Max", 1, 0, 'C', True)
            pdf.cell(col4, 8, "Percentage", 1, 0, 'C', True)
            pdf.cell(col5, 8, "Keywords", 1, 1, 'C', True)
            
            # Table rows
            pdf.set_font('Arial', '', 9)
            pdf.set_text_color(0, 0, 0)
            
            alternate_fill = False
            for _, row in results_df.iterrows():
                question_id = self._sanitize_text(str(row['Question']))
                
                # Alternate row colors
                if alternate_fill:
                    pdf.set_fill_color(240, 240, 240)
                else:
                    pdf.set_fill_color(255, 255, 255)
                
                score = float(row['Score'])
                max_score_q = float(row['Max Score'])
                percentage_q = float(row['Percentage'])
                keywords_matched = self._sanitize_text(str(row['Keywords Matched']))
                
                pdf.cell(col1, 8, question_id, 1, 0, 'C', True)
                pdf.cell(col2, 8, f"{score:.2f}", 1, 0, 'C', True)
                pdf.cell(col3, 8, f"{max_score_q:.2f}", 1, 0, 'C', True)
                pdf.cell(col4, 8, f"{percentage_q:.1f}%", 1, 0, 'C', True)
                pdf.cell(col5, 8, keywords_matched, 1, 1, 'C', True)
                
                alternate_fill = not alternate_fill
            
            # ==================== DETAILED FEEDBACK PAGE ====================
            pdf.add_page()
            pdf.set_font('Arial', 'B', 13)
            pdf.cell(0, 10, "Detailed Feedback", 0, 1)
            pdf.ln(3)
            
            pdf.set_font('Arial', '', 10)
            
            for question_id, result in evaluation_results.items():
                question_id = self._sanitize_text(str(question_id))
                
                # Question header
                pdf.set_font('Arial', 'B', 11)
                pdf.set_fill_color(220, 220, 220)
                score = float(result['score'])
                max_q = float(result['max_score'])
                pdf.cell(0, 8, f"{question_id}: {score:.2f}/{max_q:.2f} marks", 
                        0, 1, fill=True)
                
                pdf.set_font('Arial', '', 9)
                
                # Student answer
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(30, 6, "Student Answer:")
                pdf.set_font('Arial', '', 9)
                pdf.ln(6)
                
                extracted = self._sanitize_text(result['extracted_text'][:150])
                if len(result['extracted_text']) > 150:
                    extracted += "..."
                
                pdf.multi_cell(0, 4, extracted)
                pdf.ln(2)
                
                # Model answer
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(30, 6, "Expected Answer:")
                pdf.set_font('Arial', '', 9)
                pdf.ln(6)
                
                model = self._sanitize_text(result['model_answer'][:150])
                if len(result['model_answer']) > 150:
                    model += "..."
                
                pdf.multi_cell(0, 4, model)
                pdf.ln(2)
                
                # Keywords
                pdf.set_font('Arial', 'B', 9)
                keywords_list = [self._sanitize_text(k) for k in result['all_keywords'][:5]]
                keywords_str = ", ".join(keywords_list)
                if len(result['all_keywords']) > 5:
                    keywords_str += f", ... ({len(result['all_keywords'])} total)"
                pdf.multi_cell(0, 4, f"Key Concepts: {keywords_str}")
                pdf.ln(2)
                
                # Feedback
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(20, 6, "Feedback:")
                pdf.set_font('Arial', '', 9)
                pdf.ln(6)
                feedback = self._sanitize_text(result['feedback'])
                pdf.multi_cell(0, 4, feedback)
                
                pdf.ln(5)
            
            # ==================== FOOTER ====================
            pdf.set_y(-15)
            pdf.set_font('Arial', 'I', 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 10, 
                    f"Digital Marking System - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                    0, 0, 'C')
            
            # ==================== SAVE PDF ====================
            report_filename = f"report_{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            report_path = os.path.join(self.reports_dir, report_filename)
            pdf.output(report_path)
            
            return report_filename
        
        except Exception as e:
            print(f"Error generating PDF report: {e}")
            raise Exception(f"Failed to generate report: {str(e)}")
