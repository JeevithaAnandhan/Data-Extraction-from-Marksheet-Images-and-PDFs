from app import app, db, User

def check_users():
    with app.app_context():
        print("=== ALL USERS IN DATABASE ===")
        users = User.query.all()
        
        if not users:
            print("❌ NO USERS FOUND!")
            return
            
        for user in users:
            print(f"ID: {user.id}")
            print(f"Username: '{user.username}'")
            print(f"Email: '{user.email}'")
            print(f"Has Password: {'Yes' if user.password_hash else 'No'}")
            print(f"Created: {user.created_at}")
            print("---")
            
        print(f"Total users: {len(users)}")

if __name__ == "__main__":
    check_users()
