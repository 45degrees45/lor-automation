import json
from aws_auth import get_bedrock_client
from config.settings import BEDROCK_MODEL_ID

LOR_DESCRIPTIONS = {
    "EB1A": "EB-1A Extraordinary Ability (prove top percentage globally)",
    "NIW": "EB-2 National Interest Waiver (substantial merit + US national benefit)",
    "O1A": "O-1A Extraordinary Ability temporary visa (sustained acclaim + critical role)",
}


def build_prompt(
    lor_type: str,
    customer_profile: str,
    rag_examples: list,
    writing_rules: list,
    recommender_name: str,
    recommender_title: str,
    recommender_org: str,
) -> str:
    examples_block = "\n\n---\n\n".join(rag_examples) if rag_examples else "None available."
    rules_block = "\n".join(f"- {r}" for r in writing_rules) if writing_rules else "None yet."

    return f"""You are an expert immigration attorney drafting a Letter of Recommendation.

LETTER TYPE: {LOR_DESCRIPTIONS.get(lor_type, lor_type)}

WRITING RULES (follow these strictly):
{rules_block}

APPROVED EXAMPLE LETTERS (use as style and structure reference):
{examples_block}

RECOMMENDER:
Name: {recommender_name}
Title: {recommender_title}
Organization: {recommender_org}

PETITIONER PROFILE:
{customer_profile}

Write a complete, professional Letter of Recommendation. Start directly with the date line. Do not include any commentary or explanation outside the letter itself."""


def generate_lor(
    lor_type: str,
    customer_profile: str,
    rag_examples: list,
    writing_rules: list,
    recommender_name: str,
    recommender_title: str,
    recommender_org: str,
) -> dict:
    client = get_bedrock_client()
    prompt = build_prompt(
        lor_type, customer_profile, rag_examples,
        writing_rules, recommender_name, recommender_title, recommender_org
    )

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}]
    })

    response = client.invoke_model(modelId=BEDROCK_MODEL_ID, body=body)
    result = json.loads(response["body"].read())

    return {
        "text": result["content"][0]["text"],
        "input_tokens": result["usage"]["input_tokens"],
        "output_tokens": result["usage"]["output_tokens"],
    }
