```python 

from backend.scripts.llm_diagnostics import CheckModel, CheckUsage

# 1. Fetch available platforms models
CheckModel.groq_model_check()
CheckModel.gemini_model_check()

# 2. Check rate limits and active day capacity for Groq (using active model)
CheckUsage.groq_rate_limits("openai/gpt-oss-20b")
    
# 3. Check structural parameters for Gemini (using gemini-3.8-flash)
CheckUsage.gemini_context_limits("gemini-3.8-flash")
    
# 4. Calculate text usage weight before running operations
CheckUsage.gemini_count_tokens("How many credits does this sentence take?", "gemini-3.8-flash")

CheckUsage.groq_rate_limits()

```

The run for llm_info.py gives this output for a given API Key

--- Available Groq Models ---
- qwen/qwen3.8-27b
- openai/gpt-oss-120b
- allam-2-7b
- whisper-large-v3
- meta-llama/llama-prompt-guard-2-22m
- meta-llama/llama-prompt-guard-2-86m
- openai/gpt-oss-20b
- canopylabs/orpheus-arabic-saudi
- openai/gpt-oss-safeguard-20b
- canopylabs/orpheus-v1-english
- whisper-large-v3-turbo

--- Available Gemini Models ---
- models/gemini-2.5-flash (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-2.5-pro (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-2.5-flash-preview-tts (Supported actions: ['countTokens', 'generateContent'])
- models/gemini-2.5-pro-preview-tts (Supported actions: ['countTokens', 'generateContent', 'batchGenerateContent'])
- models/gemma-4-26b-a4b-it (Supported actions: ['generateContent', 'countTokens'])
- models/gemma-4-31b-it (Supported actions: ['generateContent', 'countTokens'])
- models/gemini-flash-latest (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-flash-lite-latest (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-pro-latest (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-2.5-flash-lite (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-2.5-flash-image (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/gemini-3-flash-preview (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-3.1-pro-preview (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-3.1-pro-preview-customtools (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-3.1-flash-lite-preview (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-3.1-flash-lite (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-3-pro-image-preview (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/gemini-3-pro-image (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/nano-banana-pro-preview (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/gemini-3.1-flash-image-preview (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/gemini-3.1-flash-image (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/gemini-3.1-flash-lite-image (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/gemini-nano-banana-2.1 (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/gemini-3.5-flash (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-3.5-flash-lite (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-omni-flash-preview (Supported actions: ['generateContent', 'countTokens'])
- models/gemini-omni-1.1-flash (Supported actions: ['generateContent', 'countTokens'])
- models/gemini-omni-1.2-flash (Supported actions: ['generateContent', 'countTokens'])
- models/gemini-3.5-transcribe (Supported actions: ['generateContent', 'countTokens'])
- models/gemini-3.6-flash (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-3.7-flash (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-3.8-flash (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-4-argon (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/lyria-3-clip-preview (Supported actions: ['generateContent', 'countTokens'])
- models/lyria-3-pro-preview (Supported actions: ['generateContent', 'countTokens'])
- models/lyria-3.5 (Supported actions: ['generateContent', 'countTokens'])
- models/gemini-3.1-flash-tts-preview (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/gemini-3.8-flash-tts (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/gemini-3.8-flash-lite-tts (Supported actions: ['generateContent', 'countTokens', 'batchGenerateContent'])
- models/gemini-robotics-er-2-preview (Supported actions: ['generateContent', 'countTokens', 'createCachedContent', 'batchGenerateContent'])
- models/gemini-2.5-computer-use-preview-10-2025 (Supported actions: ['generateContent', 'countTokens'])
- models/antigravity-preview-05-2026 (Supported actions: ['generateContent', 'countTokens'])
- models/antigravity-preview-09-2026 (Supported actions: ['generateContent', 'countTokens'])
- models/antigravity-preview-latest (Supported actions: ['generateContent', 'countTokens'])
- models/deep-research-max-preview-04-2026 (Supported actions: ['generateContent', 'countTokens'])- models/deep-research-preview-04-2026 (Supported actions: ['generateContent', 'countTokens'])
- models/deep-research-pro-preview-12-2025 (Supported actions: ['generateContent', 'countTokens'])- models/gemini-embedding-001 (Supported actions: ['embedContent', 'countTextTokens', 'countTokens', 'asyncBatchEmbedContent'])
- models/gemini-embedding-2-preview (Supported actions: ['embedContent', 'countTextTokens', 'countTokens', 'asyncBatchEmbedContent'])
- models/gemini-embedding-2 (Supported actions: ['embedContent', 'countTextTokens', 'countTokens', 'asyncBatchEmbedContent'])
- models/aqa (Supported actions: ['generateAnswer'])
- models/gemini-3.5-transcribe-live (Supported actions: ['bidiGenerateContent'])
- models/gemini-2.5-flash-native-audio-latest (Supported actions: ['countTokens', 'bidiGenerateContent'])
- models/gemini-2.5-flash-native-audio-preview-09-2025 (Supported actions: ['countTokens', 'bidiGenerateContent'])
- models/gemini-2.5-flash-native-audio-preview-12-2025 (Supported actions: ['countTokens', 'bidiGenerateContent'])
- models/gemini-3.1-flash-live-preview (Supported actions: ['bidiGenerateContent'])
- models/gemini-3.8-live (Supported actions: ['bidiGenerateContent'])
- models/gemini-3.8-live-extended-thinking (Supported actions: ['bidiGenerateContent'])
- models/gemini-robotics-er-2-streaming-preview (Supported actions: ['bidiGenerateContent'])
- models/gemini-3.5-live-translate-preview (Supported actions: ['bidiGenerateContent'])
- models/lyria-realtime-exp (Supported actions: ['bidiGenerateMusic'])

--- Groq Rate Limits & Usage Status ---
- Remaining Requests today (RPD): 999
- Remaining Tokens this minute (TPM): 7680
- Total Limit Requests per day: 1000
- Total Limit Tokens per minute: 8000
- Limit Reset Time (Tokens): 2.4s

--- Gemini Limits for gemini-3.8-flash ---
- Input Token Limit: 1048576
- Output Token Limit: 65536

--- Gemini Pre-flight Token Count ---
- Prompt: "How many credits does this sentence take?"
- Total Tokens Required: 9
