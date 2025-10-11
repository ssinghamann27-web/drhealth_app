import pickle, numpy as np

with open('lib/ai_model/models/lab_model.pkl','rb') as f:
    model = pickle.load(f)

# Example lab report [glucose, cholesterol, hemoglobin, wbc]
sample = [160, 250, 10.5, 12000]
pred = model.predict([sample])[0]
print('🧪 Lab sample prediction ->', pred)
