from PIL import Image, ImageDraw

# Create a white image
img = Image.new("RGB", (800, 400), color="white")

# Draw text like a lab report
draw = ImageDraw.Draw(img)
text = """Patient Name: John Doe
Age: 32

Hemoglobin: 11.2 g/dL
WBC: 13.5 x10^9/L
Platelets: 410 x10^9/L
Glucose: 108 mg/dL
Creatinine: 1.1 mg/dL
Sodium: 140 mmol/L
Potassium: 3.2 mmol/L"""

draw.text((20, 20), text, fill="black")

# Save it
img.save("lab_photo.jpg")
print("Real lab_photo.jpg created.")

