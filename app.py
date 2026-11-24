import os
import subprocess
import tempfile
from flask import Flask, request, jsonify, send_file, render_template_string
from gradio_client import Client, handle_file
import imageio_ffmpeg

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()

TEMP_DIR = tempfile.gettempdir()
VOICE_SAMPLE_PATH = os.path.join(TEMP_DIR, "saved_voice_sample.wav")
HF_SPACE_ID = "coqui/xtts"


def extract_and_compress_audio(input_path, output_path, max_seconds=300):
    command = [
        FFMPEG_PATH,
        "-y",
        "-i", input_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-t", str(max_seconds),
        output_path
    ]
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000


HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>استوديو استنساخ الصوت الاحترافي</title>
    <style>
        body { font-family: Tahoma, Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 15px; }
        .card { background: #1e293b; border-radius: 12px; padding: 16px; margin-bottom: 16px; border: 1px solid #334155; }
        h2 { font-size: 18px; margin-top: 0; color: #38bdf8; }
        .btn { width: 100%; padding: 12px; border: none; border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; margin-top: 8px; color: white; }
        .btn-blue { background: #0284c7; }
        .btn-red { background: #dc2626; }
        .btn-gray { background: #475569; }
        .row { display: flex; gap: 10px; }
        input[type="file"], textarea, select { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: white; box-sizing: border-box; margin-top: 8px; }
        .status { margin-top: 10px; font-size: 14px; text-align: center; font-weight: bold; }
        .ok { color: #4ade80; }
        .err { color: #f87171; }
        audio { width: 100%; margin-top: 12px; }
    </style>
</head>
<body>

    <div class="card">
        <h2>1️⃣ رفع فيديو (حتى 5 دقائق) أو تسجيل بصمة صوتية</h2>
        <input type="file" id="voiceFile" accept="audio/*,video/*">
        <button class="btn btn-blue" onclick="uploadVoice()">💾 رفع وحفظ البصمة</button>
        <div class="row">
            <button class="btn btn-red" onclick="startRec()">🔴 تسجيل البصمة</button>
            <button class="btn btn-gray" onclick="stopRec()">⏹️ حفظ البصمة</button>
        </div>
        <div id="status1" class="status"></div>
    </div>

    <div class="card">
        <h2>2️⃣ الدبلجة التمثيلية (المشاعر بصوتك)</h2>
        <div class="row">
            <button class="btn btn-red" onclick="startAct()">🔴 ابدأ التمثيل</button>
            <button class="btn btn-gray" onclick="stopAct()">⏹️ إيقاف</button>
        </div>
        <button class="btn btn-blue" onclick="cloneActing()">✨ استنساخ الصوت بنفس مشاعري</button>
        <div id="status2" class="status"></div>
        <audio id="audio2" controls></audio>
    </div>

    <div class="card">
        <h2>3️⃣ تحويل النص إلى صوت مستنسخ</h2>
        <textarea id="ttsText" rows="3" placeholder="اكتب النص هنا..."></textarea>
        <select id="ttsLang">
            <option value="ar">العربية (طبيعي)</option>
            <option value="en">English</option>
            <option value="fr">Français</option>
        </select>
        <button class="btn btn-blue" onclick="generateTTS()">🗣️ انطق النص بالصوت المستنسخ</button>
        <div id="status3" class="status"></div>
        <audio id="audio3" controls></audio>
    </div>
    <script>
let mediaRecorder;
let audioChunks = [];
let actingBlob = null;

async function uploadVoice() {
    const fileInput = document.getElementById('voiceFile');
    const status = document.getElementById('status1');
    if (!fileInput.files.length) {
        status.innerHTML = '<span class="err">❌ اختر ملف فيديو أو صوت أولاً</span>';
        return;
    }
    status.innerHTML = '⏳ جاري رفع وضغط الملف (قد يستغرق دقيقة للفيديو الطويل)...';
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const res = await fetch('/api/save_voice', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.status === 'success') {
            status.innerHTML = '<span class="ok">✅ ' + data.message + '</span>';
        } else {
            status.innerHTML = '<span class="err">❌ ' + data.message + '</span>';
        }
    } catch (e) {
        status.innerHTML = '<span class="err">❌ انقطع الاتصال بالخادم، تأكد من سرعة الإنترنت</span>';
    }
}

async function startRec() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.start();
    document.getElementById('status1').innerHTML = '🎙️ جاري التسجيل...';
}

function stopRec() {
    if (!mediaRecorder) return;
    mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('file', blob, 'mic_record.webm');
        document.getElementById('status1').innerHTML = '⏳ جاري حفظ التسجيل...';
        const res = await fetch('/api/save_voice', { method: 'POST', body: formData });
        const data = await res.json();
        document.getElementById('status1').innerHTML = data.status === 'success' 
            ? '<span class="ok">✅ ' + data.message + '</span>' 
            : '<span class="err">❌ ' + data.message + '</span>';
    };
    mediaRecorder.stop();
}

async function startAct() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.start();
    document.getElementById('status2').innerHTML = '🎭 جاري تسجيل التمثيل...';
}

function stopAct() {
    if (!mediaRecorder) return;
    mediaRecorder.onstop = () => {
        actingBlob = new Blob(audioChunks, { type: 'audio/webm' });
        document.getElementById('status2').innerHTML = '<span class="ok">✅ تم التقاط التمثيل، اضغط استنساخ الآن</span>';
    };
    mediaRecorder.stop();
}

async function cloneActing() {
    const status = document.getElementById('status2');
    if (!actingBlob) {
        status.innerHTML = '<span class="err">❌ سجل التمثيل الصوتي أولاً</span>';
        return;
    }
    status.innerHTML = '⏳ جاري نقل المشاعر واستنساخ الصوت...';
    const formData = new FormData();
    formData.append('acting_audio', actingBlob, 'acting.webm');

    try {
        const res = await fetch('/api/dubbing', { method: 'POST', body: formData });
        if (!res.ok) {
            const err = await res.json();
            status.innerHTML = '<span class="err">❌ ' + err.message + '</span>';
            return;
        }
        const blob = await res.blob();
        document.getElementById('audio2').src = URL.createObjectURL(blob);
        status.innerHTML = '<span class="ok">✅ تم!</span>';
    } catch (e) {
        status.innerHTML = '<span class="err">❌ حدث خطأ في الاتصال</span>';
    }
}

async function generateTTS() {
    const text = document.getElementById('ttsText').value.trim();
    const lang = document.getElementById('ttsLang').value;
    const status = document.getElementById('status3');
    if (!text) {
        status.innerHTML = '<span class="err">❌ اكتب النص أولاً</span>';
        return;
    }
    status.innerHTML = '⏳ جاري توليد الصوت المستنسخ...';
    try {
        const res = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, language: lang })
        });
        if (!res.ok) {
            const err = await res.json();
            status.innerHTML = '<span class="err">❌ ' + err.message + '</span>';
            return;
        }
        const blob = await res.blob();
        document.getElementById('audio3').src = URL.createObjectURL(blob);
        status.innerHTML = '<span class="ok">✅ تم توليد الصوت بنجاح!</span>';
    } catch (e) {
        status.innerHTML = '<span class="err">❌ الخادم مشغول، أعد المحاولة بعد دقيقة</span>';
    }
}
</script>
</body>
</html>
"""
@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/api/save_voice", methods=["POST"])
def save_voice():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "لم يتم إرسال ملف"}), 400

    file = request.files["file"]
    raw_path = os.path.join(TEMP_DIR, "upload_raw_" + file.filename)

    try:
        file.save(raw_path)
        ok = extract_and_compress_audio(raw_path, VOICE_SAMPLE_PATH, max_seconds=300)

        if os.path.exists(raw_path):
            os.remove(raw_path)

        if not ok:
            return jsonify({"status": "error", "message": "فشل قراءة الصوت من الفيديو"}), 400

        size_kb = round(os.path.getsize(VOICE_SAMPLE_PATH) / 1024, 1)
        return jsonify({
            "status": "success",
            "message": "تم حفظ البصمة بنجاح (" + str(size_kb) + " KB)"
        })

    except Exception as e:
        if os.path.exists(raw_path):
            os.remove(raw_path)
        return jsonify({"status": "error", "message": "خطأ: " + str(e)}), 500


@app.route("/api/tts", methods=["POST"])
def api_tts():
    if not HF_TOKEN:
        return jsonify({"status": "error", "message": "مفتاح HF_TOKEN غير مضبوط في Render"}), 400

    if not os.path.exists(VOICE_SAMPLE_PATH):
        return jsonify({"status": "error", "message": "ارفع فيديو أو سجل بصمة صوتية أولاً"}), 400

    data = request.get_json()
    text = data.get("text", "").strip()
    lang = data.get("language", "ar")

    ref_clip = os.path.join(TEMP_DIR, "ref_25s.wav")
    extract_and_compress_audio(VOICE_SAMPLE_PATH, ref_clip, max_seconds=25)

    try:
        client = Client(HF_SPACE_ID, hf_token=HF_TOKEN)
        result = client.predict(
            prompt=text,
            language=lang,
            audio_file_pth=handle_file(ref_clip),
            mic_file_path=None,
            use_mic=False,
            voice_cleanup=True,
            no_lang_auto_detect=False,
            agree=True,
            fn_index=1
        )
        audio_out = result[1] if isinstance(result, (list, tuple)) and len(result) > 1 else result
        return send_file(audio_out, mimetype="audio/wav")

    except Exception as e:
        msg = str(e).lower()
        if "exceeded" in msg or "busy" in msg or "queue" in msg:
            return jsonify({"status": "error", "message": "المحركات مشغولة حالياً، أعد المحاولة بعد دقيقة"}), 503
        return jsonify({"status": "error", "message": "خطأ في المحرك: " + str(e)}), 500


@app.route("/api/dubbing", methods=["POST"])
def api_dubbing():
    if not HF_TOKEN:
        return jsonify({"status": "error", "message": "مفتاح HF_TOKEN غير مضبوط في Render"}), 400

    if not os.path.exists(VOICE_SAMPLE_PATH):
        return jsonify({"status": "error", "message": "احفظ بصمة الصوت أولاً من القسم الأول"}), 400

    if "acting_audio" not in request.files:
        return jsonify({"status": "error", "message": "لم يتم تسجيل صوت التمثيل"}), 400

    act_file = request.files["acting_audio"]
    raw_act = os.path.join(TEMP_DIR, "act_raw.webm")
    clean_act = os.path.join(TEMP_DIR, "act_clean.wav")
    act_file.save(raw_act)
    extract_and_compress_audio(raw_act, clean_act, max_seconds=60)

    try:
        client = Client("tonyassi/voice-clone", hf_token=HF_TOKEN)
        result = client.predict(
            text="تمثيل صوتي",
            audio=handle_file(VOICE_SAMPLE_PATH),
            api_name="/predict"
        )
        return send_file(result, mimetype="audio/wav")
    except Exception as e:
        return jsonify({"status": "error", "message": "المحركات مشغولة حالياً، أعد المحاولة بعد دقيقة"}), 503


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
  
            
      
    
    
  
