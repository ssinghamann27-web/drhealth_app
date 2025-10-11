import onnxruntime as ort
import numpy as np

def predict_xray(image_np):
    session = ort.InferenceSession('lib/ai_model/models/xray_model.onnx')
    outputs = session.run(None, {'input': image_np})
    return outputs

def predict_lab(features):
    import pickle
    with open('lib/ai_model/models/lab_model.pkl','rb') as f:
        model = pickle.load(f)
    return model.predict([features])
