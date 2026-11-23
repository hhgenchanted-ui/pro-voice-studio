import os
import tempfile
from flask import Flask, request, send_file, jsonify
from gradio_client import Client, handle_file

app = Flask(__name__)

CLONED_VOICE_FILE = "target_cloned_voice.wav"

@app.route("/", methods=["GET"])
def home():
    return "Pro Voice Studio is Live 24/7!"

@app.route("/set_voice", methods=["POST"])
def set_cloned_voice():
    with open(CLONED_VOICE_FILE, "wb") as f:
        f.write(request.data)
    return jsonify({"status": "ok", "message": "تم حفظ البصمة الصوتية بنجاح"})

@app.route("/dub_acting", methods=["POST"])
def dub_acting():
    if not os.path.exists(CLONED_VOICE_FILE):
        return "يرجى رفع عينة الصوت أولاً", 400

    pitch = int(request.args.get("pitch", 0))
    acting_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    acting_file.write(request.data)
    acting_file.close()

    vc_client = Client("Plachta/Seed-VC")
    raw_out = vc_client.predict(
        source_audio_path=handle_file(acting_file.name),
        target_audio_path=handle_file(CLONED_VOICE_FILE),
        diffusion_steps=25,
        length_adjust=1.0,
        inference_cfg_rate=0.7,
        f0_condition=True,
        auto_f0_adjust=False,
        pitch_shift=pitch,
        api_name="/predict"
    )
    os.remove(acting_file.name)
    return send_file(raw_out, mimetype="audio/wav")

@app.route("/dub_text", methods=["POST"])
def dub_text():
    if not os.path.exists(CLONED_VOICE_FILE):
        return "يرجى رفع عينة الصوت أولاً", 400

    text = request.args.get("text", "مرحباً بك")
    emotion = request.args.get("emotion", "طبيعي")
    weights = {"طبيعي": 0.5, "فرح": 0.9, "حزن": 0.85, "غضب": 0.95, "همس": 0.75}

    tts_client = Client("IndexTeam/IndexTTS-2-Demo")
    raw_out = tts_client.predict(
        emo_control_method="Use emotion reference audio" if emotion != "طبيعي" else "Same as the voice reference",
        prompt=handle_file(CLONED_VOICE_FILE),
        text=text,
        emo_ref_path=handle_file(CLONED_VOICE_FILE),
        emo_weight=weights.get(emotion, 0.8),
        api_name="/gen_single"
    )
    return send_file(raw_out, mimetype="audio/wav")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)
    
        
  
