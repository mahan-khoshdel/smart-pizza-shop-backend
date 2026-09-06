from app.database.connection import SessionLocal
from app.database.seed.permissions import seed_permissions


db = SessionLocal()

try:
    seed_permissions(db)
    print("Permissions seeded successfully.")
finally:
    db.close()