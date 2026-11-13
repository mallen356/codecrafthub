# CodeCraftHub

CodeCraftHub is a beginner-friendly REST API built with Python and Flask that helps developers track courses they want to learn. Instead of a database, it stores course information in a local `courses.json` file, making it an ideal project for learning REST API fundamentals, HTTP methods, JSON handling, and CRUD operations.

## Features
- **Full CRUD Support:** Create, read, update, and delete learning courses.
- **File-Based Storage:** Automatically creates and manages a local `courses.json` file.
- **Auto-Generated Metadata:** Automatically assigns sequential course IDs and UTC creation timestamps.
- **Input Validation & Error Handling:** Validates required fields, `YYYY-MM-DD` date formatting, and allowed status values (`Not Started`, `In Progress`, `Completed`) with clear JSON error responses.

## Project Structure
```text
codecrafthub/
├── app.py              # Main Flask application and REST API endpoints
├── courses.json        # Local JSON file storing course data
├── requirements.txt    # Python dependencies (Flask)
└── README.md           # Project documentation
