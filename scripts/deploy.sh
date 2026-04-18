#!/bin/bash
set -e

PROJECT_ID="lor-automation"
REGION="asia-south1"
SERVICE_NAME="lor-backend"
SA_EMAIL="lor-backend@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud run deploy $SERVICE_NAME \
  --source src/backend \
  --project=$PROJECT_ID \
  --region=$REGION \
  --service-account=$SA_EMAIL \
  --set-env-vars="GCP_PROJECT=${PROJECT_ID},BEDROCK_REGION=ap-south-1,BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6-20250630-v1:0" \
  --memory=1Gi \
  --cpu=1 \
  --timeout=120 \
  --no-allow-unauthenticated

URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(status.url)")
echo "✓ Deployed: $URL"

gcloud scheduler jobs create http lor-weekly-feedback \
  --schedule="0 9 * * 1" \
  --time-zone="Asia/Kolkata" \
  --uri="${URL}/feedback" \
  --http-method=POST \
  --oidc-service-account-email=$SA_EMAIL \
  --location=$REGION \
  --project=$PROJECT_ID || echo "Scheduler job may already exist"

echo "✓ Done. Backend URL: $URL"
