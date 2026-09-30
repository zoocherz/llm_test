# Provider adapter contract v1

## Scope

This is a new v1 contract. It does not reuse the legacy Provider table and never persists a raw key.

## Credential reference

A ModelRoute configuration may reference a local environment variable only as env:VARIABLE_NAME. The resolver reads the value at execution time. API responses, snapshots, exports and logs contain the reference at most, never the resolved value.

## Normalized request

A generation request contains model, text prompt, optional image bytes already encoded as base64 with a validated MIME type, temperature and output-token limit.

## Provider mappings

- Google Gemini: POST v1beta/models/{model}:generateContent; images become Part.inlineData with mimeType and base64 data.
- OpenRouter: POST api/v1/chat/completions; images become OpenAI-compatible image_url content entries with data:{mime};base64,{bytes}.

The mappings are asserted by offline contract tests. Live HTTP calls, retries and response normalization are added only after the credential-reference API is connected to ModelRoute.

## Sources

- Google Gemini generateContent API: https://ai.google.dev/api/generate-content
- OpenRouter image inputs: https://openrouter.ai/docs/guides/overview/multimodal/image-understanding
- OpenRouter chat completions: https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request
