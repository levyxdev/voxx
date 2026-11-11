# A Narration's language is a BCP 47 tag, matched as written against the Model's languages

The v0.1 spec first required `language` to be an ISO 639-1 two-letter code, but Cantonese (`yue`) and Filipino (`fil`), which Qwen3-ASR supports, have no two-letter code, so it became BCP 47. BCP 47 contains ISO 639-1, so the existing `zh` and `en` stay valid, and CueTake already treats `language` as a language tag (such as `zh-CN`). Only canonical case is accepted (`zh-Hant-HK`, not `zh-hant-hk`), and the tag must exactly match a language the Model registers; voxx does no step-by-step fallback such as `en-US` → `en`.

## Considered options

- **RFC 4647 lookup with fallback.** Rejected: `zh-HK` would quietly fall back to `zh` and be read as Mandarin; with exact matching the agent gets `unsupported_language` with the languages the Model actually registers, and corrects the tag itself.
- **Case-insensitive matching.** Rejected: with only one spelling, neither matching nor output can be ambiguous; when the case is wrong, the error gives the canonical spelling.

## Consequences

- A Model that reads `en` does not thereby read `en-US`: a Narration must say what the registry registers.
- The self-check also matches exactly when looking for a Model to transcribe the language, so an `en-GB` Narration is not transcribed by a Model that registers only `en`; it gets a `not_checked` warning instead.
