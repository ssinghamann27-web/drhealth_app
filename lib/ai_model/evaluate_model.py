import tensorflow as tf

# ✅ Load your best model
model = tf.keras.models.load_model("pneumonia_best.keras")

# ✅ Load validation dataset
val_ds = tf.keras.utils.image_dataset_from_directory(
    "dataset/val",
    image_size=(180, 180),
    batch_size=32
)

# ✅ Evaluate
loss, acc = model.evaluate(val_ds)
print(f"\nValidation Accuracy: {acc:.4f}")
print(f"Validation Loss: {loss:.4f}")
