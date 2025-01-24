import cv2
import numpy as np
from pyzbar.pyzbar import decode

# Load the image containing the QR code
image = cv2.imread('leave_request_qr.png')  # Update with your QR code image file

# Decode the QR code
decoded_objects = decode(image)

# Loop through all detected QR codes
for obj in decoded_objects:
    # Print the data from the QR code
    print(f"QR Code Data: {obj.data.decode('utf-8')}")

    # Draw a rectangle around the QR code in the image
    rect_points = obj.polygon
    if len(rect_points) == 4:
        pts = [tuple(point) for point in rect_points]
        cv2.polylines(image, [np.array(pts, dtype=np.int32)], True, (0, 0, 255), 5)

# Display the image with the QR code rectangle
cv2.imshow("QR Code Scanner", image)

# Wait for key press and close the window
cv2.waitKey(0)
cv2.destroyAllWindows()
