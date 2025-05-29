#!/usr/bin/env python3
"""
CLI Quiz Application with SQLite Database
"""

import sqlite3
import os
import random
import argparse
from typing import List, Dict, Any, Optional


class QuizDatabase:
    def __init__(self, db_path: str = "quizzes.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create quizzes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create questions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                choice_a TEXT NOT NULL,
                choice_b TEXT NOT NULL,
                choice_c TEXT NOT NULL,
                choice_d TEXT NOT NULL,
                correct_answer TEXT NOT NULL CHECK (correct_answer IN ('a', 'b', 'c', 'd')),
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quiz_id) REFERENCES quizzes (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_quiz(self, name: str, title: str, description: str = "") -> int:
        """Create a new quiz and return its ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO quizzes (name, title, description) VALUES (?, ?, ?)",
                (name, title, description)
            )
            quiz_id = cursor.lastrowid
            conn.commit()
            return quiz_id
        except sqlite3.IntegrityError:
            raise ValueError(f"Quiz '{name}' already exists!")
        finally:
            conn.close()
    
    def add_question(self, quiz_name: str, question: str, choices: List[str], 
                    correct: str, explanation: str = ""):
        """Add a question to a quiz"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get quiz ID
        cursor.execute("SELECT id FROM quizzes WHERE name = ?", (quiz_name,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise ValueError(f"Quiz '{quiz_name}' not found!")
        
        quiz_id = result[0]
        
        # Add question
        cursor.execute('''
            INSERT INTO questions 
            (quiz_id, question, choice_a, choice_b, choice_c, choice_d, correct_answer, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (quiz_id, question, choices[0], choices[1], choices[2], choices[3], correct, explanation))
        
        conn.commit()
        conn.close()
    
    def get_quiz_questions(self, quiz_name: str) -> List[Dict[str, Any]]:
        """Get all questions for a quiz"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT q.question, q.choice_a, q.choice_b, q.choice_c, q.choice_d, 
                   q.correct_answer, q.explanation
            FROM questions q
            JOIN quizzes qz ON q.quiz_id = qz.id
            WHERE qz.name = ?
            ORDER BY q.id
        ''', (quiz_name,))
        
        questions = []
        for row in cursor.fetchall():
            questions.append({
                'question': row[0],
                'choices': [row[1], row[2], row[3], row[4]],
                'correct': ord(row[5]) - ord('a'),  # Convert letter to index
                'explanation': row[6] or ""
            })
        
        conn.close()
        return questions
    
    def get_quiz_info(self, quiz_name: str) -> Optional[Dict[str, Any]]:
        """Get quiz information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT qz.name, qz.title, qz.description, COUNT(q.id) as question_count
            FROM quizzes qz
            LEFT JOIN questions q ON qz.id = q.quiz_id
            WHERE qz.name = ?
            GROUP BY qz.id
        ''', (quiz_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'name': result[0],
                'title': result[1],
                'description': result[2],
                'question_count': result[3]
            }
        return None
    
    def list_quizzes(self) -> List[Dict[str, Any]]:
        """List all quizzes with question counts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT qz.name, qz.title, qz.description, COUNT(q.id) as question_count
            FROM quizzes qz
            LEFT JOIN questions q ON qz.id = q.quiz_id
            GROUP BY qz.id
            ORDER BY qz.name
        ''')
        
        quizzes = []
        for row in cursor.fetchall():
            quizzes.append({
                'name': row[0],
                'title': row[1],
                'description': row[2],
                'question_count': row[3]
            })
        
        conn.close()
        return quizzes
    
    def delete_quiz(self, quiz_name: str) -> bool:
        """Delete a quiz and all its questions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM quizzes WHERE name = ?", (quiz_name,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted


class Quiz:
    def __init__(self, name: str, title: str, questions: List[Dict[str, Any]]):
        self.name = name
        self.title = title
        self.questions = questions
        self.score = 0
        self.total = len(questions)
    
    def run(self, shuffle: bool = False):
        """Run the quiz"""
        if not self.questions:
            print(f"Quiz '{self.name}' has no questions!")
            return
        
        print(f"\n{'='*60}")
        print(f"  {self.title}")
        print(f"{'='*60}")
        print(f"Total Questions: {self.total}")
        print("Type the letter (a, b, c, d) for your answer")
        print("Type 'quit' to exit early")
        print("-" * 60)
        
        questions = self.questions.copy()
        if shuffle:
            random.shuffle(questions)
        
        for i, question in enumerate(questions, 1):
            if not self._ask_question(i, question):
                break
        
        self._show_results()
    
    def _ask_question(self, num: int, question: Dict[str, Any]) -> bool:
        """Ask a single question and return True to continue, False to quit"""
        print(f"\nQuestion {num}/{self.total}:")
        print(f"{question['question']}")
        print()
        
        # Display choices
        choices = question['choices']
        for i, choice in enumerate(choices):
            letter = chr(ord('a') + i)
            print(f"  {letter}) {choice}")
        
        while True:
            answer = input("\nYour answer: ").strip().lower()
            
            if answer == 'quit':
                return False
            
            if answer in ['a', 'b', 'c', 'd']:
                correct_index = question['correct']
                if ord(answer) - ord('a') == correct_index:
                    print("✓ Correct!")
                    self.score += 1
                else:
                    correct_letter = chr(ord('a') + correct_index)
                    print(f"✗ Wrong! The correct answer was {correct_letter}) {choices[correct_index]}")
                
                if question['explanation']:
                    print(f"Explanation: {question['explanation']}")
                
                input("\nPress Enter to continue...")
                return True
            else:
                print("Please enter a valid letter (a, b, c, d) or 'quit'")
    
    def _show_results(self):
        """Show final results"""
        percentage = (self.score / self.total) * 100
        print(f"\n{'='*60}")
        print("QUIZ RESULTS")
        print(f"{'='*60}")
        print(f"Score: {self.score}/{self.total} ({percentage:.1f}%)")
        
        if percentage >= 90:
            print("🌟 Excellent work!")
        elif percentage >= 80:
            print("👍 Great job!")
        elif percentage >= 70:
            print("👌 Good effort!")
        elif percentage >= 60:
            print("📚 Keep studying!")
        else:
            print("💪 Practice makes perfect!")


def create_quiz_command(db: QuizDatabase, quiz_name: str):
    """Interactive quiz creation"""
    print(f"Creating quiz: {quiz_name}")
    print("-" * 40)
    
    title = input("Quiz title: ").strip()
    if not title:
        title = quiz_name.replace('_', ' ').title()
    
    description = input("Quiz description (optional): ").strip()
    
    try:
        quiz_id = db.create_quiz(quiz_name, title, description)
        print(f"✓ Quiz '{quiz_name}' created successfully!")
        return True
    except ValueError as e:
        print(f"Error: {e}")
        return False


def add_questions_command(db: QuizDatabase, quiz_name: str):
    """Add questions to existing quiz"""
    # Verify quiz exists
    quiz_info = db.get_quiz_info(quiz_name)
    if not quiz_info:
        print(f"Error: Quiz '{quiz_name}' not found!")
        print("Use --create to create it first, or --list to see available quizzes.")
        return
    
    print(f"Adding questions to: {quiz_info['title']}")
    print(f"Current questions: {quiz_info['question_count']}")
    print("-" * 50)
    
    question_num = quiz_info['question_count'] + 1
    
    while True:
        print(f"\n--- Question {question_num} ---")
        question_text = input("Question: ").strip()
        
        if not question_text:
            print("Question cannot be empty!")
            continue
        
        # Get 4 choices
        choices = []
        for i in range(4):
            choice = input(f"Choice {chr(ord('a')+i)}: ").strip()
            if not choice:
                print("All 4 choices are required!")
                break
            choices.append(choice)
        
        if len(choices) != 4:
            continue
        
        # Get correct answer
        while True:
            correct = input("Correct answer (a, b, c, d): ").strip().lower()
            if correct in ['a', 'b', 'c', 'd']:
                break
            print("Please enter a, b, c, or d")
        
        explanation = input("Explanation (optional): ").strip()
        
        try:
            db.add_question(quiz_name, question_text, choices, correct, explanation)
            print("✓ Question added!")
            question_num += 1
        except Exception as e:
            print(f"Error adding question: {e}")
            continue
        
        if input("\nAdd another question? (y/n): ").strip().lower() != 'y':
            break
    
    # Show updated count
    updated_info = db.get_quiz_info(quiz_name)
    print(f"\nQuiz '{quiz_name}' now has {updated_info['question_count']} questions!")


def list_quizzes_command(db: QuizDatabase):
    """List all available quizzes"""
    quizzes = db.list_quizzes()
    
    if not quizzes:
        print("No quizzes found!")
        print("Use --create <name> to create your first quiz.")
        return
    
    print(f"{'Name':<20} {'Title':<30} {'Questions':<10} {'Description'}")
    print("-" * 80)
    
    for quiz in quizzes:
        desc = quiz['description'][:30] + "..." if len(quiz['description']) > 30 else quiz['description']
        print(f"{quiz['name']:<20} {quiz['title']:<30} {quiz['question_count']:<10} {desc}")


def run_quiz_command(db: QuizDatabase, quiz_name: str, shuffle: bool = False):
    """Run a specific quiz"""
    quiz_info = db.get_quiz_info(quiz_name)
    if not quiz_info:
        print(f"Quiz '{quiz_name}' not found!")
        return
    
    if quiz_info['question_count'] == 0:
        print(f"Quiz '{quiz_name}' has no questions!")
        print(f"Use: python quiz.py --add {quiz_name}")
        return
    
    questions = db.get_quiz_questions(quiz_name)
    quiz = Quiz(quiz_name, quiz_info['title'], questions)
    quiz.run(shuffle)


def main():
    parser = argparse.ArgumentParser(description="CLI Quiz Application with SQLite")
    parser.add_argument("quiz", nargs="?", help="Quiz name to run")
    parser.add_argument("--create", metavar="NAME", help="Create a new quiz")
    parser.add_argument("--add", metavar="NAME", help="Add questions to existing quiz")
    parser.add_argument("--list", action="store_true", help="List all quizzes")
    parser.add_argument("--delete", metavar="NAME", help="Delete a quiz")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle questions when running quiz")
    parser.add_argument("--info", metavar="NAME", help="Show quiz information")
    
    args = parser.parse_args()
    db = QuizDatabase()
    
    # Handle commands
    if args.create:
        if create_quiz_command(db, args.create):
            print(f"Next step: python quiz.py --add {args.create}")
        return
    
    if args.add:
        add_questions_command(db, args.add)
        return
    
    if args.list:
        list_quizzes_command(db)
        return
    
    if args.delete:
        if db.delete_quiz(args.delete):
            print(f"Quiz '{args.delete}' deleted successfully!")
        else:
            print(f"Quiz '{args.delete}' not found!")
        return
    
    if args.info:
        quiz_info = db.get_quiz_info(args.info)
        if quiz_info:
            print(f"Name: {quiz_info['name']}")
            print(f"Title: {quiz_info['title']}")
            print(f"Description: {quiz_info['description']}")
            print(f"Questions: {quiz_info['question_count']}")
        else:
            print(f"Quiz '{args.info}' not found!")
        return
    
    # Run quiz
    if args.quiz:
        run_quiz_command(db, args.quiz, args.shuffle)
    else:
        # Interactive quiz selection
        quizzes = db.list_quizzes()
        if not quizzes:
            print("No quizzes found!")
            print("Create your first quiz: python quiz.py --create myquiz")
            return
        
        print("Available quizzes:")
        for i, quiz in enumerate(quizzes, 1):
            print(f"  {i}. {quiz['name']} - {quiz['title']} ({quiz['question_count']} questions)")
        
        while True:
            try:
                choice = input(f"\nSelect quiz (1-{len(quizzes)}): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(quizzes):
                    selected_quiz = quizzes[int(choice) - 1]['name']
                    run_quiz_command(db, selected_quiz)
                    break
                else:
                    print("Invalid selection!")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break


if __name__ == "__main__":
    main()
