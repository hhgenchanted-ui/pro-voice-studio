import os
import subprocess
import shutil
from flask import Flask, request, send_file, jsonify, render_template_string
from gradio_client import Client, handle_file
import imageio_ffmpeg
from ui import PAGE

app = Flask(__name__)
UPLOAD_FOLDER = "temp_audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

def convert_to_wav(input_path, output_path, max_seconds=12):
    cmd = list((FFMPEG_PATH, "-y", "-i", input_path, "-t", str(max_seconds), "-ar", "22050", "-ac", "1", "-c:a", "pcm_s16le", output_path))
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

@app.route("/")
def index():
    return render_template_string(PAGE)

@app.route("/save_voiceprint", methods=list(("POST",)))
def save_voiceprint():
    if "file" not in request.files:
        return jsonify({"error": "يرجى اختيار ملف أولاً"}), 400
    file = request.files.get("file")
    raw_path = os.path.join(UPLOAD_FOLDER, "raw_vp")
    wav_path = os.path.join(UPLOAD_FOLDER, "voiceprint.wav")
    file.save(raw_path)
    try:
        convert_to_wav(raw_path, wav_path, max_seconds=8)
        size_kb = round(os.path.getsize(wav_path) / 1024, 1)
        if size_kb < 5:
            return jsonify({"error": "التسجيل قصير جداً"}), 400
        return jsonify({"status": "success", "size_kb": size_kb})
    except Exception as e:
        return jsonify({"error": f"خطأ تحويل الصوت: {str(e)}"}), 500

@app.route("/clone_voice", methods=list(("POST",)))
def clone_voice():
    vp_wav = os.path.join(UPLOAD_FOLDER, "voiceprint.wav")
    if not os.path.exists(vp_wav):
        return jsonify({"error": "يرجى حفظ البصمة الصوتية أولاً"}), 400
    if "acting_audio" not in request.files:
        return jsonify({"error": "يرجى تسجيل صوتك التمثيلي أولاً"}), 400

    acting_file = request.files.get("acting_audio")
    raw_act = os.path.join(UPLOAD_FOLDER, "raw_act")
    act_wav = os.path.join(UPLOAD_FOLDER, "acting.wav")
    acting_file.save(raw_act)

    try:
        convert_to_wav(raw_act, act_wav, max_seconds=15)
        client = Client("Plachta/Seed-VC")
        
        result = client.predict(
            handle_file(act_wav),
            handle_file(vp_wav),
            15,
            1.0,
            0.7,
            True,
            True,
            0,
            api_name="/predict"
        )
        
        # جمع كل المسارات الصالحة واختيار الملف الأكبر حجماً (الصوت الكامل وليس الفارغ)
        valid_files = []
        items = result if isinstance(result, (list, tuple)) else [result]
        for item in items:
            if isinstance(item, str) and os.path.exists(item):
                valid_files.append(item)
            elif isinstance(item, dict) and "path" in item and os.path.exists(item["path"]):
                valid_files.append(item["path"])

        if not valid_files:
            return jsonify({"error": "لم يتم العثور على ملف صوتي من المحرك"}), 500

        best_file = max(valid_files, key=lambda f: os.path.getsize(f))
        if os.path.getsize(best_file) < 1000:
            return jsonify({"error": "الملف الناتج فارغ، تأكد أن صوتك التمثيلي واضح ومسموع"}), 500

        final_out = os.path.join(UPLOAD_FOLDER, "cloned_output.wav")
        convert_to_wav(best_file, final_out, max_seconds=30)
        return send_file(final_out, mimetype="audio/wav")
    except Exception as e:
        return jsonify({"error": f"رد المحرك: {str(e)}"}), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
                                   
        
    
    
           
