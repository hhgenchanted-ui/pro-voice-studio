import os
import subprocess
import shutil
from flask import Flask, request, send_file, jsonify, render_template
from gradio_client import Client, handle_file
import imageio_ffmpeg

app = Flask(__name__)

UPLOAD_FOLDER = "temp_audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

def convert_to_wav(input_path, output_path, max_seconds=25):
    cmd = list((
        FFMPEG_PATH, "-y", "-i", input_path,
        "-t", str(max_seconds),
        "-ar", "22050",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_path
    ))
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/save_voiceprint", methods=list(("POST",)))
def save_voiceprint():
    if "file" not in request.files:
        return jsonify({"error": "يرجى اختيار ملف أو تسجيل صوت البصمة أولاً"}), 400
    
    file = request.files.get("file")
    raw_path = os.path.join(UPLOAD_FOLDER, "raw_voiceprint")
    wav_path = os.path.join(UPLOAD_FOLDER, "voiceprint.wav")
    
    file.save(raw_path)
    try:
        convert_to_wav(raw_path, wav_path, max_seconds=15)
        size_kb = round(os.path.getsize(wav_path) / 1024, 1)
        if size_kb < 5:
            return jsonify({"error": "التسجيل فارغ أو قصير جداً، حاول مرة أخرى"}), 400
        return jsonify({"status": "success", "size_kb": size_kb})
    except Exception as e:
        return jsonify({"error": f"فشل معالجة البصمة: {str(e)}"}), 500

@app.route("/clone_voice", methods=list(("POST",)))
def clone_voice():
    voiceprint_wav = os.path.join(UPLOAD_FOLDER, "voiceprint.wav")
    if not os.path.exists(voiceprint_wav):
        return jsonify({"error": "⚠️ يرجى رفع أو تسجيل البصمة الصوتية وحفظها أولاً"}), 400

    if "acting_audio" not in request.files:
        return jsonify({"error": "⚠️ يرجى تسجيل صوتك التمثيلي أولاً"}), 400

    acting_file = request.files.get("acting_audio")
    raw_acting = os.path.join(UPLOAD_FOLDER, "raw_acting")
    acting_wav = os.path.join(UPLOAD_FOLDER, "acting.wav")
    acting_file.save(raw_acting)

    try:
        convert_to_wav(raw_acting, acting_wav, max_seconds=25)

        client = Client("Plachta/Seed-VC")
        result = client.predict(
            source=handle_file(acting_wav),
            target=handle_file(voiceprint_wav),
            diffusion_steps=15,
            length_adjust=1.0,
            inference_cfg_rate=0.7,
            f0_condition=True,
            auto_f0_adjust=True,
            pitch_shift=0,
            api_name="/predict"
        )

        output_audio = result[0] if isinstance(result, (list, tuple)) else result
        final_output = os.path.join(UPLOAD_FOLDER, "cloned_output.wav")
        shutil.copy(output_audio, final_output)

        return send_file(final_output, mimetype="audio/wav")

    except Exception as e:
        return jsonify({"error": "⏳ المحركات السحابية مشغولة حالياً، انتظر 30 ثانية واضغط استنساخ مجدداً"}), 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
    

            
      
    
    
  
