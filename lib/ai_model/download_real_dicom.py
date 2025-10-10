import urllib.request

url = "https://zenodo.org/records/7972689/files/CT_small.dcm?download=1"
out_path = "sample.dcm"

print("Downloading real DICOM file...")

try:
    urllib.request.urlretrieve(url, out_path)
    print("✓ sample.dcm downloaded successfully.")
except Exception as e:
    print("Download failed:", e)
