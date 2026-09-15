from fastapi import FastAPI, UploadFile, File
import httpx
from datetime import datetime
from biceps_curl import BicepsCurlAPI

app = FastAPI()
biceps_trainer = BicepsCurlAPI()
SAVE_URL = "https://meisterfit-2kex.vercel.app/save-workout"


@app.get("/")
def home():
    return {"status": "Hugging Face Space is Running"}


@app.post("/analyze/biceps")
async def analyze_biceps(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = biceps_trainer.analyze_frame(image_bytes)
    print(
        f"Stage: {result.get('stage')} | Reps: {result.get('reps')} | "
        f"Left: {result.get('left_angle')}° | Right: {result.get('right_angle')}°"
    )
    return result


@app.post("/reset/biceps")
async def reset_biceps():
    data = {
        "_id": str(datetime.utcnow().timestamp()).replace(".", ""),
        "exerciseName": "Biceps Curl",
        "reps": biceps_trainer.rep_count,
        "date": datetime.utcnow().isoformat(),
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(SAVE_URL, json=data)
        print(f"Saved: {data} | Status: {response.status_code}")
    biceps_trainer.reset()
    return {"message": "reset", "saved": data}
