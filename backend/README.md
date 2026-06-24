# Let's Keep Memories - Backend

Django REST Framework backend for the Let's Keep Memories digital celebration platform.

## Prerequisites

- Python 3.12+
- SQLite (default) or PostgreSQL (configured via `.env`)

## Start Flow

1. **Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup**:
   Create a `.env` file in the root backend directory. At a minimum, you will need:
   ```env
   SECRET_KEY="your-secret-key"
   DEBUG=True
   FRONTEND_URL="http://localhost:3000"
   ```

4. **Database Migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create Superuser (Optional)**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Run Server**:
   ```bash
   python manage.py runserver
   ```
   The API will be available at `http://127.0.0.1:8000/api/`.
