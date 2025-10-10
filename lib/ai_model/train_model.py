import os
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks

# ✅ Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAIN_DIR = os.path.join(BASE_DIR, "dataset", "train")
VAL_DIR   = os.path.join(BASE_DIR, "dataset", "val")

IMG_SIZE = (180, 180)
BATCH = 32
EPOCHS = 10

# ✅ Load datasets
train_ds = tf.keras.utils.image_dataset_from_directory(
    TRAIN_DIR, image_size=IMG_SIZE, batch_size=BATCH, label_mode="int", seed=42
)
val_ds = tf.keras.utils.image_dataset_from_directory(
    VAL_DIR, image_size=IMG_SIZE, batch_size=BATCH, label_mode="int", seed=42
)

print("Classes:", train_ds.class_names)  # expect ['NORMAL', 'PNEUMONIA']

# ✅ Performance optimization
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.shuffle(1000).cache().prefetch(AUTOTUNE)
val_ds   = val_ds.cache().prefetch(AUTOTUNE)

# ✅ Data Augmentation
data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.05),
    layers.RandomZoom(0.05),
])

# ✅ Model
model = models.Sequential([
    data_augmentation,
    layers.Rescaling(1./255, input_shape=(*IMG_SIZE, 3)),
    layers.Conv2D(32, 3, activation='relu'),
    layers.MaxPooling2D(),
    layers.Conv2D(64, 3, activation='relu'),
    layers.MaxPooling2D(),
    layers.Conv2D(128, 3, activation='relu'),
    layers.MaxPooling2D(),
    layers.Dropout(0.25),
    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.25),
    layers.Dense(2, activation='softmax'),
])

# ✅ Compile
model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# ✅ Callbacks
ckpt = callbacks.ModelCheckpoint(
    filepath=os.path.join(BASE_DIR, "pneumonia_best.keras"),
    monitor="val_accuracy", save_best_only=True, mode="max", verbose=1
)
early = callbacks.EarlyStopping(patience=3, restore_best_weights=True)

# ✅ Train
history = model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, callbacks=[ckpt, early])

# ✅ Save final model
save_path = os.path.join(BASE_DIR, "pneumonia_model.keras")
model.save(save_path)
print("Saved:", save_path)

