"""Create or promote a local Atlas administrator without storing plaintext credentials."""
import argparse

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    if len(args.password) < 7:
        raise SystemExit("Password must contain at least 7 characters")
    db = SessionLocal()
    try:
        email = args.email.strip().lower()
        user = db.query(User).filter_by(email=email).first()
        if user:
            user.name = args.name.strip(); user.password = hash_password(args.password); user.role = "ADMIN"; user.is_active = True
            action = "updated"
        else:
            user = User(name=args.name.strip(), email=email, password=hash_password(args.password), role="ADMIN", is_active=True)
            db.add(user); action = "created"
        db.commit(); db.refresh(user)
        print(f"Administrator {action}: user_id={user.id}, email={user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
