from server_fastapi import app

print("✅ Checking FastAPI app...")
print("Total routes:", len(app.routes))
for r in app.routes:
    print("➡️", r.path)
