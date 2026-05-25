shutdownDB:
	uv run python -c "from database import engine; from models import Base; Base.metadata.drop_all(bind=engine)"

seed:
	uv run python seed.py

run:
	uv run uvicorn main:app --reload