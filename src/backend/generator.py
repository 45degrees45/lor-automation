import json
from aws_auth import get_bedrock_client
from config.settings import BEDROCK_MODEL_ID

LOR_DESCRIPTIONS = {
    "EB1A": "EB-1A Extraordinary Ability (prove top percentage globally)",
    "NIW": "EB-2 National Interest Waiver (substantial merit + US national benefit)",
    "O1A": "O-1A Extraordinary Ability temporary visa (sustained acclaim + distinguished contributions)",
    "OC": "Original Contribution letter — prove the petitioner created something novel that advances the field",
}

# Special 9-pillar structure for Original Contribution letters
OC_PILLARS = """
1. RECOMMENDER INTRODUCTION — Establish the recommender's credentials and clarify their professional
   relationship with the petitioner early. Be specific about how and when they encountered the work.

2. EXPLAIN THE ORIGINAL CONTRIBUTION (OC) — Describe what the OC is in clear, accessible language.
   What does it do? What problem does it solve?

3. NOVELTY OF THE OC — Explain what solutions existed before this OC. What was the state of the art?
   Be specific about the prior approaches and their limitations.

4. LOOP HOLES IN PRIOR SOLUTIONS — What were the specific gaps, failures, or limitations in existing
   approaches? How did those shortcomings affect practitioners, companies, or end users?

5. HOW THE OC SOLVED THOSE ISSUES — Precisely describe how the petitioner's approach addressed each
   gap. What was the technical or methodological insight that made this possible?

6. IMPACT WITHIN THE COMPANY — If developed at a company, describe the internal adoption and impact
   with quantifiable metrics (efficiency gains %, cost savings $, users affected, time saved, etc.).

7. MAJOR SIGNIFICANCE IN THE FIELD — Shift focus outward. How is this OC influencing the broader
   industry or research community? Citations, adoptions, derivative works, press coverage.

8. BLUEPRINT FOR THE INDUSTRY — Explain how other organizations could adopt or adapt this OC.
   How does it serve as a model or template? What would they gain by implementing it?
   Optionally reference industry trends or government reports that validate the urgency of this work.

9. FORWARD-LOOKING US BENEFIT — Wrap with a visionary paragraph. How will the petitioner's continued
   work help the US stay competitive? Connect to US economic, technological, or healthcare security
   priorities. Reinforce that this person is not filling a job — they are shaping the future of the field.
"""

# USCIS adjudicators flag these overused phrases — never use them
BANNED_PHRASES = [
    "critical role", "key role", "pivotal role", "instrumental role",
    "indispensable", "irreplaceable", "unique talent", "exceptional talent",
    "invaluable contribution", "vital contribution",
]

# Tone guide by recommender seniority — same facts, different voice
SENIORITY_TONE = {
    "manager": (
        "RECOMMENDER SENIORITY: Manager / Team Lead\n"
        "Tone: Operational and direct. Write from close daily observation. "
        "Use first-person specifics ('I assigned him this problem because...', 'I watched her debug...'). "
        "Focus on execution quality, technical depth, and team influence. "
        "Avoid strategic or board-level language — this voice saw the work happen."
    ),
    "director": (
        "RECOMMENDER SENIORITY: Director\n"
        "Tone: Strategic and cross-functional. Write from departmental oversight. "
        "Reference how the work affected multiple teams or business lines. "
        "Balance technical credibility with organizational impact. "
        "Use language like 'I oversaw...', 'across the teams I lead...', 'this shaped our department strategy...'. "
        "Show that the recommender understands both the technical and business significance."
    ),
    "vp": (
        "RECOMMENDER SENIORITY: VP / Senior VP\n"
        "Tone: Executive and industry-aware. Write from company-wide and competitive perspective. "
        "Reference how the work influenced company strategy, competitive positioning, or market outcomes. "
        "Use language like 'In my role overseeing...', 'this directly shaped our company direction...'. "
        "Less about daily observation, more about strategic consequence and organizational value."
    ),
    "c_level": (
        "RECOMMENDER SENIORITY: C-Level (CTO, CEO, Chief Scientist, etc.)\n"
        "Tone: Authoritative, industry-wide, and visionary. Write from the highest organizational vantage point. "
        "Reference industry trends, national/global importance, and long-term strategic value. "
        "Use language like 'In my decades in this field...', 'this contribution advances the state of the art...'. "
        "Connect the work to the organization's mission and the broader industry landscape. "
        "This voice rarely sees daily work — focus on outcomes, reputation, and field-level significance."
    ),
    "professor": (
        "RECOMMENDER SENIORITY: Professor / Academic Advisor\n"
        "Tone: Scholarly, field-specific, and comparative. Write from academic expertise and research context. "
        "Compare the petitioner to peers in the field, not just within one organization. "
        "Reference publications, conferences, citations, and methodological contributions. "
        "Use language like 'In my research group...', 'compared to PhD students and postdocs I have supervised...'. "
        "Establish the recommender's own credentials prominently — academic letters depend on recommender authority."
    ),
    "industry_expert": (
        "RECOMMENDER SENIORITY: Independent Industry Expert\n"
        "Tone: Objective, field-wide, and authoritative. This is the most powerful LOR type for EB-1A. "
        "Emphasize that the recommender knows the petitioner through their public work, NOT through employment. "
        "Write from the perspective of someone who encountered the work independently. "
        "Use language like 'I became aware of their work through...', 'without any personal relationship...'. "
        "Focus on reputation, field-wide adoption, and influence on peers the recommender has never met."
    ),
}

