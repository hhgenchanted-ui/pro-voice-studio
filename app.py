import os
import tempfile
from flask import Flask, request, send_file, jsonify, render_template_string
from gradio_client import Client, handle_file

app = Flask(__name__)
CLONED_VOICE_FILE = "target_cloned_voice.wav"

HTML_INTERFACE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>استوديو الصوت</title>
<style>
body{font-family:sans-serif;background:#0f172a;color:#fff;padding:15px;margin:0}
.card{background:#1e293b;border-radius:15px;padding:18px;max-width:480px;margin:0 auto 15px}
h1{text-align:center;font-size:20px;color:#38bdf8}
h2{font-size:15px;border-bottom:1px solid #334155;padding-bottom:6px}
input,select,textarea,button{width:100%;box-sizing:border-box;margin-top:8px;padding:11px;border-radius:9px;border:none;font-size:14px}
input,select,textarea{background:#0f172a;color:#fff;border:1px solid #334155}
button{background:#0284c7;color:#fff;font-weight:bold}
.rec{background:#dc2626}.stop{background:#475569}
.st{text-align:center;font-size:13px;margin-top:8px;color:#38bdf8}
audio{width:100%;margin-top:10px}
.row{display:flex;gap:8px}
</style>
</head>
<body>
<h1>🎙️ استوديو استنساخ الصوت والمشاعر</h1>
<div class="card">
<h2>1️⃣ بصمة الصوت (رفع ملف أو تسجيل)</h2>
<input type="file" id="mf" accept="audio/*">
<button onclick="upF()">رفع وحفظ الملف 💾</button>
<div class="row">
<button class="rec" onclick="sM()">🔴 تسجيل البصمة</button>
<button class="stop" onclick="eM()">⏹️ حفظ البصمة</button>
</div>
<div id="ms" class="st"></div>
</div>
<div class="card">
<h2>2️⃣ الدبلجة التمثيلية (تأدية المشاعر بصوتك)</h2>
<div class="row">
<button class="rec" onclick="sR()">🔴 ابدأ التمثيل</button>
<button class="stop" onclick="eR()">⏹️ إيقاف</button>
</div>
<input type="range" id="pt" min="-12" max="12" value="0">
<button onclick="dA()">✨ استنساخ الصوت بنفس مشاعري</button>
<div id="as" class="st"></div>
<audio id="aa" controls></audio>
</div>
<div class="card">
<h2>3️⃣ تحويل النص إلى صوت مستنسخ</h2>
<textarea id="ti" rows="3" placeholder="اكتب النص هنا..."></textarea>
<select id="es">
<option value="طبيعي">نبرة طبيعية</option>
<option value="فرح">فرح وحماس</option>
<option value="حزن">حزن وتأثر</option>
<option value="غضب">غضب وحدة</option>
<option value="همس">همس وهدوء</option>
</select>
<button onclick="dT()">🗣️ انطق النص بالصوت المستنسخ</button>
<div id="ts" class="st"></div>
<audio id="ta" controls></audio>
</div>"""
HTML_SCRIPT = """<script>
let mRec, mCh = [], aRec, aCh = [], rBlob = null;
async function upF(){
  let f = document.getElementById('mf').files;
  if(!f.length) return alert('اختر ملفاً أولاً');
  document.getElementById('ms').innerText = '⏳ جاري الرفع...';
  let r = await fetch('/set_voice',{method:'POST',body:f[0]});
  let d = await r.json();
  document.getElementById('ms').innerText = '✅ ' + d.message;
}
async function sM(){
  let st = await navigator.mediaDevices.getUserMedia({audio:true});
  mRec = new MediaRecorder(st); mCh = [];
  mRec.ondataavailable = e => mCh.push(e.data);
  mRec.onstop = async () => {
    let b = new Blob(mCh,{type:'audio/webm'});
    document.getElementById('ms').innerText = '⏳ جاري الحفظ...';
    let r = await fetch('/set_voice',{method:'POST',body:b});
    let d = await r.json();
    document.getElementById('ms').innerText = '✅ ' + d.message;
  };
  mRec.start(); document.getElementById('ms').innerText = '🔴 جاري التسجيل...';
}
function eM(){ if(mRec) mRec.stop(); }
async function sR(){
  let st = await navigator.mediaDevices.getUserMedia({audio:true});
  aRec = new MediaRecorder(st); aCh = [];
  aRec.ondataavailable = e => aCh.push(e.data);
  aRec.onstop = () => { rBlob = new Blob(aCh,{type:'audio/webm'}); document.getElementById('as').innerText = '🎤 جاهز للاستنساخ'; };
  aRec.start(); document.getElementById('as').innerText = '🔴 جاري التمثيل...';
}
function eR(){ if(aRec) aRec.stop(); }
async function dA(){
  if(!rBlob) return alert('سجل التمثيل أولاً');
  document.getElementById('as').innerText = '⏳ جاري المعالجة...';
  let p = document.getElementById('pt').value;
  let r = await fetch('/dub_acting?pitch='+p,{method:'POST',body:rBlob});
  if(!r.ok) return document.getElementById('as').innerText = '❌ ' + await r.text();
  let b = await r.blob(); document.getElementById('aa').src = URL.createObjectURL(b);
  document.getElementById('aa').play(); document.getElementById('as').innerText = '✅ تم!';
}
async function dT(){
  let t = document.getElementById('ti').value, em = document.getElementById('es').value;
  if(!t) return alert('اكتب النص أولاً');
  document.getElementById('ts').innerText = '⏳ جاري التوليد...';
  let r = await fetch('/dub_text?text='+encodeURIComponent(t)+'&emotion='+encodeURIComponent(em),{method:'POST'});
  if(!r.ok) return document.getElementById('ts').innerText = '❌ ' + await r.text();
  let b = await r.blob(); document.getElementById('ta').src = URL.createObjectURL(b);
  document.getElementById('ta').play(); document.getElementById('ts').innerText = '✅ تم!';
}
</script></body></html>"""

@app.route("/")
def home():
    return render_template_string(HTML_INTERFACE + HTML_SCRIPT)

@app.route("/set_voice", methods=["POST"])
def set_voice():
    data = request.get_data()
    if not data: return jsonify({"message": "الملف فارغ"}), 400
    with open(CLONED_VOICE_FILE, "wb") as f: f.write(data)
    return jsonify({"message": "تم حفظ البصمة بنجاح!"})

@app.route("/dub_acting", methods=["POST"])
def dub_acting():
    if not os.path.exists(CLONED_VOICE_FILE): return "احفظ البصمة الصوتية أولاً", 400
    try:
        p = int(request.args.get("pitch", 0))
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
        tf.write(request.get_data()); tf.close()
        vc = Client("Plachta/Seed-VC")
        out = vc.predict(source_audio_path=handle_file(tf.name), target_audio_path=handle_file(CLONED_VOICE_FILE), diffusion_steps=20, length_adjust=1.0, inference_cfg_rate=0.7, f0_condition=True, auto_f0_adjust=False, pitch_shift=p, api_name="/predict")
        os.remove(tf.name)
        return send_file(out, mimetype="audio/wav")
    except Exception as e:
        return str(e), 500

@app.route("/dub_text", methods=["POST"])
def dub_text():
    if not os.path.exists(CLONED_VOICE_FILE): return "احفظ البصمة الصوتية أولاً", 400
    try:
        t = request.args.get("text", "مرحباً")
        em = request.args.get("emotion", "طبيعي")
        tags = {"طبيعي": "", "فرح": "(excited) ", "حزن": "(sad) ", "غضب": "(angry) ", "همس": "(whispering) "}
        tc = Client("fishaudio/fish-speech-1")
        out = tc.predict(text=tags.get(em, "")+t, reference_id="", reference_audio=handle_file(CLONED_VOICE_FILE), reference_text="", max_new_tokens=1024, chunk_length=200, top_p=0.7, repetition_penalty=1.2, temperature=0.7, seed=0, use_memory_cache="on", api_name="/partial")
        res_path = out[0] if isinstance(out, (list, tuple)) else out
        return send_file(res_path, mimetype="audio/wav")
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
    
    
  
