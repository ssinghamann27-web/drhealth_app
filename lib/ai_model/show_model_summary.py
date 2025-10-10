from tensorflow import keras

MODEL_PATH = "pneumonia_model.keras"

print("[INFO] Loading model...")
model = keras.models.load_model(MODEL_PATH)
model.summary()
print("[OK] Model loaded successfully!")
