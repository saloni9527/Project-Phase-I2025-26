import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import re
import string
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class EvaluationEngine:
    def __init__(self):
        """Initialize Evaluation Engine"""
        # Initialize NLTK components
        try:
            self.lemmatizer = WordNetLemmatizer()
            self.stopwords_list = stopwords.words('english')
        except LookupError:
            # Download required NLTK data if not present
            nltk.download('stopwords')
            nltk.download('wordnet')
            nltk.download('omw-1.4')
            self.lemmatizer = WordNetLemmatizer()
            self.stopwords_list = stopwords.words('english')
    
    def preprocess_text(self, text):
        """
        Preprocess text for evaluation using regex approach
        
        Parameters:
        text (str): Input text
        
        Returns:
        str: Preprocessed text
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and numbers
        text = re.sub(r'[^a-z\s]', ' ', text)
        
        # Remove stopwords
        no_stop = [word for word in text.split() if word not in self.stopwords_list]
        
        # Lemmatize words
        preprocessed = ' '.join([self.lemmatizer.lemmatize(word) for word in no_stop])
        
        return preprocessed
    
    def keyword_matching(self, student_answer, keywords):
        """
        Check for presence of keywords in student answer
        
        Parameters:
        student_answer (str): Student's answer
        keywords (list): List of keywords to check
        
        Returns:
        tuple: (matched_keywords, match_ratio)
        """
        # Handle empty keywords
        if not keywords:
            return [], 0
        
        # Preprocess student answer
        processed_answer = self.preprocess_text(student_answer)
        
        # Check for keyword matches
        matched_keywords = []
        for keyword in keywords:
            # Preprocess keyword
            processed_keyword = self.preprocess_text(keyword)
            
            # Check if keyword is in the answer (word-level matching)
            if processed_keyword and processed_keyword in processed_answer.split():
                matched_keywords.append(keyword)
            # Also check if it's a substring (for multi-word keywords)
            elif processed_keyword and processed_keyword in processed_answer:
                matched_keywords.append(keyword)
        
        # Calculate match ratio
        match_ratio = len(matched_keywords) / len(keywords) if keywords else 0
        
        return matched_keywords, match_ratio
    
    def semantic_similarity(self, student_answer, model_answer):
        """
        Calculate semantic similarity between student answer and model answer
        using TF-IDF and cosine similarity
        
        Parameters:
        student_answer (str): Student's answer
        model_answer (str): Model answer
        
        Returns:
        float: Similarity score between 0 and 1
        """
        # Handle empty answers
        if not student_answer or not model_answer:
            return 0
        
        # Preprocess texts
        processed_student = self.preprocess_text(student_answer)
        processed_model = self.preprocess_text(model_answer)
        
        # Handle empty preprocessed texts
        if not processed_student or not processed_model:
            return 0
        
        # Create TF-IDF vectors
        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([processed_model, processed_student])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Ensure similarity is in valid range [0, 1]
            similarity = max(0, min(1, similarity))
        
        except Exception as e:
            # Handle case where vectorization fails
            print(f"Error in semantic similarity calculation: {e}")
            similarity = 0
        
        return similarity
    
    def evaluate_answer(self, student_answer, model_answer, keywords, max_score):
        """
        Evaluate a student answer against a model answer and keywords
        
        Parameters:
        student_answer (str): Student's answer text
        model_answer (str): Expected/model answer
        keywords (list): List of important keywords for the answer
        max_score (float): Maximum possible score for this question
        
        Returns:
        tuple: (score, feedback) - Score is float, feedback is string
        """
        # Handle empty/invalid inputs
        if not student_answer or student_answer.isspace():
            return 0, "No answer provided."
        
        if not model_answer or model_answer.isspace():
            return 0, "No model answer configured."
        
        if max_score <= 0:
            max_score = 10
        
        # Keyword matching
        matched_keywords, keyword_ratio = self.keyword_matching(student_answer, keywords)
        
        # Semantic similarity
        similarity = self.semantic_similarity(student_answer, model_answer)
        
        # Calculate score
        # Weight: 60% keyword matching, 40% semantic similarity
        weighted_score = (0.6 * keyword_ratio + 0.4 * similarity) * max_score
        score = min(round(weighted_score, 2), max_score)  # Ensure score doesn't exceed max_score
        
        # Generate feedback
        feedback = self._generate_feedback(
            student_answer, 
            model_answer, 
            matched_keywords, 
            keywords, 
            similarity,
            score,
            max_score
        )
        
        return score, feedback
    
    def _generate_feedback(self, student_answer, model_answer, matched_keywords, all_keywords, similarity, score, max_score):
        """
        Generate detailed feedback for the student based on evaluation metrics
        
        Parameters:
        student_answer (str): Student's answer
        model_answer (str): Model answer
        matched_keywords (list): Keywords found in student's answer
        all_keywords (list): All keywords that should be in answer
        similarity (float): Semantic similarity score
        score (float): Calculated score
        max_score (float): Maximum possible score
        
        Returns:
        str: Feedback message
        """
        feedback = []
        
        # Score-based feedback
        percentage = (score / max_score) * 100 if max_score > 0 else 0
        
        if percentage >= 80:
            feedback.append("✓ Excellent answer! You've covered the main points well.")
        elif percentage >= 60:
            feedback.append("✓ Good answer, but there's room for improvement.")
        elif percentage >= 40:
            feedback.append("△ Your answer is partially correct.")
        else:
            feedback.append("✗ Your answer needs significant improvement.")
        
        # Missing keywords feedback
        missing_keywords = [k for k in all_keywords if k not in matched_keywords]
        if missing_keywords:
            if len(missing_keywords) <= 2:
                feedback.append(f"Missing key concepts: {', '.join(missing_keywords)}.")
            else:
                feedback.append(f"Missing {len(missing_keywords)} key concepts. Consider including: {', '.join(missing_keywords[:3])}...")
        
        # Semantic similarity feedback
        if similarity < 0.3:
            feedback.append("Your answer differs significantly from the expected response. Review the model answer.")
        elif similarity < 0.5:
            feedback.append("Your answer partially addresses the question. Add more relevant details.")
        elif similarity < 0.7:
            feedback.append("Your answer aligns fairly well with the expected response.")
        else:
            feedback.append("Your answer aligns very well with the expected response.")
        
        # Length feedback
        student_length = len(student_answer.split())
        model_length = len(model_answer.split())
        
        if student_length < model_length * 0.3:
            feedback.append("Your answer is too brief. Provide more detailed explanation.")
        elif student_length < model_length * 0.6:
            feedback.append("Consider elaborating further on your answer.")
        elif student_length > model_length * 2.5:
            feedback.append("Your answer is unnecessarily long. Be more concise.")
        
        # Combine all feedback
        final_feedback = " ".join(feedback)
        
        return final_feedback
