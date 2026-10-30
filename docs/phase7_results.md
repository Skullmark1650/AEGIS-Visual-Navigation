# Phase 7 AI analysis: implementation and validation status

2026-10-28, America/Chicago. Phase 7 implementation and bounded acceptance testing are complete for research use. A funded OpenAI request successfully analyzed selected camera pixels and explained a documented navigation discontinuity using real telemetry. Local diagnostics and mocked API tests remain separately identified. Recommendations require engineering review; no automated configuration or control changes are permitted. Phase 8 has not started.

## Implemented

`laptop.ai_assistant` reads operator-selected telemetry under results/reports, summarizes a bounded elapsed-time window, measures selected image texture locally, optionally compares a second run, and produces JSON, Markdown, and a measured pose-status SVG. Local-only mode makes no network requests. Current configuration snapshots are identified as current, not historical proof of the original run configuration. Operator test conditions are identified as reports rather than verified measurements.

Cloud mode uses an explicit model ID, an environment API key, and one optionally selected image resized to at most 640 x 480, JPEG quality 75, and 300,000 bytes. It sends only the bounded summary and that selected image, not raw logs or continuous video. The original/uploaded image hashes, model identifier, prompt version, limits, returned token usage, tool calls, status, and response elapsed time are recorded. No key is recorded.

The dashboard adds Diagnose last 10 s (local) and Analyze frame (OpenAI upload). Work runs in a background thread and does not run in the navigation estimator. Only one analysis task is active per dashboard. A failure reports its exception class without displaying provider bodies or secrets. Successful results are saved as separate experiment reports; the on-screen status shows their path.

The model's tool allowlist contains only get_selected_telemetry and get_selected_frame_metadata, with no arguments and no model-controlled paths. Unknown tools/arguments are rejected. It cannot change configuration or execute shell commands. Selected image pixels are provided directly with explicit cloud selection; no image retrieval tool accepts arbitrary filesystem paths. Model interpretations are kept separate from measured data and local deterministic explanations.

API limits: default three HTTP requests per UTC day, configurable from one to twenty; at most three requests and two read-only tool continuations per analysis; default 800 output tokens per response, configurable 128–2000; 45-second timeout, bounded response size, and no automatic retries. A SQLite transaction reserves each request before sending, including failed requests. These are application request/output limits, not a provider monetary hard cap. Persistent budget data is local to this checkout; it is not a shared account-wide billing limit.

## Measured local evidence

The real Phase 6 interruption CSV contains 517 frames, a maximum receipt gap of 4.781 seconds, and a frame-gap reset. The local explanation correctly reports that discontinuity and distinguishes it from proof of the transport/capture root cause. It also explains baseline waiting, homography ambiguity, and low-parallax rejection without inventing a distance or trajectory accuracy.

Artifact `results/reports/phase7-local-evidence` contains the real interruption analysis and comparison against the uninterrupted Phase 6 run. Its selected checkerboard image is explicitly from a different calibration session, not claimed to depict the interruption. Local scene measurement found 277 Shi-Tomasi features. This is an image-quality measurement, not semantic AI scene understanding.

Three local telemetry-plus-image measurements averaged 68.754 ms in `results/reports/phase7-local-benchmark.json`. This excludes cloud inference and report disk output; it is not API latency. All 49 automated tests passed, including read-scope checks, allowlist rejection, persistent quota enforcement, missing-key failure before network access, mocked tool-call continuation, incomplete-response rejection, real interruption evidence, local scene measurement, and report overwrite prevention. Mock API results are explicitly labeled MOCK ONLY in tests.

## Funded real AI acceptance test

Artifact: `results/reports/phase7-funded-ai-test` (report.json, report.md, pose-statuses.svg, review.json). Requested model gpt-5.4-mini; returned model **gpt-5.4-mini-2026-03-17**; prompt **aegis-diagnostics-v1**. The one HTTP inference request completed successfully in **8.2186 seconds**, measured around the analysis call. Provider usage was **1,685 input tokens and 1,180 output tokens, 2,865 total**, with zero reported reasoning tokens. The configured output limit was 2,000 tokens. No price or billing charge is inferred from token counts.

