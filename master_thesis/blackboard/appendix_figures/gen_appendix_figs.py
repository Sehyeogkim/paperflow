#!/usr/bin/env python3
"""Generate Appendix A/B schematic figures with two Google image models.

  Imagen      = imagen-4.0-generate-001   (:predict)
  Nano-banana = gemini-2.5-flash-image    (:generateContent)

Reads gemini_api_key from ../../../.env  ("key = value" format, spaces around =).
Saves PNGs next to this script. Prints a per-image status line.
"""
import base64, json, os, sys, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT  = os.path.dirname(os.path.abspath(__file__))
API  = "https://generativelanguage.googleapis.com/v1beta"

def load_key():
    for line in open(os.path.join(ROOT, ".env")):
        if "gemini" in line.lower() and "=" in line:
            return line.split("=", 1)[1].strip()
    sys.exit("no gemini_api_key in .env")

KEY = load_key()

# ----------------------------------------------------------------------------
# Prompts. Generative image models mangle text, so we ask for an *illustration*
# (shapes, color, spatial relationships) and explicitly suppress text/equations.
# ----------------------------------------------------------------------------
PROMPT_A = (
    "A clean scientific medical illustration, 16:9, on a pure white background, "
    "showing how an irregular calcification is grown inside the lipid core of a "
    "coronary artery plaque by a seed-based region-growing algorithm. "
    "Show a longitudinal cut-away of a cylindrical coronary artery: red vessel "
    "wall on the outside, a thin bright fibrous cap layer lining the lumen, and a "
    "large soft yellow lipid-core blob embedded in the wall. Inside the yellow "
    "lipid core, show a small magenta dot as the 'seed', and an irregular, rough "
    "bone-white calcification mass that has grown outward from that seed and stays "
    "fully contained inside the yellow core with a thin clear safety gap to the cap. "
    "Use three small side panels stacked at the right showing three calcification "
    "shapes grown from the same seed: one round/isotropic, one elongated along the "
    "vessel axis, one stretched around the circumference — to convey anisotropic "
    "growth. Soft medical-textbook shading, subtle drop shadows, high detail. "
    "Do NOT render any text, letters, numbers, equations, or labels anywhere."
)

PROMPT_B = (
    "A clean engineering systems schematic, 16:9, on a pure white background, "
    "showing the boundary-condition generators for a coronary blood-flow "
    "simulation, in two stacked rows. "
    "TOP ROW (inlet pressure via a three-element Windkessel): on the left a small "
    "icon of a pulsatile inflow (a curved arrow into a tube), feeding an "
    "electrical-analog circuit drawn with clean lines — one resistor in series, "
    "then a parallel branch of a second resistor and a capacitor to ground — and on "
    "the right a smooth periodic arterial pressure waveform plotted as a clean curve "
    "rising and falling each heartbeat. "
    "BOTTOM ROW (intramyocardial pressure via a time-varying-elastance heart model): "
    "a stylized cross-section of a heart left ventricle that squeezes, drawn beside a "
    "simple lumped circuit with diode-like valve symbols, producing on the right a "
    "tall sharp ventricular-pressure waveform that peaks in systole. "
    "Modern flat vector infographic style, soft blue and teal accent colors, thin "
    "neat connector lines, generous white space, professional journal-figure look. "
    "Do NOT render any text, letters, numbers, equations, axis labels, or captions."
)

JOBS = [
    ("imagen",  "A", PROMPT_A, "imagen_appendixA.png"),
    ("imagen",  "B", PROMPT_B, "imagen_appendixB.png"),
    ("nano",    "A", PROMPT_A, "nanobanana_appendixA.png"),
    ("nano",    "B", PROMPT_B, "nanobanana_appendixB.png"),
]

def post(url, body):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)

def run_imagen(prompt, outfile):
    url = f"{API}/models/imagen-4.0-generate-001:predict?key={KEY}"
    body = {"instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": "16:9"}}
    d = post(url, body)
    b64 = d["predictions"][0]["bytesBase64Encoded"]
    open(os.path.join(OUT, outfile), "wb").write(base64.b64decode(b64))

def run_nano(prompt, outfile):
    url = f"{API}/models/gemini-2.5-flash-image:generateContent?key={KEY}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    d = post(url, body)
    parts = d["candidates"][0]["content"]["parts"]
    for p in parts:
        if "inlineData" in p:
            open(os.path.join(OUT, outfile), "wb").write(
                base64.b64decode(p["inlineData"]["data"]))
            return
    raise RuntimeError("no image part in response: " +
                       json.dumps(d)[:300])

for model, app, prompt, outfile in JOBS:
    try:
        (run_imagen if model == "imagen" else run_nano)(prompt, outfile)
        sz = os.path.getsize(os.path.join(OUT, outfile))
        print(f"OK   {model:6s} Appendix {app} -> {outfile} ({sz//1024} KB)")
    except urllib.error.HTTPError as e:
        print(f"FAIL {model:6s} Appendix {app}: HTTP {e.code} {e.read()[:200]!r}")
    except Exception as e:
        print(f"FAIL {model:6s} Appendix {app}: {e}")
