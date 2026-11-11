# Cloning checks no consent; the user is responsible

voxx cannot tell whose voice a Reference Recording is, and any consent flag can be bypassed with one sentence, so the code sets no consent gate and asks for no consent statement. Users answer for their right to the voices they clone, as README's disclaimer says; the skill requires the agent to remind the user, before cloning, to confirm they may use the voice, and at publication to disclose that the content is AI-generated where the platform requires it. voxx embeds no audio watermark either; it only records in its output the Model, Voice and seed of each Line.

Designing a Voice from a text description makes the same trade-off: a Designed Voice comes from no real person, but a description can say "sounds like so-and-so" and imitate a real person in effect. The code does not check descriptions; the skill requires the agent to write descriptions only from traits such as age, gender, timbre, pace and setting, never one that points at or imitates a real person, and to decline and rewrite as such traits when the user asks for that.

## Considered options

- **`voice add` requires a consent statement (DESIGN.md draft).** Rejected: the statement cannot be verified and only adds friction.
- **Clone only the user's own voice.** Rejected: there is no technical way to tell whose voice it is either, and it would block legitimate uses such as hiring a voice actor.
- **A keyword blocklist of real names when designing Voices.** Rejected: rewording gets around it, so like a consent statement it only adds friction.
