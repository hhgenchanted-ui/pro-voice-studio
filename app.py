import os, tempfile
from flask import Flask, request, send_file, jsonify, render_template_string
from gradio_client import Client, handle_file

app = Flask(__name__)
VOICE_FILE = "target_voice.wav"

HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>استوديو الصوت الاحترافي</title><style>
body{font-family:sans-serif;background:#0b1120;color:#fff;padding:12px;margin:0}
.c{background:#1e293b;border-radius:14px;padding:16px;max-width:480px;margin:0 auto 12px;border:1px solid #334155}
h1{text-align:center;font-size:20px;color:#38bdf8;margin:4px 0}
h2{font-size:15px;border-bottom:1px solid #334155;padding-bottom:6px;margin-top:0}
input,select,textarea,button{width:100%;box-sizing:border-box;margin-top:8px;padding:11px;border-radius:9px;border:none;font-size:14px}
input,select,textarea{background:#0f172a;color:#fff;border:1px solid #475569}
button{background:#0284c7;color:#fff;font-weight:bold;cursor:pointer}
.rec{background:#dc2626}.stop{background:#475569}.mic{background:#059669}
.st{text-align:center;font-size:13px;margin-top:8px;color:#38bdf8;word-wrap:break-word}
audio{width:100%;margin-top:10px}.row{display:flex;gap:8px}
.dl{display:none;text-align:center;background:#10b981;color:#fff;padding:10px;border-radius:9px;text-decoration:none;margin-top:8px;font-weight:bold}
</style></head><body>
<h1>🎙️ استوديو استنساخ الصوت والمشاعر</h1>
<div class="c"><button class="mic" onclick="askMic()">🎤 تفعيل إذن المايكروفون</button><div id="mSt" class="st"></div></div>
<div class="c"><h2>1️⃣ بصمة الصوت المراد استنساخها</h2>
<input type="file" id="mf" accept="audio/*"><button onclick="upF()">رفع وحفظ الملف 💾</button>
<div class="row"><button class="rec" onclick="sM()">🔴 تسجيل البصمة</button><button class="stop" onclick="eM()">⏹️ حفظ البصمة</button></div>
<div id="ms" class="st"></div></div>
<div class="c"><h2>2️⃣ الدبلجة التمثيلية (المشاعر بصوتك)</h2>
<div class="row"><button class="rec" onclick="sR()">🔴 ابدأ التمثيل</button><button class="stop" onclick="eR()">⏹️ إيقاف</button></div>
<label style="font-size:12px;color:#94a3b8;display:block;margin-top:6px">طبقة الصوت: <span id="pv">0</span></label>
<input type="range" id="pt" min="-12" max="12" value="0" oninput="document.getElementById('pv').innerText=this.value">
<button onclick="dA()">✨ استنساخ الصوت بنفس مشاعري</button>
<div id="as" class="st"></div><audio id="aa" controls playsinline></audio>
<a id="dlA" class="dl" download="dubbed_acting.wav">⬇️ تحميل الصوت المستنسخ</a></div>
<div class="c"><h2>3️⃣ تحويل النص إلى صوت مستنسخ</h2>
<textarea id="ti" rows="3" placeholder="اكتب النص هنا..."></textarea>
<select id="es"><option value="طبيعي">طبيعي</option><option value="فرح">فرح وحماس</option><option value="حزن">حزن</option><option value="غضب">غضب</option><option value="همس">همس</option></select>
<button onclick="dT()">🗣️ انطق النص بالصوت المستنسخ</button>
<div id="ts" class="st"></div><audio id="ta" controls playsinline></audio>
<a id="dlT" class="dl" download="cloned_text.wav">⬇️ تحميل الصوت المستنسخ</a></div>
<script>
let mR,mC=[],aR,aC=[],rB=null;
async function askMic(){try{let s=await navigator.mediaDevices.getUserMedia({audio:true});s.getTracks().forEach(t=>t.stop());document.getElementById('mSt').innerText='✅ المايكروفون مفعل';}catch(e){document.getElementById('mSt').innerText='⚠️ اسمح بالمايكروفون من إعدادات المتصفح';}}
async function upF(){let f=document.getElementById('mf').files;if(!f.length)return alert('اختر ملفاً');document.getElementById('ms').innerText='⏳ جاري الرفع...';let r=await fetch('/set_voice',{method:'POST',body:f});let d=await r.json();document.getElementById('ms').innerText='✅ '+d.message;}
async function sM(){try{let s=await navigator.mediaDevices.getUserMedia({audio:true});mR=new MediaRecorder(s);mC=[];mR.ondataavailable=e=>mC.push(e.data);mR.onstop=async()=>{let b=new Blob(mC,{type:'audio/webm'});document.getElementById('ms').innerText='⏳ جاري الحفظ...';let r=await fetch('/set_voice',{method:'POST',body:b});let d=await r.json();document.getElementById('ms').innerText='✅ '+d.message;};mR.start();document.getElementById('ms').innerText='🔴 يسجل البصمة...';}catch(e){askMic();}}
function eM(){if(mR&&mR.state!=='inactive')mR.stop();}
async function sR(){try{let s=await navigator.mediaDevices.getUserMedia({audio:true});aR=new MediaRecorder(s);aC=[];aR.ondataavailable=e=>aC.push(e.data);aR.onstop=()=>{rB=new Blob(aC,{type:'audio/webm'});document.getElementById('as').innerText='🎤 جاهز للاستنساخ';};aR.start();document.getElementById('as').innerText='🔴 يسجل التمثيل...';}catch(e){askMic();}}
function eR(){if(aR&&aR.state!=='inactive')aR.stop();}
async function playRes(res, audioId, dlId, stId){
  let buf = await res.arrayBuffer();
  if(buf.byteLength < 500) return document.getElementById(stId).innerText = '❌ الملف الصوتي فارغ، أعد المحاولة';
  let blob = new Blob([buf], {type: 'audio/wav'});
  let u = URL.createObjectURL(blob);
  let au = document.getElementById(audioId);
  au.src = u; au.load(); au.play().catch(()=>{});
  let dl = document.getElementById(dlId);
  dl.href = u; dl.style.display = 'block';
  document.getElementById(stId).innerText = '✅ تم الإنتاج! اضغط تشغيل أو تحميل';
}
async function dA(){if(!rB)return alert('سجل التمثيل أولاً');document.getElementById('as').innerText='⏳ جاري المعالجة...';let r=await fetch('/dub_acting?pitch='+document.getElementById('pt').value,{method:'POST',body:rB});if(!r.ok)return document.getElementById('as').innerText='❌ '+await r.text();await playRes(r,'aa','dlA','as');}
async function dT(){let t=document.getElementById('ti').value;if(!t)return alert('اكتب النص');document.getElementById('ts').innerText='⏳ جاري التوليد...';let r=await fetch('/dub_text?text='+encodeURIComponent(t)+'&emotion='+encodeURIComponent(document.getElementById('es').value),{method:'POST'});if(!r.ok)return document.getElementById('ts').innerText='❌ '+await r.text();await playRes(r,'ta','dlT','ts');}
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
    hf_token = os.environ.get("HF_TOKEN")
    try:
        vc = Client("Plachta/Seed-VC", token=hf_token)
        out = vc.predict(handle_file(tf.name), handle_file(VOICE_FILE), 25, 1.0, 0.7, True, False, int(request.args.get("pitch", 0)), api_name="/predict")
        os.remove(tf.name)
        res = out if isinstance(out, (list, tuple)) else out
        return send_file(res, mimetype="audio/wav", as_attachment=False)
    except Exception as e:
        if os.path.exists(tf.name): os.remove(tf.name)
        return str(e), 500

@app.route("/dub_text", methods=["POST"])
def dub_text():
    if not os.path.exists(VOICE_FILE): return "احفظ البصمة أولاً", 400
    t = request.args.get("text", "مرحبا")
    hf_token = os.environ.get("HF_TOKEN")
    last_err = ""
    for sp in ["coqui/xtts", "mrfakename/E2-F5-TTS", "tonyassi/voice-clone"]:
        try:
            tc = Client(sp, token=hf_token)
            if "xtts" in sp: out = tc.predict(t, "ar", handle_file(VOICE_FILE), None, False, True, False, True, api_name="/predict")
            elif "E2-F5" in sp: out = tc.predict(handle_file(VOICE_FILE), "", t, False, True, 0.15, 32, 1.0, api_name="/basic_tts")
            else: out = tc.predict(t, handle_file(VOICE_FILE), api_name="/predict")
            res = out if isinstance(out, (list, tuple)) else out
            return send_file(res, mimetype="audio/wav", as_attachment=False)
        except Exception as e:
            last_err = str(e); continue
    return f"المحركات مشغولة حالياً: {last_err}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
            
      
    
    
  
