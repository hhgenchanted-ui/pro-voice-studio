import os
import tempfile
from flask import Flask, request, send_file, jsonify
from gradio_client import Client, handle_file
import static_ffmpeg
from pydub import AudioSegment, effects, silence

static_ffmpeg.add_paths()
app = Flask(__name__)

# محرك 1: استنساخ الصوت مع نقل المشاعر التمثيلية (دبلجة استوديو)
vc_client = Client("Plachta/Seed-VC")
# محرك 2: استنساخ الصوت من النص مع المشاعر
tts_client = Client("IndexTeam/IndexTTS-2-Demo")

# ملف حفظ البصمة الصوتية المستنسخة (5 دقائق)
CLONED_VOICE_FILE = "target_cloned_voice.wav"

def clean_and_master(input_path, output_path, is_reference=False):
    """تنقية العينة أو تطبيق هندسة الاستوديو على النتيجة"""
    sound = AudioSegment.from_file(input_path)
    sound = sound.set_frame_rate(44100).set_channels(1)
    if is_reference:
        # إزالة الصمت من عينة الـ 5 دقائق واستخلاص أنقى 45 ثانية مركزة
        chunks = silence.split_on_silence(sound, min_silence_len=600, silence_thresh=-40)
        sound = sum(chunks)[:45000] if chunks else sound[:45000]
    else:
        # هندسة صوتية إذاعية للصوت النهائي
        sound = effects.compress_dynamic_range(sound, threshold=-20.0, ratio=4.0)
        sound = effects.normalize(sound)
    sound.export(output_path, format="wav")

@app.route("/set_voice", methods=["POST"])
def set_cloned_voice():
    """استقبال وحفظ عينة الـ 5 دقائق للصوت المراد استنساخه"""
    temp_raw = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_raw.write(request.data)
    temp_raw.close()
    clean_and_master(temp_raw.name, CLONED_VOICE_FILE, is_reference=True)
    os.remove(temp_raw.name)
    return jsonify({"status": "ok", "message": "تم حفظ البصمة الصوتية بنجاح"})

@app.route("/dub_acting", methods=["POST"])
def dub_acting():
    """الوضع الأول: استنساخ الصوت مع تأدية المشاعر بصوتك (Speech-to-Speech)"""
    if not os.path.exists(CLONED_VOICE_FILE):
        return "يرجى رفع عينة الصوت المراد استنساخه أولاً", 400

    pitch = int(request.args.get("pitch", 0))
    acting_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    acting_file.write(request.data)
    acting_file.close()

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
    final_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    clean_and_master(raw_out, final_out, is_reference=False)
    os.remove(acting_file.name)
    return send_file(final_out, mimetype="audio/wav")

@app.route("/dub_text", methods=["POST"])
def dub_text():
    """الوضع الثاني: نطق النص بالصوت المستنسخ مع اختيار الشعور (Text-to-Speech)"""
    if not os.path.exists(CLONED_VOICE_FILE):
        return "يرجى رفع عينة الصوت المراد استنساخه أولاً", 400

    text = request.args.get("text", "مرحباً بك")
    emotion = request.args.get("emotion", "طبيعي")
    weights = {"طبيعي": 0.5, "فرح": 0.9, "حزن": 0.85, "غضب": 0.95, "همس": 0.75}

    raw_out = tts_client.predict(
        emo_control_method="Use emotion reference audio" if emotion != "طبيعي" else "Same as the voice reference",
        prompt=handle_file(CLONED_VOICE_FILE),
        text=text,
        emo_ref_path=handle_file(CLONED_VOICE_FILE),
        emo_weight=weights.get(emotion, 0.8),
        api_name="/gen_single"
    )
    final_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    clean_and_master(raw_out, final_out, is_reference=False)
    return send_file(final_out, mimetype="audio/wav")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
  
