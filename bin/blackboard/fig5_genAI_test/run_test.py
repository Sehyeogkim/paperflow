import os, base64, traceback
from dotenv import load_dotenv
load_dotenv("/home/jeff/project/3_journal_template/paperflow/.env")

HERE = os.path.dirname(os.path.abspath(__file__))
SKELETON = os.path.join(os.path.dirname(HERE), "fig5_skeleton.png")
OUT = HERE

PROMPT = """Create a clean, professional 3-stage METHODS WORKFLOW OVERVIEW figure for a
scientific journal paper in cardiovascular biomechanics. Horizontal left-to-right flow,
white background, publication-quality flat modern vector style, muted academic palette,
legible sans-serif labels, rounded-rectangle boxes connected by arrows. Clearly number the three stages.

STAGE 1 - "Dataset Generation":
  top box "Input Parameters" with three small labeled insets: (1) a hemodynamic pressure/flow
  waveform plot, (2) a plaque morphology cross-section diagram, (3) material stress-strain curves.
  Arrow down to box "Cost-effective FSI simulation" -> a 1,000-sample dataset, outputs stress
  metrics PSS and delta-PSS.

STAGE 2 - "Vulnerability Index Selection":
  box "6 VI candidates": VI = stress / strength, stress = {PSS, delta-PSS}, alpha = {0.0, 0.5, 1.0}.
  Arrow to box "7-criterion clinical screening" selecting two final indices:
  VI1 = delta-PSS / E_FC^0.5 and VI2 = delta-PSS / E_FC^1.0.

STAGE 3 - "Surrogate Model & Sensitivity Analysis":
  box "GPR surrogate model" mapping inputs to VI.
  Arrow to box "Sobol sensitivity analysis" with a small bar-chart inset;
  conclusion label: Material > Hemodynamic > Morphological.

Keep text concise and correct."""

def save(path, data):
    with open(path, "wb") as f: f.write(data)
    print(f"   -> saved {os.path.basename(path)} ({len(data)} bytes)")

# ---------- OpenAI gpt-image-2 ----------
def openai_calls():
    from openai import OpenAI
    cli = OpenAI(api_key=os.environ["openai_api_key"])
    # A: prompt only
    try:
        print("[1/4] OpenAI gpt-image-2  prompt-only ...")
        r = cli.images.generate(model="gpt-image-2", prompt=PROMPT, size="1536x1024")
        save(os.path.join(OUT,"A_gptimage2_prompt_only.png"), base64.b64decode(r.data[0].b64_json))
    except Exception as e:
        print("   FAIL:", e); traceback.print_exc()
    # B: prompt + skeleton (edit)
    try:
        print("[2/4] OpenAI gpt-image-2  prompt+skeleton ...")
        with open(SKELETON,"rb") as img:
            r = cli.images.edit(model="gpt-image-2", image=img, prompt=PROMPT, size="1536x1024")
        save(os.path.join(OUT,"B_gptimage2_prompt_skeleton.png"), base64.b64decode(r.data[0].b64_json))
    except Exception as e:
        print("   FAIL:", e); traceback.print_exc()

# ---------- Gemini gemini-3-pro-image (Nano Banana 2) ----------
def gemini_calls():
    from google import genai
    from google.genai import types
    from PIL import Image
    cli = genai.Client(api_key=os.environ["gemini_api_key"])
    MODEL = "gemini-3-pro-image"
    cfg = types.GenerateContentConfig(response_modalities=["Text","Image"])
    def extract(resp, path):
        for part in resp.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                save(path, part.inline_data.data); return True
        print("   (no image part returned)"); return False
    # C: prompt only
    try:
        print("[3/4] Gemini nano-banana-2  prompt-only ...")
        r = cli.models.generate_content(model=MODEL, contents=[PROMPT], config=cfg)
        extract(r, os.path.join(OUT,"C_nanobanana2_prompt_only.png"))
    except Exception as e:
        print("   FAIL:", e); traceback.print_exc()
    # D: prompt + skeleton
    try:
        print("[4/4] Gemini nano-banana-2  prompt+skeleton ...")
        skel = Image.open(SKELETON)
        r = cli.models.generate_content(model=MODEL, contents=[PROMPT, skel], config=cfg)
        extract(r, os.path.join(OUT,"D_nanobanana2_prompt_skeleton.png"))
    except Exception as e:
        print("   FAIL:", e); traceback.print_exc()

if __name__ == "__main__":
    print("skeleton:", SKELETON, "exists:", os.path.exists(SKELETON))
    openai_calls()
    gemini_calls()
    print("DONE")
