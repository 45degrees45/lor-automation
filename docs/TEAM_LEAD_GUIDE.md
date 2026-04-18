# Team Lead Guide — How Your Feedback Trains the System

## Your Role in the Self-Improvement Loop

Every comment you leave in Google Docs becomes a training signal.
The system reads your comments weekly and updates its writing rules automatically.

---

## How to Give Feedback (That the System Learns From)

### Use Comments, Not Suggestions
- ✅ **Insert > Comment** (Ctrl+Alt+M) — the system reads these
- ❌ Suggesting mode edits — the system cannot parse these as structured feedback

### Be Specific in Comments
The more specific your comment, the better the system learns.

**Good comments:**
- "This sentence is too vague — always include a specific metric like % improvement or citations count"
- "EB-1A letters must establish recommender independence from the petitioner in paragraph 1"
- "The impact statement needs to reference US benefit explicitly for NIW"

**Comments the system can't learn from:**
- "Fix this"
- "Rewrite"
- "Not good"

### Tag the LOR Type in Critical Comments (optional)
If a rule applies to one type only, prefix with the type:
- `[EB1A]` This phrasing is too weak for extraordinary ability claims
- `[NIW]` Always tie the contribution to a national problem in paragraph 2

---

## Weekly Feedback Cycle

Every Monday at 9 AM, the system:
1. Collects all your comments from the past 7 days
2. Asks Claude to summarize them into writing rules
3. Updates the rules used in all future generations
4. Adds fully approved letters to the knowledge base

You'll see quality improve gradually — this is expected and by design.

---

## Approving a Letter

When a letter is ready to send:
1. Resolve all your comments in the Google Doc
2. Add a final comment: `[APPROVED]`

This tells the system the letter is a gold example and adds it to the training library.
