// Replace YOUR-CLOUD-RUN-URL with the actual URL after deploying with scripts/deploy.sh
const BACKEND_URL = "https://YOUR-CLOUD-RUN-URL";

function onOpen() {
  DocumentApp.getUi()
    .createAddonMenu()
    .addItem("Open LOR Generator", "showSidebar")
    .addToUi();
}

function showSidebar() {
  const html = HtmlService.createHtmlOutputFromFile("sidebar")
    .setTitle("LOR Generator")
    .setWidth(320);
  DocumentApp.getUi().showSidebar(html);
}

function generateLOR(formData) {
  const doc = DocumentApp.getActiveDocument();
  const employeeEmail = Session.getActiveUser().getEmail();

  const payload = {
    lor_type: formData.lorType,
    customer_doc_url: formData.customerDocUrl,
    recommender_name: formData.recommenderName,
    recommender_title: formData.recommenderTitle,
    recommender_org: formData.recommenderOrg,
    employee_email: employeeEmail,
  };

  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    headers: {
      Authorization: "Bearer " + ScriptApp.getIdentityToken(),
    },
    muteHttpExceptions: true,
  };

  const response = UrlFetchApp.fetch(BACKEND_URL + "/generate", options);
  const code = response.getResponseCode();

  if (code !== 200) {
    throw new Error("Backend error " + code + ": " + response.getContentText());
  }

  const result = JSON.parse(response.getContentText());

  const body = doc.getBody();
  body.appendPageBreak();
  body.appendParagraph("--- GENERATED DRAFT ---").setHeading(DocumentApp.ParagraphHeading.HEADING2);
  body.appendParagraph(result.text);

  return {
    inputTokens: result.input_tokens,
    outputTokens: result.output_tokens,
    costUsd: result.cost_usd,
  };
}
