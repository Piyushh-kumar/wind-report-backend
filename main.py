from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from report_generator import process_wind_assessment

app = FastAPI()

# Allow connections from your frontend website
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WindRequest(BaseModel):
    email: str
    location: str
    mast_height: float = 10.0

@app.post("/generate-report")
def generate_report(req: WindRequest):
    try:
        pdf_file = process_wind_assessment(req.email, req.location)
        return {
            "status": "success",
            "message": f"Wind assessment report generated successfully and dispatched to {req.email}",
            "report_file": pdf_file
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)