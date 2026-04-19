# Evaluation Rubric

Version: `summary-eval-v1`

Use this rubric exactly. Do not invent alternative criteria, scales, or key names.

## Scope

Evaluate each markdown summary file against the single `.txt` file in the same directory.

Judge the summary on five criteria only:
- `accuracy`
- `completeness`
- `clarity`
- `faithfulness_to_source_prompt`
- `actionability`

All criterion scores must be integers from `0` to `5`.

`overall_score` must be a number from `0` to `5`. It should reflect the overall quality of the summary under this rubric. It does not need to equal the arithmetic mean exactly, but it should be directionally consistent with the five criterion scores.

## Scoring Scale

Use the same meaning for `0` to `5` across all criteria:
- `0`: fails completely
- `1`: very poor
- `2`: weak
- `3`: acceptable
- `4`: strong
- `5`: excellent

## Criterion Definitions

### `accuracy`

How correct the summary is relative to the source text.

- `5`: all material claims are correct; no distortions or invented details
- `4`: minor imprecision, but meaning is still correct
- `3`: mostly correct, with a few notable inaccuracies or overstatements
- `2`: multiple inaccuracies, misleading framing, or unsupported claims
- `1`: largely inaccurate or mostly unsupported
- `0`: fabricated, self-contradictory, or completely detached from the source

### `completeness`

How much of the important source content is covered.

- `5`: captures all major points, decisions, and important details
- `4`: captures most important points; only minor omissions
- `3`: covers the core idea but misses several important details
- `2`: partial coverage; major omissions
- `1`: barely covers the source
- `0`: no meaningful coverage of source content

### `clarity`

How easy the summary is to read and understand.

- `5`: very clear, well-structured, and easy to follow
- `4`: clear with only minor awkwardness
- `3`: understandable but somewhat vague, repetitive, or clumsy
- `2`: hard to follow in places
- `1`: very confusing or poorly written
- `0`: unreadable or incoherent

### `faithfulness_to_source_prompt`

How well the output actually performs the requested task and stays grounded in the provided source.

- `5`: directly fulfills the task exactly as requested and stays grounded in the source
- `4`: fulfills the task well with only small deviations
- `3`: mostly follows the task but misses some expected behavior
- `2`: partially follows the task but drifts or stays generic
- `1`: weakly connected to the requested task
- `0`: does not perform the requested task in substance

### `actionability`

How useful the summary is for someone who needs to act on it or make a decision from it.

- `5`: highly useful; preserves key decisions, next steps, owners, risks, or implications
- `4`: useful with minor missing practical detail
- `3`: somewhat useful but missing important practical takeaways
- `2`: limited practical value
- `1`: nearly useless for action or decision-making
- `0`: no practical value

## Source-Gap Rule

If the `.txt` file does not actually contain the information needed for the requested task, score based on how the summary handles that limitation.

Examples:
- If the prompt says "Summarize the meeting notes" but no meeting notes are present, a placeholder summary should score poorly on `accuracy`, `completeness`, `faithfulness_to_source_prompt`, and `actionability`.
- If a summary clearly and honestly signals that the source is missing required information, that may improve `accuracy` and `faithfulness_to_source_prompt`, but it still cannot score highly on `completeness` or `actionability`.

Do not reward generic filler text.

## Strengths And Weaknesses

For each file:
- `strengths` should contain short concrete observations tied to the rubric
- `weaknesses` should contain short concrete observations tied to the rubric
- `notes` should explain the score in 1 to 3 sentences without referring to any hidden context

## Ranking Rules

Rank all summaries from best to worst.

Primary rule:
- Better summaries rank higher.

Tie-break rules, in order:
- higher `overall_score`
- higher `accuracy`
- higher `faithfulness_to_source_prompt`
- higher `completeness`
- higher `actionability`
- higher `clarity`
- if still tied, rank filenames in ascending alphabetical order

Ranks must start at `1` and contain no gaps.

## Output Discipline

Return only the JSON object required by the driver.
Do not include Markdown fences.
Do not include explanatory text before or after the JSON.
