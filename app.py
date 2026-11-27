import os
import subprocess
import shutil
from flask import Flask, request, send_file, jsonify, render_template_string
from gradio_client import Client, handle_file
import imageio_ffmpeg

app = Flask(__name__)

UPLOAD_FOLDER = "temp_audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

HTML_PAGE = '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pro Voice Studio</title>
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: sans-serif; padding: 16px; display: flex; flex-direction: column; align-items: center; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 18px; width: 100%; max-width: 460px; margin-bottom: 16px; box-sizing: border-box; }
        h3 { margin-top: 0; font-size: 16px; }
        .btn { width: 100%; padding: 12px; border: none; border-radius: 10px; font-size: 15px; font-weight: bold; cursor: pointer; margin-top: 10px; color: white; }
        .btn-blue { background: #0284c7; }
        .btn-red { background: #dc2626; }
        .btn-gray { background: #475569; }
        .row { display: flex; gap: 10px; margin-top: 10px; }
        .row .btn { margin-top: 0; }
        input[type="file"] { width: 100%; padding: 10px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: #cbd5e1; box-sizing: border-box; }
        .status { text-align: center; margin-top: 10px; font-size: 14px; color: #38bdf8; }
        .error { color: #f87171; }
        .success { color: #4ade80; }
        audio { width: 100%; margin-top: 12px; }
    </style>
</head>
<body>
    <div class="card">
        <h3>1️⃣ البصمة الصوتية المستهدفة (فيديو أو صوت)</h3>
        <input type="file" id="voiceFile" accept="audio/*,video/*">
        <button class="btn btn-blue" onclick="uploadVoiceprint()">💾 رفع وحفظ البصمة من ملف</button>
        <div class="row">
            <button class="btn btn-red" id="recVpBtn" onclick="startRec('vp')">🔴 تسجيل البصمة</button>
            <button class="btn btn-gray" id="stopVpBtn" onclick="stopRec('vp')" disabled>⏹️ حفظ البصمة</button>
        </div>
        <div id="vpStatus" class="status"></div>
    </div>
    <div class="card">
        <h3>2️⃣ الدبلجة التمثيلية (استنساخ الصوت بنفس مشاعرك)</h3>
        <div class="row">
            <button class="btn btn-red" id="recActBtn" onclick="startRec('act')">🔴 ابدأ التمثيل</button>
            <button class="btn btn-gray" id="stopActBtn" onclick="stopRec('act')" disabled>⏹️ إيقاف</button>
        </div>
        <div id="actStatus" class="status"></div>
        <button class="btn btn-blue" onclick="cloneVoiceToVoice()">✨ استنساخ الصوت بنفس مشاعري</button>
        <div id="cloneStatus" class="status"></div>
        <audio id="resultAudio" controls></audio>
    </div>
'''
      HTML_SCRIPT = '''
    <script>
        let mediaRecorder;
        let audioChunks = new Array();
        let actingBlob = null;

        async function startRec(type) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioChunks = new Array();
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
                mediaRecorder.onstop = async () => {
                    stream.getTracks().forEach(t => t.stop());
                    const blob = new Blob(audioChunks, { type: 'audio/webm' });
                    if (type === 'vp') {
                        await sendVoiceprintBlob(blob);
                    } else {
                        actingBlob = blob;
                        const kb = Math.round(blob.size / 1024);
                        document.getElementById('actStatus').innerHTML = `<span class="success">✅ تم تسجيل الأداء (${kb} KB)</span>`;
                    }
                };
                mediaRecorder.start();
                if (type === 'vp') {
                    document.getElementById('recVpBtn').disabled = true;
                    document.getElementById('stopVpBtn').disabled = false;
                    document.getElementById('vpStatus').innerText = "🎙️ جاري تسجيل البصمة...";
                } else {
                    document.getElementById('recActBtn').disabled = true;
                    document.getElementById('stopActBtn').disabled = false;
                    document.getElementById('actStatus').innerText = "🎭 جاري تسجيل التمثيل...";
                }
            } catch (err) { alert("يرجى السماح بالميكروفون"); }
        }

        function stopRec(type) {
            if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
            if (type === 'vp') {
                document.getElementById('recVpBtn').disabled = false;
                document.getElementById('stopVpBtn').disabled = true;
            } else {
                document.getElementById('recActBtn').disabled = false;
                document.getElementById('stopActBtn').disabled = true;
            }
        }

        async function uploadVoiceprint() {
            const fileInput = document.getElementById('voiceFile');
            if (!fileInput.files.length) return alert("اختر ملفاً أولاً");
            await sendVoiceprintBlob(fileInput.files.item(0));
        }

        async function sendVoiceprintBlob(fileOrBlob) {
            const status = document.getElementById('vpStatus');
            status.innerText = "⏳ جاري حفظ البصمة...";
            const formData = new FormData();
            formData.append("file", fileOrBlob, "voiceprint.webm");
            try {
                const res = await fetch("/save_voiceprint", { method: "POST", body: formData });
                const data = await res.json();
                status.innerHTML = res.ok ? `<span class="success">✅ تم حفظ البصمة (${data.size_kb} KB)</span>` : `<span class="error">❌ ${data.error}</span>`;
            } catch (e) { status.innerHTML = `<span class="error">❌ خطأ اتصال</span>`; }
        }

        async function cloneVoiceToVoice() {
            if (!actingBlob) return alert("سجّل صوتك التمثيلي أولاً");
            const status = document.getElementById('cloneStatus');
            status.innerText = "⏳ جاري استنساخ الصوت ونقل المشاعر...";
            const formData = new FormData();
            formData.append("acting_audio", actingBlob, "acting.webm");
            try {
                const res = await fetch("/clone_voice", { method: "POST", body: formData });
                if (!res.ok) {
                    const err = await res.json();
                    status.innerHTML = `<span class="error">❌ ${err.error}</span>`;
                    return;
                }
                const audioBlob = await res.blob();
                const player = document.getElementById('resultAudio');
                player.src = URL.createObjectURL(audioBlob);
                player.play();
                status.innerHTML = `<span class="success">✅ تم استنساخ الصوت بنجاح!</span>`;
            } catch (e) { status.innerHTML = `<span class="error">❌ خطأ: ${e.message}</span>`; }
        }
    </script>
</body>
</html>'''

def convert_to_wav(input_path, output_path, max_seconds=10):
    cmd = list((FFMPEG_PATH, "-y", "-i", input_path, "-t", str(max_seconds), "-ar", "22050", "-ac", "1", "-c:a", "pcm_s16le", output_path))
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

@app.route("/")
def index():
    return render_template_string(HTML_PAGE + HTML_SCRIPT)

@app.route("/save_voiceprint", methods=list(("POST",)))
def save_voiceprint():
    if "file" not in request.files:
        return jsonify({"error": "يرجى اختيار ملف أولاً"}), 400
    file = request.files.get("file")
    raw_path = os.path.join(UPLOAD_FOLDER, "raw_voiceprint")
    wav_path = os.path.join(UPLOAD_FOLDER, "voiceprint.wav")
    file.save(raw_path)
    try:
        convert_to_wav(raw_path, wav_path, max_seconds=8)
        size_kb = round(os.path.getsize(wav_path) / 1024, 1)
        if size_kb < 5:
            return jsonify({"error": "التسجيل فارغ أو قصير جداً"}), 400
        return jsonify({"status": "success", "size_kb": size_kb})
    except Exception as e:
        return jsonify({"error": f"فشل المعالجة: {str(e)}"}), 500

@app.route("/clone_voice", methods=list(("POST",)))
def clone_voice():
    voiceprint_wav = os.path.join(UPLOAD_FOLDER, "voiceprint.wav")
    if not os.path.exists(voiceprint_wav):
        return jsonify({"error": "يرجى حفظ البصمة الصوتية أولاً"}), 400
    if "acting_audio" not in request.files:
        return jsonify({"error": "يرجى تسجيل صوتك التمثيلي أولاً"}), 400
    acting_file = request.files.get("acting_audio")
    raw_acting = os.path.join(UPLOAD_FOLDER, "raw_acting")
    acting_wav = os.path.join(UPLOAD_FOLDER, "acting.wav")
    acting_file.save(raw_acting)
    try:
        convert_to_wav(raw_acting, acting_wav, max_seconds=15)
        client = Client("Plachta/Seed-VC")
        result = client.predict(
            source=handle_file(acting_wav),
            target=handle_file(voiceprint_wav),
            diffusion_steps=10,
            length_adjust=1.0,
            inference_cfg_rate=0.7,
            f0_condition=True,
            auto_f0_adjust=True,
            pitch_shift=0,
            api_name="/predict"
        )
        output_audio = result if isinstance(result, (list, tuple)) else result
        final_output = os.path.join(UPLOAD_FOLDER, "cloned_output.wav")
        shutil.copy(output_audio, final_output)
        return send_file(final_output, mimetype="audio/wav")
    except Exception as e:
        return jsonify({"error": f"السبب التقني: {str(e)}"}), 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
           
