# voxx

voxx is a local voice tool for agents only: it reads aloud, Line by Line, a narration an agent has written, and returns the audio and word timings. Terms it shares with CueTake keep the same names.

## Language

### Narration

**Narration**:
An ordered set of Lines in one language: the input to one voxx synthesis, and the manifest it returns.
_Avoid_: script, copy file, voice-over script

**Line**:
A piece of text in a Narration with a unique id, read in one continuous take, and matched by one audio file.
_Avoid_: segment, paragraph, sentence

**Delivery Control**:
A way a Line asks to be read, from fixed values. There are four: emotion (happy, sad, angry, fearful, disgusted, surprised, neutral), speed (slow, medium, fast), pitch (low, medium, high) and volume (low, medium, high). Like style, set at the Narration's top level it is every Line's default, and set on a Line it overrides the default. A Model that cannot follow them ignores them with a warning and reads the Line anyway.
_Avoid_: control instruction, instruct, parameter

**Word Timing**:
The moments each word (each character, for Chinese) starts and ends in a Line's audio, relative to the start of that Line's audio.
_Avoid_: alignment, timeline, time

### Voices

**Voice**:
The vocal identity a Line is read in: a Preset Voice, a Cloned Voice or a Designed Voice.
_Avoid_: speaker, sound, character

**Preset Voice**:
A Voice a Model ships with, chosen by name.
_Avoid_: built-in speaker, built-in sound

**Cloned Voice**:
A Voice obtained from a Reference Recording a real person made.
_Avoid_: custom voice, voice profile

**Designed Voice**:
A Voice designed from a text description and fixed by choosing one of several Design Takes.
_Avoid_: generated voice, AI voice, virtual voice

**Default Voice**:
The Voice a Line is read in when neither it nor its Narration names one: at most one per language, set by the user, and kept for every later Narration on the machine.
_Avoid_: preferred voice, fallback voice, my voice

**Design Take**:
One candidate Voice designed from a text description, reading the same sample text as the others, waiting for the user to listen and choose.
_Avoid_: candidate, sample, voice test

**Reference Recording**:
The recording a Cloned Voice or Designed Voice comes from: a real person's recording for a Cloned Voice, the chosen Design Take for a Designed Voice.
_Avoid_: prompt audio, ref, sample

### Models

**Model**:
A downloadable TTS, alignment or transcription model registered in voxx's registry, pinned to one upstream revision, with a checked weight license.
_Avoid_: checkpoint, weights

**Audition**:
The stage in which a newly registered Model stays in the registry so the user can listen to it beside the existing Models before deciding whether it stays; README, DESIGN.md and the skill mark such a Model "on audition".
_Avoid_: candidate, trial

**Extra Repo**:
Another Hugging Face repo a Model needs when it loads, downloaded with the Model by `voxx install`; it is not pinned, and the install manifest records the revision actually downloaded.
_Avoid_: dependency, bundled model

**Capability**:
Something a Model can do: read Preset Voices (preset_voice), clone (clone), design Voices (design), align (align) or transcribe (transcribe).
_Avoid_: feature, task

**Engine**:
The inference library that actually loads and runs a Model; one Engine can run several Models.
_Avoid_: backend, runtime, framework
