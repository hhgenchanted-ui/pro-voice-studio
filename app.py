
      import os
import tempfile
from flask import Flask, request, send_file, jsonify, render_template_string
from gradio_client import Client, handle_file

app = Flask(__name__)
CLONED_VOICE_FILE = "target_cloned_voice.wav"

HTML_PART_1 = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>استوديو الدبلجة واستنساخ الصوت</title>
<style>
body{font-family:'Segoe UI',Tahoma,sans-serif;background:#0b1120;color:#f8fafc;padding:14px;margin:0}
.card{background:#1e293b;border-radius:16px;padding:18px;max-width:500px;margin:0 auto 14px;border:1px solid #334155;box-shadow:0 4px 12px rgba(0,0,0,0.4)}
h1{text-align:center;font-size:21px;color:#38bdf8;margin:5px 0}
.sub{text-align:center;font-size:12px;color:#94a3b8;margin-bottom:14px}
h2{font-size:15px;color:#e2e8f0;border-bottom:1px solid #334155;padding-bottom:8px;margin-top:0}
input,select,textarea,button{width:100%;box-sizing:border-box;margin-top:8px;padding:12px;border-radius:10px;border:none;font-size:14px}
input[type="file"],select,textarea{background:#0f172a;color:#fff;border:1px solid #475569}
button{background:linear-gradient(135deg,#0284c7,#2563eb);color:#fff;font-weight:bold;cursor:pointer}
.rec{background:linear-gradient(135deg,#dc2626,#991b1b)}.stop{background:#475569}.mic-btn{background:#059669;margin-bottom:10px}
.st{text-align:center;font-size:13px;margin-top:10px;color:#38bdf8;word-wrap:break-word}
audio{width:100%;margin-top:10px;border-radius:8px}
.row{display:flex;gap:8px}
.dl{display:none;text-align:center;background:#10b981;color:#fff;padding:10px;border-radius:8px;text-decoration:none;margin-top:8px;font-weight:bold;font-size:14px}
</style>
</head>
<body>
<h1>🎙️ استوديو استنساخ الصوت الاحترافي</h1>
<div class="sub">جودة استوديو • دبلجة بالمشاعر • يعمل 24 ساعة</div>
<div class="card">
<button class="mic-btn" onclick="askMic()">🎤 تفعيل إذن المايكروفون للتطبيق</button>
<div id="micSt" class="st"></div>
</div>
<div class="card">
<h2>1️⃣ بصمة الصوت المراد استنساخها (حتى 5 دقائق)</h2>
<input type="file" id="mf" accept="audio/*">
<button onclick="upF()">رفع وحفظ الملف المختار 💾</button>
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
<label style="font-size:12px;color:#94a3b8;display:block;margin-top:8px">طبقة الصوت (عميق -12 إلى حاد +12): <span id="pv">0</span></label>
<input type="range" id="pt" min="-12" max="12" value="0" oninput="document.getElementById('pv').innerText=this.value">
<button onclick="dA()">✨ استنساخ الصوت بنفس مشاعري</button>
<div id="as" class="st"></div>
<audio id="aa" controls></audio>
<a id="dlA" class="dl" download="dubbed_acting.wav">⬇️ حفظ الصوت على الهاتف</a>
</div>
<div class="card">
<h2>3️⃣ تحويل النص إلى صوت مستنسخ</h2>
<textarea id="ti" rows="3" placeholder="اكتب الجملة العربية أو الإنجليزية هنا..."></textarea>
<select id="es">
<option value="طبيعي">نبرة طبيعية</option>
<option value="فرح">😄 فرح وحماس</option>
<option value="حزن">😢 حزن وتأثر</option>
<option value="غضب">😠 غضب وحدة</option>
<option value="همس">🤫 همس وهدوء</option>
</select>
<button onclick="dT()">🗣️ انطق النص بالصوت المستنسخ</button>
<div id="ts" class="st"></div>
<audio id="ta" controls></audio>
<a id="dlT" class="dl" download="cloned_speech.wav">⬇️ حفظ الصوت على الهاتف</a>
</div>"""
HTML_PART_2 = """<script>
let mRec,mCh=[],aRec,aCh=[],rBlob=null;
async function askMic(){
  try{
    let s=await navigator.mediaDevices.getUserMedia({audio:true});
    s.getTracks().forEach(t=>t.stop());
    document.getElementById('micSt').innerText='✅ المايكروفون مفعل وجاهز للتسجيل!';
  }catch(e){
    document.getElementById('micSt').innerText='⚠️ افتح إعدادات المتصفح واسمح بالمايكروفون';
  }
}
async function upF(){
  let f=document.getElementById('mf').files;
  if(!f.length)return alert('اختر ملف الصوت أولاً');
  document.getElementById('ms').innerText='⏳ جاري رفع وحفظ البصمة...';
  let r=await fetch('/set_voice',{method:'POST',body:f[0]});
  let d=await r.json();
  document.getElementById('ms').innerText='✅ '+d.message;
}
async function sM(){
  try{
    let st=await navigator.mediaDevices.getUserMedia({audio:true});
    mRec=new MediaRecorder(st);mCh=[];
    mRec.ondataavailable=e=>mCh.push(e.data);
    mRec.onstop=async()=>{
      let b=new Blob(mCh,{type:'audio/webm'});
      document.getElementById('ms').innerText='⏳ جاري حفظ البصمة...';
      let r=await fetch('/set_voice',{method:'POST',body:b});
      let d=await r.json();
      document.getElementById('ms').innerText='✅ '+d.message;
    };
    mRec.start();document.getElementById('ms').innerText='🔴 جاري تسجيل البصمة... تحدث بوضوح';
  }catch(e){askMic();}
}
function eM(){if(mRec&&mRec.state!=='inactive')mRec.stop();}
async function sR(){
  try{
    let st=await navigator.mediaDevices.getUserMedia({audio:true});
    aRec=new MediaRecorder(st);aCh=[];
    aRec.ondataavailable=e=>aCh.push(e.data);
    aRec.onstop=()=>{rBlob=new Blob(aCh,{type:'audio/webm'});document.getElementById('as').innerText='🎤 تم التسجيل، اضغط زر الاستنساخ';};
    aRec.start();document.getElementById('as').innerText='🔴 جاري تسجيل مشاعرك...';
  }catch(e){askMic();}
}
function eR(){if(aRec&&aRec.state!=='inactive')aRec.stop();}
async function dA(){
  if(!rBlob)return alert('سجل أداءك التمثيلي أولاً');
  document.getElementById('as').innerText='⏳ جاري المعالجة في الاستوديو (20-30 ثانية)...';
  let p=document.getElementById('pt').value;
  let r=await fetch('/dub_acting?pitch='+p,{method:'POST',body:rBlob});
  if(!r.ok)return document.getElementById('as').innerText='❌ '+await r.text();
  let b=await r.blob(),u=URL.createObjectURL(b);
  document.getElementById('aa').src=u;document.getElementById('aa').play();
  let dl=document.getElementById('dlA');dl.href=u;dl.style.display='block';
  document.getElementById('as').innerText='✅ تم الإنتاج بنجاح!';
}
async function dT(){
  let t=document.getElementById('ti').value,em=document.getElementById('es').value;
  if(!t)return alert('اكتب النص أولاً');
  document.getElementById('ts').innerText='⏳ جاري توليد الصوت المستنسخ (20-30 ثانية)...';
  let r=await fetch('/dub_text?text='+encodeURIComponent(t)+'&emotion='+encodeURIComponent(em),{method:'POST'});
  if(!r.ok)return document.getElementById('ts').innerText='❌ '+await r.text();
  let b=await r.blob(),u=URL.createObjectURL(b);
  document.getElementById('ta').src=u;document.getElementById('ta').play();
  let dl=document.getElementById('dlT');dl.href=u;dl.style.display='block';
  document.getElementById('ts').innerText='✅ تم التوليد بنجاح!';
}
</script></body></html>"""

@app.route("/")
def home():
    return render_template_string(HTML_PART_1 + HTML_PART_2)

@app.route("/set_voice", methods=["POST"])
def set_voice():
    data = request.get_data()
    if not data or len(data) < 100:
        return jsonify({"message": "الملف فارغ"}), 400
    with open(CLONED_VOICE_FILE, "wb") as f:
        f.write(data)
    return jsonify({"message": f"تم حفظ البصمة الصوتية بنجاح ({len(data)//1024} KB)"})

@app.route("/dub_acting", methods=["POST"])
def dub_acting():
    if not os.path.exists(CLONED_VOICE_FILE):
        return "يرجى حفظ البصمة الصوتية في القسم 1 أولاً", 400
    p = int(request.args.get("pitch", 0))
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    tf.write(request.get_data())
    tf.close()
    try:
        vc = Client("Plachta/Seed-VC")
        out = vc.predict(
            handle_file(tf.name),
            handle_file(CLONED_VOICE_FILE),
            25,
            1.0,
            0.7,
            True,
            False,
            p,
            api_name="/predict"
        )
        os.remove(tf.name)
        res = out[0] if isinstance(out, (list, tuple)) else out
        return send_file(res, mimetype="audio/wav")
    except Exception as e:
        if os.path.exists(tf.name):
            os.remove(tf.name)
        return f"حدث خطأ في الدبلجة: {str(e)}", 500

@app.route("/dub_text", methods=["POST"])
def dub_text():
    if not os.path.exists(CLONED_VOICE_FILE):
        return "يرجى حفظ البصمة الصوتية في القسم 1 أولاً", 400
    t = request.args.get("text", "مرحباً")
    em = request.args.get("emotion", "طبيعي")
    spaces = [
        "tonyassi/voice-clone",
        "coqui/xtts",
        "mrfakename/E2-F5-TTS"
    ]
    last_err = ""
    for sp in spaces:
        try:
            tc = Client(sp)
            if "tonyassi" in sp:
                out = tc.predict(t, handle_file(CLONED_VOICE_FILE), api_name="/predict")
            elif "xtts" in sp:
                out = tc.predict(t, "ar", handle_file(CLONED_VOICE_FILE), None, False, True, False, True, api_name="/predict")
            else:
                out = tc.predict(handle_file(CLONED_VOICE_FILE), "", t, False, True, 0.15, 32, 1.0, api_name="/basic_tts")
            res = out[0] if isinstance(out, (list, tuple)) else out
            return send_file(res, mimetype="audio/wav")
        except Exception as e:
            last_err = str(e)
            continue
    return f"المحركات مشغولة حالياً، حاول بعد قليل: {last_err}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
      
    
    
  
