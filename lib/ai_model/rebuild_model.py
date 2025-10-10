import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# ✅ Modern input definition
inputs = keras.Input(shape=(180, 180, 3))

x = layers.Conv2D(16, 3, activation='relu')(inputs)
x = layers.MaxPooling2D()(x)
x = layers.Conv2D(32, 3, activation='relu')(x)
x = layers.MaxPooling2D()(x)
x = layers.Flatten()(x)
x = layers.Dense(64, activation='relu')(x)
outputs = layers.Dense(2, activation='softmax')(x)

model = keras.Model(inputs, outputs)

# ✅ Compile
model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

# ⚙️ Optionally retrain quickly
# train_ds = ...
# val_ds = ...
# model.fit(train_ds, validation_data=val_ds, epochs=5)

# ✅ Save in new format
model.save("pneumonia_model.keras", save_format="keras")

print("Model rebuilt and saved successfully")

