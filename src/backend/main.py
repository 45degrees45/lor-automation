import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import firestore

from generator import generate_lor
from rag import retrieve_examples
from rules import get_rules
from tracker import log_usage
from gdocs import read_doc_text, extract_doc_id

app = FastAPI(title="LOR Automation API")
db = firestore.Client()

class GenerateRequest(BaseModel):
    lor_type: str          # EB1A | NIW | O1A
    customer_doc_url: str
    recommender_name: str
    recommender_title: str
    recommender_org: str
    employee_email: str

class GenerateResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    try:
        doc_id = extract_doc_id(req.customer_doc_url)
        customer_profile = read_doc_text(doc_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read customer doc: {e}")

    try:
        rag_examples = retrieve_examples(query=customer_profile[:500], lor_type=req.lor_type, n=3)
        writing_rules = get_rules(db, req.lor_type)

        result = generate_lor(
            lor_type=req.lor_type,
            customer_profile=customer_profile,
            rag_examples=rag_examples,
            writing_rules=writing_rules,
            recommender_name=req.recommender_name,
            recommender_title=req.recommender_title,
            recommender_org=req.recommender_org,
        )

        cost = log_usage(
            db=db,
            employee_email=req.employee_email,
            doc_id=doc_id,
            lor_type=req.lor_type,
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            model_id=os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6-20250630-v1:0"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")

    return GenerateResponse(
        text=result["text"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        cost_usd=cost,
    )
