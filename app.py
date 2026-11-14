"""
CodeCraftHub - Course Tracking REST API

This Flask application provides CRUD operations for courses and stores
course data in a local JSON file named courses.json.

Run the application with:

    python app.py
"""

from datetime import datetime, timezone
from pathlib import Path
import json

from flask import Flask, jsonify, request


# Create the Flask application
app = Flask(__name__)
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

# Store courses.json in the same directory as this Python file
COURSES_FILE = Path(__file__).resolve().parent / "courses.json"

# Allowed course status values
VALID_STATUSES = {
    "Not Started",
    "In Progress",
    "Completed",
}

# Required fields when creating or replacing a course
REQUIRED_FIELDS = {
    "name",
    "description",
    "target_date",
    "status",
}


class CourseFileError(Exception):
    """Custom error used when the courses.json file cannot be read or written."""


def create_courses_file_if_needed():
    """
    Create courses.json automatically if it does not already exist.

    The file starts with an empty JSON list because courses will be stored
    as objects inside that list.
    """
    if not COURSES_FILE.exists():
        try:
            COURSES_FILE.write_text("[]", encoding="utf-8")
        except OSError as error:
            raise CourseFileError(
                f"Could not create {COURSES_FILE.name}: {error}"
            ) from error


def read_courses():
    """
    Read and return all courses from courses.json.

    Returns:
        list: A list of course dictionaries.

    Raises:
        CourseFileError: If the file cannot be read or contains invalid JSON.
    """
    create_courses_file_if_needed()

    try:
        with COURSES_FILE.open("r", encoding="utf-8") as file:
            courses = json.load(file)
    except OSError as error:
        raise CourseFileError(
            f"Could not read {COURSES_FILE.name}: {error}"
        ) from error
    except json.JSONDecodeError as error:
        raise CourseFileError(
            f"{COURSES_FILE.name} contains invalid JSON: {error}"
        ) from error

    # Make sure the JSON file contains a list
    if not isinstance(courses, list):
        raise CourseFileError(
            f"{COURSES_FILE.name} must contain a JSON list."
        )

    return courses


def write_courses(courses):
    """
    Write the supplied course list to courses.json.

    Args:
        courses: List of course dictionaries.

    Raises:
        CourseFileError: If the file cannot be written.
    """
    try:
        with COURSES_FILE.open("w", encoding="utf-8") as file:
            json.dump(courses, file, indent=2)
            file.write("\n")
    except OSError as error:
        raise CourseFileError(
            f"Could not write to {COURSES_FILE.name}: {error}"
        ) from error


def get_next_course_id(courses):
    """
    Generate the next course ID.

    The first course receives ID 1. After that, the next ID is one greater
    than the largest existing ID.
    """
    if not courses:
        return 1

    return max(course["id"] for course in courses) + 1


def get_utc_timestamp():
    """
    Return the current UTC time in ISO 8601 format.

    Example:
        2026-11-13T12:30:45.123456+00:00
    """
    return datetime.now(timezone.utc).isoformat()


def validate_date_format(target_date):
    """
    Validate that a date uses the YYYY-MM-DD format.

    Returns:
        True if valid, otherwise False.
    """
    if not isinstance(target_date, str):
        return False

    try:
        parsed_date = datetime.strptime(target_date, "%Y-%m-%d")

        # This additional check rejects values such as 2026-2-1,
        # which datetime.strptime may otherwise accept.
        return parsed_date.strftime("%Y-%m-%d") == target_date
    except ValueError:
        return False


def validate_course_data(data, require_all_fields=True):
    """
    Validate course data received from a client.

    Args:
        data: Request JSON object.
        require_all_fields: When True, all required fields must be present.
                            Used for POST and PUT.

    Returns:
        A dictionary containing an error response, or None if valid.
    """
    if not isinstance(data, dict):
        return {
            "error": "Request body must contain a JSON object."
        }

    if require_all_fields:
        missing_fields = sorted(REQUIRED_FIELDS - set(data.keys()))

        if missing_fields:
            return {
                "error": "Missing required fields.",
                "missing_fields": missing_fields,
            }

    # Validate fields that are present
    if "name" in data:
        if not isinstance(data["name"], str) or not data["name"].strip():
            return {
                "error": "The 'name' field is required and cannot be empty."
            }

    if "description" in data:
        if (
            not isinstance(data["description"], str)
            or not data["description"].strip()
        ):
            return {
                "error": (
                    "The 'description' field is required "
                    "and cannot be empty."
                )
            }

    if "target_date" in data:
        if not validate_date_format(data["target_date"]):
            return {
                "error": (
                    "The 'target_date' field must use the "
                    "YYYY-MM-DD format."
                )
            }

    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            return {
                "error": "Invalid status value.",
                "valid_statuses": sorted(VALID_STATUSES),
            }

    return None


