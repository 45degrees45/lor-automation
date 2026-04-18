#!/bin/bash
set -e

PROJECT_ID="lor-automation"
REGION="asia-south1"
SA_NAME="lor-backend"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Creating GCP project..."
gcloud projects create $PROJECT_ID --name="LOR Automation" || echo "Project may already exist"
gcloud config set project $PROJECT_ID

echo "Enabling billing..."
echo "Go to: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
read -p "Press enter once billing is enabled..."

echo "Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  docs.googleapis.com \
  drive.googleapis.com \
  --project=$PROJECT_ID

echo "Creating service account..."
gcloud iam service-accounts create $SA_NAME \
  --display-name="LOR Backend" \
  --project=$PROJECT_ID || echo "SA may already exist"

for ROLE in roles/datastore.user roles/secretmanager.secretAccessor roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE"
done

echo "Creating Firestore database..."
gcloud firestore databases create --location=$REGION --project=$PROJECT_ID || echo "Firestore may already exist"

echo "✓ Setup complete."
echo "Next: gcloud secrets create aws-bedrock-credentials --project=$PROJECT_ID"
echo "      gcloud secrets versions add aws-bedrock-credentials --data-file=aws_credentials.json"
