from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, validator
from typing import Optional
import psycopg2
import psycopg2.extras

app = FastAPI(title="Student Management System")

# Allow the HTML frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Database connection ──────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "student_db",
    "user": "postgres",
    "password": 12345678,   # ← change this
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)


# ── Pydantic models (input validation) ──────────────────────

class StudentCreate(BaseModel):
    full_name: str
    email: str
    course_name: str
    age: int
    phone: str

    @validator("full_name")
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()

    @validator("age")
    def valid_age(cls, v):
        if not (5 <= v <= 100):
            raise ValueError("Age must be between 5 and 100")
        return v

    @validator("email")
    def valid_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v.strip().lower()

    @validator("phone")
    def valid_phone(cls, v):
        digits = v.replace("+", "").replace("-", "").replace(" ", "")
        if not digits.isdigit() or len(digits) < 7:
            raise ValueError("Invalid phone number")
        return v.strip()

class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    course_name: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None


# ── Serve the frontend ───────────────────────────────────────

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")


# ── CREATE ───────────────────────────────────────────────────

@app.post("/students", status_code=201)
def create_student(student: StudentCreate):
    sql = """
        INSERT INTO students (full_name, email, course_name, age, phone)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
    """
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (
                    student.full_name, student.email,
                    student.course_name, student.age, student.phone
                ))
                result = dict(cur.fetchone())
            conn.commit()
        return {"message": "Student added successfully", "student": result}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Email already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── READ (all, with optional search) ────────────────────────

@app.get("/students")
def get_all_students(search: Optional[str] = None):
    if search:
        sql = """
            SELECT * FROM students
            WHERE full_name ILIKE %s OR email ILIKE %s OR course_name ILIKE %s
            ORDER BY student_id
        """
        params = (f"%{search}%", f"%{search}%", f"%{search}%")
    else:
        sql = "SELECT * FROM students ORDER BY student_id"
        params = None

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = [dict(r) for r in cur.fetchall()]
        return {"students": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── READ (single student by ID) ──────────────────────────────

@app.get("/students/{student_id}")
def get_student(student_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
                row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Student not found")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── UPDATE ───────────────────────────────────────────────────

@app.put("/students/{student_id}")
def update_student(student_id: int, student: StudentUpdate):
    # Only update the fields that were actually sent
    fields = {k: v for k, v in student.dict().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [student_id]
    sql = f"UPDATE students SET {set_clause} WHERE student_id = %s RETURNING *"

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, values)
                row = cur.fetchone()
            conn.commit()
        if not row:
            raise HTTPException(status_code=404, detail="Student not found")
        return {"message": "Student updated successfully", "student": dict(row)}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Email already in use")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── DELETE ───────────────────────────────────────────────────

@app.delete("/students/{student_id}")
def delete_student(student_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM students WHERE student_id = %s RETURNING student_id",
                    (student_id,)
                )
                deleted = cur.fetchone()
            conn.commit()
        if not deleted:
            raise HTTPException(status_code=404, detail="Student not found")
        return {"message": f"Student {student_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── STATS (bonus) ────────────────────────────────────────────

@app.get("/students/meta/stats")
def get_stats():
    sql = """
        SELECT
            COUNT(*) AS total,
            COUNT(DISTINCT course_name) AS courses,
            ROUND(AVG(age), 1) AS avg_age
        FROM students
    """
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                return dict(cur.fetchone())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))