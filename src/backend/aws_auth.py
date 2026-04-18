import json
import boto3
from config.settings import GCP_PROJECT, AWS_SECRET_NAME, BEDROCK_REGION, BEDROCK_MODEL_ID


def get_aws_credentials() -> dict:
    """Fetch AWS credentials from GCP Secret Manager."""
    from google.cloud import secretmanager
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT}/secrets/{AWS_SECRET_NAME}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return json.loads(response.payload.data.decode("utf-8"))


def get_bedrock_client():
    """Return a boto3 bedrock-runtime client using credentials from Secret Manager."""
    creds = get_aws_credentials()
    return boto3.client(
        "bedrock-runtime",
        region_name=creds.get("region_name", BEDROCK_REGION),
        aws_access_key_id=creds["aws_access_key_id"],
        aws_secret_access_key=creds["aws_secret_access_key"],
    )
