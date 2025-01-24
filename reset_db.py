from app import app, db  # Replace 'app' with your Flask app file name
with app.app_context():
    db.drop_all()  # Drops all the tables
    db.create_all()  # Recreates the tables
    print("Database reset successfully!")