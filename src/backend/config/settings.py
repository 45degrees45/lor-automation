import os

GCP_PROJECT = os.environ.get("GCP_PROJECT", "lor-automation")
AWS_SECRET_NAME = os.environ.get("AWS_SECRET_NAME", "aws-bedrock-credentials")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "us.anthropic.claude-sonnet-4-6-20250630-v1:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "ap-south-1")
CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "/data/chroma")
COLLECTION_NAME = "approved_letters"
FIRESTORE_TOKEN_LOGS = "token_logs"
FIRESTORE_WRITING_RULES = "writing_rules"
FIRESTORE_DOC_REGISTRY = "doc_registry"
