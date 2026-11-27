import os
import subprocess
from flask import Flask, request, send_file, jsonify, render_template_string
from gradio_client import Client, handle_file
import imageio_ffmpeg
from ui import PAGE

app = Flask(__name__)
UPLOAD_FOLDER = "temp_audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

def convert_to_wav(input_path, output_path, max_seconds=10):
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

def convert_to_mp3(input_path, output_path):
    cmd = list((
        FFMPEG_PATH, "-y", "-i", input_path,
        "-ar", "24000", "-ac", "1",
        "-codec:a", "libmp3lame", "-b:a", "128k",
        output_path
    ))
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
            return jsonify({"error": "التسجيل قصير جداً أو فارغ"}), 400
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
        convert_to_wav(raw_act, act_wav, max_seconds=8)
    except Exception as e:
        return jsonify({"error": f"خطأ في تجهيز الصوت: {str(e)}"}), 500

    hf_token = os.environ.get("HF_TOKEN")
    # قائمة محركات استنساخ الصوت إلى صوت (Zero-shot Voice Conversion)
    spaces = list((
        "Plachta/Seed-VC",
        "myshell-ai/OpenVoiceV2",
        "amphion/maskgct"
    ))
    last_error = ""

    for space_name in spaces:
        try:
            client = Client(space_name, token=hf_token) if hf_token else Client(space_name)
            
            if space_name == "Plachta/Seed-VC":
                result = client.predict(
                    handle_file(act_wav),
                    handle_file(vp_wav),
                    6,
                    1.0,
                    0.7,
                    True,
                    True,
                    0,
                    api_name="/predict"
                )
            elif space_name == "myshell-ai/OpenVoiceV2":
                # OpenVoiceV2 تحويل نبرة الصوت (Tone Color Converter)
                result = client.predict(
                    handle_file(act_wav),
                    handle_file(vp_wav),
                    api_name="/change_tone"
                )
            else:
                # البحث التلقائي عن أي مسار دالة متاح في المحرك الثالث
                info = client.view_api(return_format="dict")
                eps = list(info.get("named_endpoints", {}).keys())
                target_ep = eps.pop(0) if eps else "/predict"
                result = client.predict(
                    handle_file(vp_wav),
                    handle_file(act_wav),
                    api_name=target_ep
                )

            valid_files = list()
            items = result if isinstance(result, (list, tuple)) else list((result,))
            for item in items:
                if isinstance(item, str) and os.path.exists(item):
                    valid_files.append(item)
                elif isinstance(item, dict) and "path" in item and os.path.exists(item.get("path")):
                    valid_files.append(item.get("path"))

            if valid_files:
                best_file = max(valid_files, key=lambda f: os.path.getsize(f))
                final_mp3 = os.path.join(UPLOAD_FOLDER, "cloned_output.mp3")
                convert_to_mp3(best_file, final_mp3)
                mp3_kb = round(os.path.getsize(final_mp3) / 1024, 1)
                return jsonify({"status": "success", "size_kb": mp3_kb})
        except Exception as e:
            last_error = f"{space_name}: {str(e)}"
            continue

    return jsonify({"error": f"المحركات مشغولة حالياً: {last_error[:150]}"}), 503

@app.route("/get_audio")
def get_audio():
    final_mp3 = os.path.join(UPLOAD_FOLDER, "cloned_output.mp3")
    if not os.path.exists(final_mp3):
        return "Not found", 404
    return send_file(final_mp3, mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
                
    

        
                                   
        
    
    
           
