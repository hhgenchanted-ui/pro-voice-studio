import os
import tempfile
from flask import Flask, request, send_file, jsonify, render_template_string
from gradio_client import Client, handle_file

app = Flask(__name__)
CLONED_VOICE_FILE = "target_cloned_voice.wav"

HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>استوديو استنساخ الصوت الاحترافي</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 16px; }
        .card { background: #1e293b; border-radius: 16px; padding: 20px; max-width: 500px; margin: 0 auto 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        h1 { text-align: center; font-size: 22px; color: #38bdf8; margin-bottom: 5px; }
        p.sub { text-align: center; font-size: 13px; color: #94a3b8; margin-top: 0; }
        h2 { font-size: 16px; color: #e2e8f0; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-top: 0; }
        input, select, textarea, button { width: 100%; box-sizing: border-box; margin-top: 10px; padding: 12px; border-radius: 10px; border: none; font-size: 15px; }
        input[type="file"], select, textarea { background: #0f172a; color: #fff; border: 1px solid #334155; }
        button { background: linear-gradient(135deg, #0284c7, #2563eb); color: white; font-weight: bold; cursor: pointer; }
        button:active { transform: scale(0.98); }
        button.rec { background: linear-gradient(135deg, #dc2626, #b91c1c); }
        button.stop { background: #475569; }
        .status { text-align: center; font-size: 13px; margin-top: 10px; color: #38bdf8; }
        audio { width: 100%; margin-top: 12px; border-radius: 8px; }
        .row { display: flex; gap: 10px; }
    </style>
</head>
<body>
    <h1>🎙️ استوديو استنساخ الصوت والمشاعر</h1>
    <p class="sub">يعمل 24 ساعة • جودة استوديو بدون صوت روبوت</p>

    <div class="card">
        <h2>1️⃣ بصمة الصوت المراد استنساخها (حتى 5 دقائق)</h2>
        <input type="file" id="masterFile" accept="audio/*">
        <button onclick="uploadMaster()">حفظ البصمة الصوتية في السيرفر 💾</button>
        <div id="masterStatus" class="status"></div>
    </div>

    <div class="card">
        <h2>2️⃣ الدبلجة التمثيلية (تأدية المشاعر بصوتك)</h2>
        <div class="row">
            <button class="rec" onclick="startRec()">🔴 ابدأ التمثيل</button>
            <button class="stop" onclick="stopRec()">⏹️ إيقاف</button>
        </div>
        <label style="font-size:13px; color:#94a3b8; display:block; margin-top:10px;">طبقة الصوت (عميق -12 إلى حاد +12): <span id="pitchVal">0</span></label>
        <input type="range" id="pitch" min="-12" max="12" value="0" oninput="document.getElementById('pitchVal').innerText=this.value">
        <button onclick="dubActing()">✨ استنساخ الصوت بنفس مشاعري</button>
        <div id="actStatus" class="status"></div>
        <audio id="actAudio" controls></audio>
    </div>

    <div class="card">
        <h2>3️⃣ تحويل النص إلى صوت مستنسخ</h2>
        <textarea id="textInput" rows="3" placeholder="اكتب النص الذي تريد نطقه بالصوت المستنسخ..."></textarea>
        <select id="emotionSelect">
            <option value="طبيعي">نبرة طبيعية</option>
            <option value="فرح">😄 فرح وحماس</option>
            <option value="حزن">😢 حزن وتأثر</option>
            <option value="غضب">😠 غضب وحدة</option>
            <option value="همس">🤫 همس وهدوء</option>
        </select>
        <button onclick="dubText()">🗣️ انطق النص بالصوت المستنسخ</button>
        <div id="txtStatus" class="status"></div>
        <audio id="txtAudio" controls></audio>
    </div>

    <script>
        let mediaRecorder, audioChunks = [], recordedBlob = null;

        async function uploadMaster() {
            const file = document.getElementById('masterFile').files[0];
            if (!file) return alert('اختر ملف الصوت أولاً');
            document.getElementById('masterStatus').innerText = '⏳ جاري رفع وحفظ البصمة...';
            const res = await fetch('/set_voice', { method: 'POST', body: file });
            const data = await res.json();
            document.getElementById('masterStatus').innerText = '✅ ' + data.message;
        }

        async function startRec() {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
            mediaRecorder.onstop = () => {
                recordedBlob = new Blob(audioChunks, { type: 'audio/wav' });
                document.getElementById('actStatus').innerText = '🎤 تم تسجيل أدائك، اضغط زر الاستنساخ الآن';
            };
            mediaRecorder.start();
            document.getElementById('actStatus').innerText = '🔴 جاري التسجيل... مثّل مشاعرك الآن';
        }

        function stopRec() {
            if (mediaRecorder) mediaRecorder.stop();
        }

        async function dubActing() {
            if (!recordedBlob) return alert('سجّل أداءك التمثيلي أولاً');
            document.getElementById('actStatus').innerText = '⏳ جاري المعالجة في الاستوديو (قد يستغرق 20 ثانية)...';
            const pitch = document.getElementById('pitch').value;
            const res = await fetch('/dub_acting?pitch=' + pitch, { method: 'POST', body: recordedBlob });
            if (!res.ok) return document.getElementById('actStatus').innerText = '❌ ' + await res.text();
            const blob = await res.blob();
            document.getElementById('actAudio').src = URL.createObjectURL(blob);
            document.getElementById('actAudio').play();
            document.getElementById('actStatus').innerText = '✅ تم الإنتاج بنجاح!';
        }

        async function dubText() {
            const text = document.getElementById('textInput').value;
            const emotion = document.getElementById('emotionSelect').value;
            if (!text) return alert('اكتب النص أولاً');
            document.getElementById('txtStatus').innerText = '⏳ جاري توليد الصوت بالمشاعر...';
            const res = await fetch('/dub_text?text=' + encodeURIComponent(text) + '&emotion=' + encodeURIComponent(emotion), { method: 'POST' });
            if (!res.ok) return document.getElementById('txtStatus').innerText = '❌ ' + await res.text();
            const blob = await res.blob();
            document.getElementById('txtAudio').src = URL.createObjectURL(blob);
            document.getElementById('txtAudio').play();
            document.getElementById('txtStatus').innerText = '✅ تم توليد الصوت بنجاح!';
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_INTERFACE)

@app.route("/set_voice", methods=["POST"])
def set_cloned_voice():
    with open(CLONED_VOICE_FILE, "wb") as f:
        f.write(request.data)
    return jsonify({"status": "ok", "message": "تم حفظ البصمة الصوتية بنجاح!"})

@app.route("/dub_acting", methods=["POST"])
def dub_acting():
    if not os.path.exists(CLONED_VOICE_FILE):
        return "يرجى حفظ البصمة الصوتية في القسم 1 أولاً", 400
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
        return "يرجى حفظ البصمة الصوتية في القسم 1 أولاً", 400
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
    
  
