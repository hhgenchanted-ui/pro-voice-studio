<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pro Voice Studio - استنساخ الصوت بالمشاعر</title>
    <style>
        body {
            background-color: #0f172a;
            color: #f8fafc;
            font-family: system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 14px;
            padding: 18px;
            width: 100%;
            max-width: 460px;
            margin-bottom: 16px;
            box-sizing: border-box;
        }
        h3 { margin-top: 0; font-size: 16px; color: #e2e8f0; }
        .btn {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 10px;
            color: white;
            transition: 0.2s;
        }
        .btn-blue { background-color: #0284c7; }
        .btn-blue:hover { background-color: #0369a1; }
        .btn-red { background-color: #dc2626; }
        .btn-gray { background-color: #475569; }
        .row { display: flex; gap: 10px; margin-top: 10px; }
        .row .btn { margin-top: 0; }
        input[type="file"] {
            width: 100%;
            padding: 10px;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            color: #cbd5e1;
            box-sizing: border-box;
        }
        .status {
            text-align: center;
            margin-top: 10px;
            font-size: 14px;
            color: #38bdf8;
        }
        .error { color: #f87171; }
        .success { color: #4ade80; }
        audio { width: 100%; margin-top: 12px; border-radius: 8px; }
    </style>
</head>
<body>

    <!-- القسم 1: البصمة الصوتية -->
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

    <!-- القسم 2: الدبلجة واستنساخ الصوت إلى صوت -->
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

    <script>
        let mediaRecorder;
        let audioChunks = [];
        let actingBlob = null;

        async function startRec(type) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioChunks = [];
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
                        document.getElementById('actStatus').innerHTML = `<span class="success">✅ تم تسجيل الأداء التمثيلي (${kb} KB)</span>`;
                    }
                };

                mediaRecorder.start();
                if (type === 'vp') {
                    document.getElementById('recVpBtn').disabled = true;
                    document.getElementById('stopVpBtn').disabled = false;
                    document.getElementById('vpStatus').innerText = "🎙️ جاري تسجيل البصمة (تحدث 10 ثوانٍ)...";
                } else {
                    document.getElementById('recActBtn').disabled = true;
                    document.getElementById('stopActBtn').disabled = false;
                    document.getElementById('actStatus').innerText = "🎭 جاري تسجيل أدائك التمثيلي...";
                }
            } catch (err) {
                alert("يرجى السماح بالوصول للميكروفون من المتصفح");
            }
        }

        function stopRec(type) {
            if (mediaRecorder && mediaRecorder.state !== "inactive") {
                mediaRecorder.stop();
            }
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
            if (!fileInput.files.length) return alert("اختر ملف صوت أو فيديو أولاً");
            await sendVoiceprintBlob(fileInput.files[0]);
        }

        async function sendVoiceprintBlob(fileOrBlob) {
            const status = document.getElementById('vpStatus');
            status.innerText = "⏳ جاري ضغط وحفظ البصمة...";
            const formData = new FormData();
            formData.append("file", fileOrBlob, "voiceprint.webm");

            try {
                const res = await fetch("/save_voiceprint", { method: "POST", body: formData });
                const data = await res.json();
                if (res.ok) {
                    status.innerHTML = `<span class="success">✅ تم حفظ البصمة (${data.size_kb} KB)</span>`;
                } else {
                    status.innerHTML = `<span class="error">❌ ${data.error}</span>`;
                }
            } catch (e) {
                status.innerHTML = `<span class="error">❌ فشل الاتصال بالسيرفر</span>`;
            }
        }

        async function cloneVoiceToVoice() {
            if (!actingBlob) return alert("سجّل صوتك التمثيلي أولاً بالضغط على (ابدأ التمثيل)");
            const status = document.getElementById('cloneStatus');
            status.innerText = "⏳ جاري استنساخ الصوت ونقل المشاعر (قد يستغرق 15-30 ثانية)...";

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
                const audioUrl = URL.createObjectURL(audioBlob);
                const player = document.getElementById('resultAudio');
                player.src = audioUrl;
                player.play();
                status.innerHTML = `<span class="success">✅ تم استنساخ الصوت بنجاح!</span>`;
            } catch (e) {
                status.innerHTML = `<span class="error">❌ حدث خطأ في الاتصال: ${e.message}</span>`;
            }
        }
    </script>
</body>
</html>

            
      
    
    
  
