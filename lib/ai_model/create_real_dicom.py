# create_real_dicom.py
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
import datetime, os

filename = "sample.dcm"
print("Generating a real DICOM file...")

# Create dummy pixel data (128x128 grayscale)
pixel_array = (np.random.rand(128, 128) * 255).astype(np.uint16)

# --- File Meta Information ---
file_meta = pydicom.dataset.FileMetaDataset()
file_meta.MediaStorageSOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
file_meta.ImplementationClassUID = pydicom.uid.PYDICOM_IMPLEMENTATION_UID
file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian  # ✅ REQUIRED FIX

# --- Dataset ---
ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)
ds.Modality = "CT"
ds.ContentDate = str(datetime.date.today()).replace("-", "")
ds.ContentTime = str(datetime.datetime.now().time()).replace(":", "").split(".")[0]
ds.PatientName = "John Doe"
ds.PatientID = "123456"

# --- Image Data ---
ds.Rows, ds.Columns = pixel_array.shape
ds.SamplesPerPixel = 1
ds.PhotometricInterpretation = "MONOCHROME2"
ds.BitsStored = 16
ds.BitsAllocated = 16
ds.HighBit = 15
ds.PixelRepresentation = 1
ds.PixelData = pixel_array.tobytes()

# --- Save ---
ds.save_as(filename)
print(f"Real DICOM file created successfully: {filename} ({os.path.getsize(filename)} bytes)")


