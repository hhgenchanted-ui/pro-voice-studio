PAGE = '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pro Voice Studio</title>
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: sans-serif; padding: 16px; display: flex; flex-direction: column; align-items: center; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 18px; width: 100%; max-width: 460px; margin-bottom: 16px; box-sizing: border-box; }
        h3 { margin-top: 0; font-size: 16px; }
        .btn { width: 100%; padding: 12px; border: none; border-radius: 10px; font-size: 15px; font-weight: bold; cursor: pointer; margin-top: 10px; color: white; text-decoration: none; display: block; text-align: center; box-sizing: border-box; }
        .btn-blue { background: #0284c7; }
        .btn-green { background: #16a34a; }
        .btn-red { background: #dc2626; }
        .btn-gray { background: #475569; }
        .row { display: flex; gap: 10px; margin-top: 10px; }
        .row .btn { margin-top: 0; }
        input[type="file"] { width: 100%; padding: 10px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: #cbd5e1; box-sizing: border-box; }
        .status { text-align: center; margin-top: 10px; font-size: 14px; color: #38bdf8; word-break: break-word; }
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
        <audio id="resultAudio" controls preload="metadata"></audio>
        <a id="dlBtn" class="btn btn-green" href="/get_audio" download="cloned_voice.mp3" style="display:none;">⬇️ تحميل الصوت المستنسخ</a>
    </div>
    <script>
        let mediaRecorder, actingBlob = null;
        let audioChunks = new Array();

        async function startRec(type) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioChunks = new Array();
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
                mediaRecorder.onstop = async () => {
                    stream.getTracks().forEach(t => t.stop());
                    const blob = new Blob(audioChunks, { type: 'audio/webm' });
                    if (type === 'vp') await sendVoiceprintBlob(blob);
                    else {
                        actingBlob = blob;
                        document.getElementById('actStatus').innerHTML = `<span class="success">✅ تم تسجيل الأداء (${Math.round(blob.size/1024)} KB)</span>`;
                    }
                };
                mediaRecorder.start();
                document.getElementById(type === 'vp' ? 'recVpBtn' : 'recActBtn').disabled = true;
                document.getElementById(type === 'vp' ? 'stopVpBtn' : 'stopActBtn').disabled = false;
                document.getElementById(type === 'vp' ? 'vpStatus' : 'actStatus').innerText = "🎙️ جاري التسجيل...";
            } catch (err) { alert("يرجى السماح بالميكروفون"); }
        }

        function stopRec(type) {
            if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
            document.getElementById(type === 'vp' ? 'recVpBtn' : 'recActBtn').disabled = false;
            document.getElementById(type === 'vp' ? 'stopVpBtn' : 'stopActBtn').disabled = true;
        }

        async function uploadVoiceprint() {
            const f = document.getElementById('voiceFile');
            if (!f.files.length) return alert("اختر ملفاً أولاً");
            await sendVoiceprintBlob(f.files.item(0));
        }

        async function sendVoiceprintBlob(fileOrBlob) {
            const status = document.getElementById('vpStatus');
            status.innerText = "⏳ جاري حفظ البصمة...";
            const fd = new FormData();
            fd.append("file", fileOrBlob, "voiceprint.webm");
            try {
                const res = await fetch("/save_voiceprint", { method: "POST", body: fd });
                const data = await res.json();
                status.innerHTML = res.ok ? `<span class="success">✅ تم حفظ البصمة (${data.size_kb} KB)</span>` : `<span class="error">❌ ${data.error}</span>`;
            } catch (e) { status.innerHTML = `<span class="error">❌ خطأ اتصال</span>`; }
        }

        async function cloneVoiceToVoice() {
            if (!actingBlob) return alert("سجّل صوتك التمثيلي أولاً");
            const status = document.getElementById('cloneStatus');
            const dlBtn = document.getElementById('dlBtn');
            dlBtn.style.display = "none";
            status.innerText = "⏳ جاري استنساخ الصوت ونقل المشاعر...";
            const fd = new FormData();
            fd.append("acting_audio", actingBlob, "acting.webm");
            try {
                const res = await fetch("/clone_voice", { method: "POST", body: fd });
                const data = await res.json();
                if (!res.ok) {
                    status.innerHTML = `<span class="error">❌ ${data.error}</span>`;
                    return;
                }
                const audioUrl = "/get_audio?t=" + new Date().getTime();
                const player = document.getElementById('resultAudio');
                player.src = audioUrl;
                player.load();
                player.play();
                dlBtn.href = audioUrl;
                dlBtn.style.display = "block";
                status.innerHTML = `<span class="success">✅ تم استنساخ الصوت بنجاح (${data.size_kb} KB)!</span>`;
            } catch (e) { status.innerHTML = `<span class="error">❌ خطأ: ${e.message}</span>`; }
        }
    </script>
</body>
</html>'''

