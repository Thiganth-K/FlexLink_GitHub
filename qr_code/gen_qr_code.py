import qrcode
import sqlite3

# Connect to SQLite database
conn = sqlite3.connect('leave_requests.db')  # Update with your actual database file
cursor = conn.cursor()

# Fetch data from SQLite table
cursor.execute("SELECT * FROM leave_requests WHERE id = 1")  # Modify the query as needed
row = cursor.fetchone()

# Check if the query returned any results
if row is not None:
    # Prepare the data for the QR code
    data = {
        'student_name': row[1],
        'reason': row[2],
        'start_time': row[3],
        'end_time': row[4],
        'approval_status': row[5],
        'approval_timestamp': row[6],
        'form_id': row[0]  # Form ID for easy lookup
    }

    # Convert the data to a string format (can be JSON or custom format)
    data_str = str(data)

    # Generate QR code
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(data_str)
    qr.make(fit=True)

    # Create and save the QR code image
    img = qr.make_image(fill='black', back_color='white')
    img.save('leave_request_qr.png')

    print("QR code generated and saved as 'leave_request_qr.png'")

else:
    print("No data found for the provided ID")

# Close connection
conn.close()
