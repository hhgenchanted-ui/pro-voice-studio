import os, tempfile
from flask import Flask, request, send_file, jsonify, render_template_string
from gradio_client import Client, handle_file

app = Flask(__name__)
VOICE_FILE = "target_voice.wav"

HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>استوديو الصوت</title><style>
body{font-family:sans-serif;background:#0b1120;color:#fff;padding:12px;margin:0}
.c{background:#1e293b;border-radius:14px;padding:16px;max-width:480px;margin:0 auto 12px;border:1px solid #334155}
h1{text-align:center;font-size:20px;color:#38bdf8;margin:4px 0}
h2{font-size:15px;border-bottom:1px solid #334155;padding-bottom:6px;margin-top:0}
input,select,textarea,button{width:100%;box-sizing:border-box;margin-top:8px;padding:11px;border-radius:9px;border:none;font-size:14px}
input,select,textarea{background:#0f172a;color:#fff;border:1px solid #475569}
button{background:#0284c7;color:#fff;font-weight:bold}.rec{background:#dc2626}.stop{background:#475569}.mic{background:#059669}
.st{text-align:center;font-size:13px;margin-top:8px;color:#38bdf8;word-wrap:break-word}
audio{width:100%;margin-top:8px}.row{display:flex;gap:8px}
</style></head><body>
<h1>🎙️ استوديو استنساخ الصوت والمشاعر</h1>
<div class="c"><button class="mic" onclick="askMic()">🎤 تفعيل إذن المايكروفون</button><div id="mSt" class="st"></div></div>
<div class="c"><h2>1️⃣ بصمة الصوت المراد استنساخها</h2>
<input type="file" id="mf" accept="audio/*"><button onclick="upF()">رفع وحفظ الملف 💾</button>
<div class="row"><button class="rec" onclick="sM()">🔴 تسجيل البصمة</button><button class="stop" onclick="eM()">⏹️ حفظ البصمة</button></div>
<div id="ms" class="st"></div></div>
<div class="c"><h2>2️⃣ الدبلجة التمثيلية (المشاعر بصوتك)</h2>
<div class="row"><button class="rec" onclick="sR()">🔴 ابدأ التمثيل</button><button class="stop" onclick="eR()">⏹️ إيقاف</button></div>
<input type="range" id="pt" min="-12" max="12" value="0">
<button onclick="dA()">✨ استنساخ الصوت بنفس مشاعري</button><div id="as" class="st"></div><audio id="aa" controls></audio></div>
<div class="c"><h2>3️⃣ تحويل النص إلى صوت مستنسخ</h2>
<textarea id="ti" rows="3" placeholder="اكتب النص هنا..."></textarea>
<select id="es"><option value="طبيعي">طبيعي</option><option value="فرح">فرح</option><option value="حزن">حزن</option><option value="غضب">غضب</option><option value="همس">همس</option></select>
<button onclick="dT()">🗣️ انطق النص بالصوت المستنسخ</button><div id="ts" class="st"></div><audio id="ta" controls></audio></div>
<script>
let mR,mC=[],aR,aC=[],rB=null;
async function askMic(){try{let s=await navigator.mediaDevices.getUserMedia({audio:true});s.getTracks().forEach(t=>t.stop());document.getElementById('mSt').innerText='✅ مفعل';}catch(e){document.getElementById('mSt').innerText='⚠️ اسمح بالمايكروفون من إعدادات المتصفح';}}
async function upF(){let f=document.getElementById('mf').files;if(!f.length)return alert('اختر ملفاً');document.getElementById('ms').innerText='⏳ جاري الرفع...';let r=await fetch('/set_voice',{method:'POST',body:f[0]});let d=await r.json();document.getElementById('ms').innerText='✅ '+d.message;}
async function sM(){try{let s=await navigator.mediaDevices.getUserMedia({audio:true});mR=new MediaRecorder(s);mC=[];mR.ondataavailable=e=>mC.push(e.data);mR.onstop=async()=>{let b=new Blob(mC,{type:'audio/webm'});document.getElementById('ms').innerText='⏳ جاري الحفظ...';let r=await fetch('/set_voice',{method:'POST',body:b});let d=await r.json();document.getElementById('ms').innerText='✅ '+d.message;};mR.start();document.getElementById('ms').innerText='🔴 يسجل...';}catch(e){askMic();}}
function eM(){if(mR&&mR.state!=='inactive')mR.stop();}
async function sR(){try{let s=await navigator.mediaDevices.getUserMedia({audio:true});aR=new MediaRecorder(s);aC=[];aR.ondataavailable=e=>aC.push(e.data);aR.onstop=()=>{rB=new Blob(aC,{type:'audio/webm'});document.getElementById('as').innerText='🎤 جاهز للاستنساخ';};aR.start();document.getElementById('as').innerText='🔴 يسجل التمثيل...';}catch(e){askMic();}}
function eR(){if(aR&&aR.state!=='inactive')aR.stop();}
async function dA(){if(!rB)return alert('سجل التمثيل أولاً');document.getElementById('as').innerText='⏳ جاري المعالجة...';let r=await fetch('/dub_acting?pitch='+document.getElementById('pt').value,{method:'POST',body:rB});if(!r.ok)return document.getElementById('as').innerText='❌ '+await r.text();let u=URL.createObjectURL(await r.blob());document.getElementById('aa').src=u;document.getElementById('aa').play();document.getElementById('as').innerText='✅ تم!';}
async function dT(){let t=document.getElementById('ti').value;if(!t)return alert('اكتب النص');document.getElementById('ts').innerText='⏳ جاري التوليد...';let r=await fetch('/dub_text?text='+encodeURIComponent(t)+'&emotion='+encodeURIComponent(document.getElementById('es').value),{method:'POST'});if(!r.ok)return document.getElementById('ts').innerText='❌ '+await r.text();let u=URL.createObjectURL(await r.blob());document.getElementById('ta').src=u;document.getElementById('ta').play();document.getElementById('ts').innerText='✅ تم!';}
</script></body></html>"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/set_voice", methods=["POST"])
def set_voice():
    d = request.get_data()
    if not d: return jsonify({"message": "فارغ"}), 400
    with open(VOICE_FILE, "wb") as f: f.write(d)
    return jsonify({"message": f"تم حفظ البصمة ({len(d)//1024} KB)"})

@app.route("/dub_acting", methods=["POST"])
def dub_acting():
    if not os.path.exists(VOICE_FILE): return "احفظ البصمة أولاً", 400
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    tf.write(request.get_data()); tf.close()
    try:
        vc = Client("Plachta/Seed-VC")
        out = vc.predict(handle_file(tf.name), handle_file(VOICE_FILE), 25, 1.0, 0.7, True, False, int(request.args.get("pitch", 0)), api_name="/predict")
        os.remove(tf.name)
        return send_file(out[0] if isinstance(out, (list, tuple)) else out, mimetype="audio/wav")
    except Exception as e:
        if os.path.exists(tf.name): os.remove(tf.name)
        return str(e), 500

@app.route("/dub_text", methods=["POST"])
def dub_text():
    if not os.path.exists(VOICE_FILE): return "احفظ البصمة أولاً", 400
    t = request.args.get("text", "مرحبا")
    for sp in ["tonyassi/voice-clone", "coqui/xtts", "mrfakename/E2-F5-TTS"]:
        try:
            tc = Client(sp)
            if "tonyassi" in sp: out = tc.predict(t, handle_file(VOICE_FILE), api_name="/predict")
            elif "xtts" in sp: out = tc.predict(t, "ar", handle_file(VOICE_FILE), None, False, True, False, True, api_name="/predict")
            else: out = tc.predict(handle_file(VOICE_FILE), "", t, False, True, 0.15, 32, 1.0, api_name="/basic_tts")
            return send_file(out[0] if isinstance(out, (list, tuple)) else out, mimetype="audio/wav")
        except Exception: continue
    return "المحركات مشغولة حالياً، أعد المحاولة بعد دقيقة", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
      
      
    
    
  
