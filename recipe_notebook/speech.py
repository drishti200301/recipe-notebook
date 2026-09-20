"""
speech.py - the ONLY place JavaScript appears in this project.

WHY JAVASCRIPT AT ALL?  Your Python code runs on a SERVER. The microphone
and speakers belong to the BROWSER on your phone/laptop. Python can't reach
through the internet and grab your mic - only code running inside the
browser can. So a small JavaScript helper runs in the browser and talks to
the browser's built-in speech tools. It's like an OS permission dialog:
the browser, not our app, owns the mic and asks you for access.

THE BRIDGE, in plain terms (two directions):
  Python -> browser : ui.run_javascript("window.recipeVoice.start()")
  browser -> Python : the JS calls emitEvent('voice_text', {...}) and
                      Python catches it with ui.on('voice_text', handler)
You never edit the JavaScript; you only call the Python helpers below.
"""
import json

from nicegui import ui

# This text is sent to the browser once per page load. It is a Python
# string, not a separate .js file, so the whole bridge lives here.
_BRIDGE_JS = r"""
(function () {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const st = { rec: null, wanted: false, lastText: '', lastTime: 0 };

  function begin() {
    const rec = new SR();
    rec.continuous = true;          // keep listening across pauses
    rec.interimResults = false;     // only send finished sentences
    rec.lang = navigator.language || 'en-US';

    rec.onresult = function (event) {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (!event.results[i].isFinal) continue;
        const text = event.results[i][0].transcript.trim();
        const now = Date.now();
        // Some Android versions repeat a sentence; ignore instant duplicates.
        if (text && !(text === st.lastText && now - st.lastTime < 1500)) {
          st.lastText = text; st.lastTime = now;
          emitEvent('voice_text', { text: text });
        }
      }
    };
    rec.onerror = function (event) {
      if (event.error === 'no-speech' || event.error === 'aborted') return;
      if (['not-allowed', 'service-not-allowed', 'network', 'language-not-supported'].includes(event.error)) {
        st.wanted = false;          // permission denied: don't retry forever
      }
      emitEvent('voice_error', { error: event.error });
    };
    rec.onend = function () {
      // Browsers stop recognition after silence; restart while we still want it.
      if (st.wanted && st.rec === rec) setTimeout(begin, 250);
    };
    st.rec = rec;
    try { rec.start(); } catch (e) {}
  }

  window.recipeVoice = {
    supported: function () { return !!SR; },
    start: function () {
      if (!SR) { emitEvent('voice_error', { error: 'unsupported' }); return; }
      st.wanted = true; begin();
    },
    stop: function () {
      st.wanted = false;
      if (st.rec) { try { st.rec.stop(); } catch (e) {} }
    },
  };

  window.recipeSpeak = function (chunks) {
    const synth = window.speechSynthesis;
    synth.cancel();
    // Many short utterances (instead of one long one) avoids a Chrome bug
    // where long speech cuts out after ~15 seconds.
    chunks.forEach(function (t) {
      const u = new SpeechSynthesisUtterance(t);
      u.rate = 0.95;
      synth.speak(u);
    });
  };
  window.recipeStopSpeaking = function () { window.speechSynthesis.cancel(); };
})();
"""


def install_bridge() -> None:
    """Call once at the top of any page that uses voice. Adds the JS to the page."""
    ui.add_head_html(f"<script>{_BRIDGE_JS}</script>")


# ---------- Python-friendly wrappers --------------------------------------
async def is_supported() -> bool:
    """Ask the browser whether it has speech recognition at all."""
    return bool(await ui.run_javascript("window.recipeVoice.supported()", timeout=5))


def start_listening() -> None:
    ui.run_javascript("window.recipeVoice.start()")


def stop_listening() -> None:
    ui.run_javascript("window.recipeVoice.stop()")


def recipe_to_chunks(recipe: dict) -> list[str]:
    """Break a recipe into short phrases, in reading order: name -> ingredients -> steps."""
    def clean(text: str) -> str:
        return text.replace(" (?)", "")       # "(?)" is a note for your eyes, not for reading aloud

    recipe = {**recipe,
              "ingredients": [clean(i) for i in recipe["ingredients"]],
              "steps": [clean(s) for s in recipe["steps"]]}
    chunks = [recipe["name"] + "."]
    if recipe["ingredients"]:
        chunks.append("Ingredients.")
        chunks += [i + "." for i in recipe["ingredients"]]
    if recipe["steps"]:
        chunks.append("Steps.")
        chunks += [f"Step {n}. {s}." for n, s in enumerate(recipe["steps"], start=1)]
    return chunks


def speak(chunks: list[str]) -> None:
    # json.dumps safely converts a Python list into JavaScript array text.
    ui.run_javascript(f"window.recipeSpeak({json.dumps(chunks)})")


def stop_speaking() -> None:
    ui.run_javascript("window.recipeStopSpeaking()")
