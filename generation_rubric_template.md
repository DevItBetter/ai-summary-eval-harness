# Generation Rubric

Version: `summary-generate-v1`

Use this rubric exactly when generating a summary.

## Goal

Produce one concise markdown summary from the provided source text.

## Requirements

- Be faithful to the source text.
- Do not invent facts, decisions, dates, owners, risks, blockers, or next steps that are not supported by the source.
- Prefer direct, plain language.
- Keep the summary compact and easy to evaluate later.
- Use markdown.
- Do not mention the model, the prompt, the rubric, or the generation process.

## Missing-Information Rule

If the source text does not contain enough information to produce a substantive summary:
- do not fabricate content
- produce the most faithful minimal summary possible
- it is acceptable to state that the source lacks enough detail, if needed

## Style

- Aim for one short heading and one concise paragraph or a short bullet list.
- Avoid unnecessary flourish.
- Avoid repetition.
