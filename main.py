from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio


from scraper import get_captcha_and_session, fetch_case_data

from database import engine, queries, cases, orders

SESSIONS = {}
SESSION_ID_COUNTER = 0

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_event():
    for session in SESSIONS.values():
        await session["browser"].close()
        await session["playwright"].stop()

@app.get("/api/captcha")
async def get_new_captcha():
    global SESSION_ID_COUNTER
    session_id = SESSION_ID_COUNTER
    SESSION_ID_COUNTER += 1
    try:
        session_data = await get_captcha_and_session()
        SESSIONS[session_id] = session_data
        return {"session_id": session_id, "captcha_image": session_data["captcha_image"]}
    except Exception as e:
        print(f"Failed to get CAPTCHA: {e}")
        raise HTTPException(status_code=500, detail="Could not connect to the court website.")

@app.post("/api/case-data")
async def get_case_data(payload: dict = Body(...)):
    session_id = payload.get("session_id")
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=400, detail="Invalid or expired session.")

    case_details = {
        "type": payload.get("case_type"),
        "number": payload.get("case_number"),
        "year": payload.get("case_year"),
        "captcha_text": payload.get("captcha_text")
    }

    result = await fetch_case_data(session["page"], case_details)
    
    await session["browser"].close()
    await session["playwright"].stop()
    del SESSIONS[session_id]
    
    db_connection = engine.connect()
    
    
    if result.get("error"):
        db_connection.execute(queries.insert().values(
            case_type=case_details["type"], case_number=case_details["number"],
            case_year=case_details["year"], status="FAILURE"
        ))
        db_connection.commit()
        db_connection.close()
        raise HTTPException(status_code=400, detail=result["error"])

   
    
    
    db_connection.execute(queries.insert().values(
        case_type=case_details["type"], case_number=case_details["number"],
        case_year=case_details["year"], status="SUCCESS",
        raw_response_html=result.get("html", "")
    ))

    parsed_data = result["data"]
    case_identifier = f"{case_details['type']}-{case_details['number']}-{case_details['year']}"

    
    existing_case = db_connection.execute(
        cases.select().where(cases.c.case_identifier == case_identifier)
    ).first()

    if existing_case:
        case_id = existing_case.id
    else:
        
        new_case = db_connection.execute(cases.insert().values(
            case_identifier=case_identifier,
            parties=parsed_data["parties"],
            filing_date=parsed_data["filing_date"],
            next_hearing_date=parsed_data["next_hearing_date"]
        ))
        case_id = new_case.inserted_primary_key[0]

    
    for link in parsed_data.get("pdf_links", []):
        
        link_exists = db_connection.execute(
            orders.select().where(orders.c.pdf_url == link)
        ).first()
        if not link_exists:
            db_connection.execute(orders.insert().values(
                case_id=case_id,
                pdf_url=link,
                order_date="N/A" 
            ))

    db_connection.commit()
    db_connection.close()
    
    
    
    return parsed_data

app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')