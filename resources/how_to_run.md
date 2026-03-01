# Sound First Service - Setup & Run

## First Time Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` file** (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` to set your `DATABASE_URL` (e.g., `sqlite:///./sound_first.db`)

3. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

4. **Seed the database:**
   ```bash
   py -m app.seed_data
   py -m app.seed_capabilities_v2
   ```

## Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run Tests

```bash
pytest
```

