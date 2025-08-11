from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import User
from app.core.config import settings

def make_admin():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = db.query(User).filter(User.username == "adminuser").first()
    if user:
        user.is_admin = True
        db.commit()
        print(f"User 'adminuser' is now an admin.")
    else:
        print(f"User 'adminuser' not found.")
    db.close()

if __name__ == "__main__":
    make_admin()
