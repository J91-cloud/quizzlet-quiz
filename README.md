CLI Quiz Application with SQLite Setup & Usage
Quick Start

Save the Python script as quiz.py
Make it executable (Linux/Mac): chmod +x quiz.py
Create your first quiz:




# Create a new quiz
python quiz.py --create quiz_name

# Add questions to existing quiz
python quiz.py --add quiz_name

# List all quizzes
python quiz.py --list

# Show quiz info
python quiz.py --info quiz_name

# Delete a quiz
python quiz.py --delete quiz_name




# Interactive selection
python quiz.py

# Run specific quiz
python quiz.py quiz_name

# Run with shuffled questions
python quiz.py quiz_name --shuffle