def find_course(courses, course_id):
    """Find a course by ID, or return None if it does not exist."""
    return next(
        (course for course in courses if course.get("id") == course_id),
        None,
    )


def json_body_or_error():
    """
    Read the request JSON body.

    Returns:
        A tuple of (data, error_response).
        error_response is None when the request body is valid.
    """
    if not request.is_json:
        return None, {
            "error": "Request must have Content-Type: application/json."
        }

    data = request.get_json(silent=True)

    if data is None:
        return None, {
            "error": "Request body contains invalid JSON."
        }

    return data, None


@app.errorhandler(CourseFileError)
def handle_course_file_error(error):
    """
    Return a helpful response when courses.json cannot be read or written.
    """
    return jsonify({
        "error": "Course file error.",
        "details": str(error),
    }), 500


@app.errorhandler(404)
def handle_not_found(error):
    """Return JSON instead of Flask's default HTML 404 page."""
    return jsonify({
        "error": "The requested endpoint was not found."
    }), 404


@app.errorhandler(405)
def handle_method_not_allowed(error):
    """Return JSON when an unsupported HTTP method is used."""
    return jsonify({
        "error": "The HTTP method is not allowed for this endpoint."
    }), 405


@app.route("/api/courses", methods=["POST"])
def add_course():
    """
    Add a new course.

    Endpoint:
        POST /api/courses
    """
    data, body_error = json_body_or_error()

    if body_error:
        return jsonify(body_error), 400

    validation_error = validate_course_data(data)

    if validation_error:
        return jsonify(validation_error), 400

    courses = read_courses()

    new_course = {
        "id": get_next_course_id(courses),
        "name": data["name"].strip(),
        "description": data["description"].strip(),
        "target_date": data["target_date"],
        "status": data["status"],
        "created_at": get_utc_timestamp(),
    }

    courses.append(new_course)
    write_courses(courses)

    return jsonify(new_course), 201


@app.route("/api/courses", methods=["GET"])
def get_all_courses():
    """
    Return all courses.

    Endpoint:
        GET /api/courses
    """
    courses = read_courses()
    return jsonify(courses), 200


@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    """
    Return one course by ID.

    Endpoint:
        GET /api/courses/<id>
    """
    courses = read_courses()
    course = find_course(courses, course_id)

    if course is None:
        return jsonify({
            "error": f"Course with ID {course_id} was not found."
        }), 404

    return jsonify(course), 200


@app.route("/api/courses/<int:course_id>", methods=["PUT"])
def update_course(course_id):
    """
    Replace all editable fields for an existing course.

    The ID and created_at values cannot be changed.

    Endpoint:
        PUT /api/courses/<id>
    """
    data, body_error = json_body_or_error()

    if body_error:
        return jsonify(body_error), 400

    validation_error = validate_course_data(data)

    if validation_error:
        return jsonify(validation_error), 400

    courses = read_courses()
    course = find_course(courses, course_id)

    if course is None:
        return jsonify({
            "error": f"Course with ID {course_id} was not found."
        }), 404

    # Update only the editable course fields.
    course["name"] = data["name"].strip()
    course["description"] = data["description"].strip()
    course["target_date"] = data["target_date"]
    course["status"] = data["status"]

    write_courses(courses)

    return jsonify(course), 200


@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    """
    Delete an existing course.

    Endpoint:
        DELETE /api/courses/<id>
    """
    courses = read_courses()
    course = find_course(courses, course_id)

    if course is None:
        return jsonify({
            "error": f"Course with ID {course_id} was not found."
        }), 404

    courses.remove(course)
    write_courses(courses)

    return jsonify({
        "message": f"Course with ID {course_id} was deleted successfully."
    }), 200


if __name__ == "__main__":
    # Ensure the file is created when the application starts.
    # File errors are also handled when an API request is made.
    try:
        create_courses_file_if_needed()
    except CourseFileError as error:
        print(f"Warning: {error}")

    # debug=True is convenient during development.
    # Disable it in production.
    app.run(debug=True)