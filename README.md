# Student Management System

A CRUD web application built with FastAPI + PostgreSQL + HTML/CSS/JS.

## Setup

### 1. Install dependencies
### 2. Set up the database
- Open pgAdmin or psql
- Run: `CREATE DATABASE student_db;`
- Connect to `student_db` and run `schema.sql`

### 3. Configure the connection
In `main.py`, update `DB_CONFIG` with your PostgreSQL password.

### 4. Run the server
### 5. Open in browser
Visit `http://localhost:8000`

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST   | /students | Add a student |
| GET    | /students | Get all students |
| GET    | /students?search=xyz | Search students |
| GET    | /students/{id} | Get one student |
| PUT    | /students/{id} | Update a student |
| DELETE | /students/{id} | Delete a student |