DEFAULT_SENIORITY_TONE = (
    "Tone: Professional and specific. Balance operational detail with strategic context."
)

# The 10 content pillars every strong LOR must address
LOR_PILLARS = """
1. PROJECT OVERVIEW — What the project is, its scope, and the petitioner's specific position in it.
2. ORGANIZATIONAL CRITICALITY — Why this project was essential to the organization, with concrete stakes.
3. SIGNIFICANT CONTRIBUTION — Exactly what the petitioner personally built, designed, or discovered.
   Use: "X made a significant contribution to this project by [specific action]..."
   Never use: "critical role", "key role", "pivotal role", or similar vague phrases.
4. CHALLENGES AND SOLUTIONS — What was technically hard, what prior approaches failed, what the petitioner innovated.
5. SUCCESS METRICS — Quantified outcomes only. Numbers, percentages, scale, revenue, citations.
6. DEVASTATING CONSEQUENCE — What would break or regress if this person's contributions were removed.
7. DISTINCTION FROM PEERS — What makes this person rare in the field (awards, invitations, recognitions).
8. ORGANIZATION-WIDE IMPACT — How the work spread beyond the immediate team across the organization.
9. INDUSTRY-WIDE IMPACT — How the work matters to the broader field, not just the employer (open source, papers, standards).
10. US BENEFIT — How the petitioner's continued work in the United States serves national interests.
"""


def build_prompt(
    lor_type: str,
    customer_profile: str,
    rag_examples: list,
    writing_rules: list,
    recommender_name: str,
    recommender_title: str,
    recommender_org: str,
    recommender_seniority: str = "director",
) -> str:
    examples_block = "\n\n---\n\n".join(rag_examples) if rag_examples else "None available."
    rules_block = "\n".join(f"- {r}" for r in writing_rules) if writing_rules else "None yet."
    banned_block = "\n".join(f'- "{p}"' for p in BANNED_PHRASES)
    tone_block = SENIORITY_TONE.get(recommender_seniority.lower(), DEFAULT_SENIORITY_TONE)
    pillars_block = OC_PILLARS if lor_type == "OC" else LOR_PILLARS

    return f"""You are an expert immigration attorney drafting a Letter of Recommendation for a US visa petition.

LETTER TYPE: {LOR_DESCRIPTIONS.get(lor_type, lor_type)}

{tone_block}

BANNED PHRASES — never use these (USCIS adjudicators flag them as boilerplate):
{banned_block}

REQUIRED CONTENT PILLARS — the letter must address all of these in order:
{pillars_block}

TEAM LEAD WRITING RULES (follow these strictly):
{rules_block}

APPROVED EXAMPLE LETTERS (use as style and structure reference — do not copy verbatim):
{examples_block}

RECOMMENDER:
Name: {recommender_name}
Title: {recommender_title}
Organization: {recommender_org}

PETITIONER PROFILE (use all facts provided — do not invent any):
{customer_profile}

Write a complete, professional Letter of Recommendation.
- Start directly with the date line (no preamble)
- Address all 10 content pillars naturally within flowing paragraphs — do not use numbered headings
- Adopt the tone and voice appropriate for the recommender's seniority level
- Every claim must be supported by a specific fact from the profile
- Quantify every impact statement
- Do not include any commentary outside the letter itself"""


def generate_lor(
    lor_type: str,
    customer_profile: str,
    rag_examples: list,
    writing_rules: list,
    recommender_name: str,
    recommender_title: str,
    recommender_org: str,
    recommender_seniority: str = "director",
) -> dict:
    client = get_bedrock_client()
    prompt = build_prompt(
        lor_type, customer_profile, rag_examples,
        writing_rules, recommender_name, recommender_title, recommender_org,
        recommender_seniority,
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
