import os
import subprocess
import wave
import audioop
from flask import Flask, request, send_file, jsonify, render_template_string
from gradio_client import Client, handle_file
import imageio_ffmpeg
from ui import PAGE

app = Flask(__name__)
UPLOAD_FOLDER = "temp_audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

def convert_to_wav(input_path, output_path, max_seconds=15):
    cmd = list((
        FFMPEG_PATH, "-y", "-i", input_path,
        "-t", str(max_seconds),
        "-ar", "16000",
        "-ac", "1",
        "-af", "loudnorm",
        "-c:a", "pcm_s16le",
        output_path
    ))
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def is_silent(wav_path):
    try:
        with wave.open(wav_path, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            rms = audioop.rms(frames, wf.getsampwidth())
            return rms < 50
    except Exception:
        return False

def convert_to_mp3(input_path, output_path):
    cmd = list((FFMPEG_PATH, "-y", "-i", input_path, "-ar", "24000", "-ac", "1", "-codec:a", "libmp3lame", "-b:a", "128k", output_path))
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
        convert_to_wav(raw_path, wav_path, max_seconds=10)
        if is_silent(wav_path):
            return jsonify({"error": "البصمة صامتة! تأكد من وجود صوت في الفيديو أو الميكروفون"}), 400
        size_kb = round(os.path.getsize(wav_path) / 1024, 1)
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
        if is_silent(act_wav):
            return jsonify({"error": "تسجيلك التمثيلي صامت! تأكد من إذن الميكروفون وتحدث بصوت مرتفع"}), 400

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
        
        valid_files = list()
        items = result if isinstance(result, (list, tuple)) else list((result,))
        for item in items:
            if isinstance(item, str) and os.path.exists(item):
                valid_files.append(item)
            elif isinstance(item, dict) and "path" in item and os.path.exists(item.get("path")):
                valid_files.append(item.get("path"))

        if not valid_files:
            return jsonify({"error": "لم يرجع المحرك أي ملف صوتي"}), 500

        # اختيار الملف الثاني (المخرج النهائي الكامل) إذا وُجد، وإلا الأكبر حجماً
        best_file = valid_files[-1] if len(valid_files) > 1 else valid_files[0]
        final_mp3 = os.path.join(UPLOAD_FOLDER, "cloned_output.mp3")
        convert_to_mp3(best_file, final_mp3)
        
        mp3_kb = round(os.path.getsize(final_mp3) / 1024, 1)
        return jsonify({"status": "success", "size_kb": mp3_kb})
    except Exception as e:
        return jsonify({"error": f"رد المحرك: {str(e)}"}), 503

@app.route("/get_audio")
def get_audio():
    final_mp3 = os.path.join(UPLOAD_FOLDER, "cloned_output.mp3")
    if not os.path.exists(final_mp3):
        return "Not found", 404
    return send_file(final_mp3, mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

        
                                   
        
    
    
           