A single **640 x 480 JPEG, 32,176 bytes**, derived from calibration view 12, was uploaded with low image detail. Its source and uploaded hashes are in report.json. It was accompanied by the selected 40-second telemetry summary and explicitly labeled operator conditions. The image is from a separate calibration session and is not evidence of the interruption scene at the time of failure.

The response correctly cited 517 frames, the 4.781-second receipt gap, ten sequence gaps, one frame-gap reset, six accepted poses, and the remaining pose-status counts. It explained that the observed gap and reset are consistent with the documented pause/recovery but do not by themselves identify the mechanism. This meets the requirement to explain a documented failure using real telemetry.

The scene description correctly identified the checkerboard, brick wall, upholstered seating, and smooth low-texture regions. It suggested checkerboard corners and high-contrast edges as useful image features and repeated texture as a potential matching difficulty. This was a qualitative inspection of one frame, not a semantic benchmark or reliability estimate.

**Engineering review found limitations.** The suggestion of mounting-frame occlusion was unsupported: the checkerboard is fully visible and all 54 corners were detected. Its suggestion to move the checkerboard is not an appropriate camera-ego-motion validation experiment; move the camera through a stationary multi-depth scene instead. The separate image and telemetry must not be causally linked. These corrections are recorded beside the original unmodified AI response in the reviewed report. No AI recommendation changed any configuration or executed an action.

The live response made zero function calls because its selected evidence was already included. Read-only tool execution, continuation handling, and rejection of unknown tools are verified with mocks; a real model tool-call invocation is not claimed. All **49 automated tests passed** after the final error-handling changes. No additional cloud requests were made for those tests.

The three-request UTC-day application budget was reached by two prior failed generation attempts and this successful inference. Failed attempts count by design. Further same-day inference will report the local request limit unless the operator intentionally changes its configured budget; no automatic retries occur.

## Use and data handling

```powershell
.\.venv\Scripts\python.exe -m laptop.ai_assistant --telemetry results/reports/viewer-20261028-231556.csv --seconds 40 --output results/reports/new-local-analysis
```

Add `--image data/calibration/session-20261028-211233/view-0012.png` for local texture measurement. Add `--cloud --model YOUR_VISION_MODEL_ID` to explicitly send the selected evidence to OpenAI. The API key is read from OPENAI_API_KEY; AEGIS_AI_MODEL can provide the model ID. On Windows, user environment variables are read when newly configured values are absent from the running process. API keys are not copied to the Pi.

`scripts/configure_ai_key.ps1` accepts hidden input and stores the key as a Windows user environment variable. This is not a secrets vault; processes with access to that Windows account can access its environment settings. The project writes no key file and ignores .env files.

Cloud requests use store=false. This is not a guarantee of zero provider retention. Uploaded scene pixels can contain private surroundings; choose frames deliberately. Local snapshots, selected telemetry, summaries, and AI replies are saved under ignored results paths until the operator removes them. No automatic upload occurs when starting the dashboard or running local diagnostics.

Official implementation references: [OpenAI vision input guide](https://developers.openai.com/api/docs/guides/images-vision?api-mode=responses) and [API quickstart](https://developers.openai.com/api/docs/quickstart). API availability, permissions, and usage depend on the configured account and chosen model.


## Authenticated API test outcome

The replacement key authenticated successfully against the model-list endpoint.
The account lists gpt-5.4-mini as available, and AEGIS_AI_MODEL is configured
to that model. A generation request returned HTTP 429 with error code
credit_balance_exhausted and type insufficient_quota. The diagnostic result is
saved in results/reports/phase7-api-preflight.json. Two generation attempts
were reserved against the local three-request daily budget; failed requests
count against that limit. No successful inference, returned token usage,
semantic-scene result, or inference latency is claimed.

The provider error is now sanitized into a typed application error, and the
dashboard explains exhausted credits while leaving the camera running. A new
regression test verifies the safe error code without displaying provider bodies.
The user then added API credits. The successful funded test above supersedes
this historical billing blocker; it is retained as diagnostic history.
Phase 8 has not started.
