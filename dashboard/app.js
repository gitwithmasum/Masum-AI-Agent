const state = { agents: [], status: null };

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

function toast(message, isError=false){
  const el=$("#toast");
  el.textContent=message;
  el.className="toast show"+(isError?" error":"");
  clearTimeout(window.__toastTimer);
  window.__toastTimer=setTimeout(()=>{el.className="toast";},2600);
}

async function api(url, options={}){
  const opts={...options};
  opts.headers={"Content-Type":"application/json",...(options.headers||{})};
  const res=await fetch(url,opts);
  let data={};
  try{data=await res.json();}catch{}
  if(!res.ok) throw new Error(data.detail||("Request failed: "+res.status));
  return data;
}

function setView(id){
  $$(".panel-view").forEach(v=>v.classList.toggle("active",v.id===id));
  $$(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.target===id));
  window.scrollTo({top:0,behavior:"smooth"});
}

$$(".nav-item").forEach(btn=>btn.addEventListener("click",()=>setView(btn.dataset.target)));
$$("[data-open-chat]").forEach(btn=>btn.addEventListener("click",()=>setView("chat")));
$$("[data-target-jump]").forEach(btn=>btn.addEventListener("click",()=>setView(btn.dataset.targetJump)));

function updateClock(){
  const now=new Date();
  $("#clock").textContent=now.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"});
}
setInterval(updateClock,1000);updateClock();

async function loadStatus(){
  try{
    const d=await api("/api/status");
    state.status=d;
    $("#nodeState").textContent=d.ollama.online?"ONLINE":"OLLAMA OFF";
    $("#nodeDot").classList.toggle("online",d.ollama.online);
    $("#routeChip").textContent=d.auto_route?"AUTO ROUTE ON":"AUTO ROUTE OFF";
    const cards=$$("#statusGrid .status-card strong");
    cards[0].textContent=d.ollama.online?"ONLINE":"OFFLINE";
    cards[0].className=d.ollama.online?"good":"bad";
    cards[1].textContent=d.gmail.authorized?"AUTHORIZED":"SETUP";
    cards[1].className=d.gmail.authorized?"good":"";
    cards[2].textContent=d.automation.enabled+"/"+d.automation.total;
    cards[2].className=d.automation.enabled?"good":"";
    cards[3].textContent=String(d.reports);
    cards[3].className=d.reports?"good":"";
  }catch(e){
    $("#nodeState").textContent="ERROR";toast(e.message,true);
  }
}

function renderAgents(){
  const icon={general:"◎",research:"⌬",developer:"</>",gmail:"✉",data:"▦"};
  const mini=state.agents.map(a=>`
    <div class="mini-agent">
      <strong>${a.id}</strong>
      <small>${a.description}</small>
    </div>`).join("");
  $("#agentMiniList").innerHTML=mini;
  $("#chatAgentList").innerHTML=mini;
  $("#agentGrid").innerHTML=state.agents.map(a=>`
    <article class="agent-card glass">
      <div class="icon">${icon[a.id]||"⬡"}</div>
      <h3>${a.id}</h3>
      <p>${a.description}</p>
      <button class="secondary" data-agent-chat="${a.id}">OPEN AGENT</button>
    </article>`).join("");
  $$("[data-agent-chat]").forEach(btn=>btn.addEventListener("click",()=>{
    $("#agentSelect").value=btn.dataset.agentChat;setView("chat");$("#chatInput").focus();
  }));
}

async function loadAgents(){
  try{
    const d=await api("/api/agents");state.agents=d.agents||[];renderAgents();
  }catch(e){toast(e.message,true);}
}

function addMessage(role,text,label){
  const wrap=document.createElement("div");
  wrap.className="message "+(role==="user"?"user-message":"agent-message");
  const av=document.createElement("div");av.className="avatar";av.textContent=role==="user"?"MB":"AI";
  const body=document.createElement("div");
  const small=document.createElement("small");small.textContent=label||role.toUpperCase();
  const p=document.createElement("p");p.textContent=text;
  body.append(small,p);wrap.append(av,body);$("#messages").appendChild(wrap);
  $("#messages").scrollTop=$("#messages").scrollHeight;
}

$("#chatForm").addEventListener("submit",async(e)=>{
  e.preventDefault();
  const input=$("#chatInput"), message=input.value.trim();
  if(!message)return;
  const agent=$("#agentSelect").value, teamReview=$("#teamReview").checked;
  addMessage("user",message,"MASUM");input.value="";$("#sendBtn").disabled=true;$("#sendBtn").textContent="THINKING…";
  const pending=document.createElement("div");pending.className="message agent-message";pending.id="pendingMsg";
  pending.innerHTML='<div class="avatar">AI</div><div><small>PROCESSING</small><p>Routing request through the local agent network…</p></div>';
  $("#messages").appendChild(pending);$("#messages").scrollTop=$("#messages").scrollHeight;
  try{
    const d=await api("/api/chat",{method:"POST",body:JSON.stringify({message,agent,team_review:teamReview})});
    pending.remove();addMessage("agent",d.answer,(d.agents||[]).join(" + ")+" // "+d.mode);
  }catch(err){
    pending.remove();addMessage("agent","Error: "+err.message,"SYSTEM");toast(err.message,true);
  }finally{$("#sendBtn").disabled=false;$("#sendBtn").textContent="SEND";}
});
$("#chatInput").addEventListener("keydown",(e)=>{
  if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();$("#chatForm").requestSubmit();}
});

$("#gmailStatusBtn").addEventListener("click",async()=>{
  $("#quickOutput").textContent="Checking Gmail…";
  try{const d=await api("/api/gmail/status");$("#quickOutput").textContent=d.text;}catch(e){$("#quickOutput").textContent=e.message;}
});
$("#githubSummaryBtn").addEventListener("click",async()=>{
  $("#quickOutput").textContent="Reading GitHub repository…";
  try{const d=await api("/api/github/summary");$("#quickOutput").textContent=d.text;}catch(e){$("#quickOutput").textContent=e.message;}
});

function taskElement(t){
  const el=document.createElement("div");el.className="task";
  const top=document.createElement("div");top.className="task-top";
  const info=document.createElement("div");
  const strong=document.createElement("strong");strong.textContent=t.action;
  const meta=document.createElement("small");meta.textContent=`${t.id} • ${t.enabled?"ON":"OFF"} • ${t.schedule_type} ${t.schedule_value} • next: ${t.next_run||"—"}`;
  info.append(strong,meta);top.append(info);el.append(top);
  const actions=document.createElement("div");actions.className="task-actions";
  const defs=[["RUN","run"],[t.enabled?"PAUSE":"ENABLE",t.enabled?"disable":"enable"],["DELETE","delete"]];
  defs.forEach(([label,op])=>{
    const b=document.createElement("button");b.textContent=label;if(op==="delete")b.classList.add("danger");
    b.addEventListener("click",async()=>{
      b.disabled=true;
      try{
        if(op==="delete") await api("/api/automations/"+t.id,{method:"DELETE"});
        else await api("/api/automations/"+t.id+"/"+op,{method:"POST"});
        toast(op==="run"?"Automation executed.":"Automation updated.");await loadAutomations();await loadStatus();
      }catch(e){toast(e.message,true);}finally{b.disabled=false;}
    });
    actions.append(b);
  });
  el.append(actions);return el;
}

async function loadAutomations(){
  try{
    const d=await api("/api/automations"), list=$("#automationList");list.innerHTML="";
    if(!(d.tasks||[]).length){list.textContent="No automation tasks configured.";return;}
    d.tasks.forEach(t=>list.appendChild(taskElement(t)));
  }catch(e){toast(e.message,true);}
}
$("#refreshAutomations").addEventListener("click",loadAutomations);

$("#scheduleType").addEventListener("change",()=>{
  const type=$("#scheduleType").value,input=$("#scheduleValue"),hint=$("#scheduleHint");
  if(type==="daily"){input.value="09:00";input.placeholder="09:00";hint.textContent="Daily uses 24-hour HH:MM.";}
  else if(type==="interval"){input.value="60";input.placeholder="60";hint.textContent="Interval is in minutes.";}
  else{input.value="";input.placeholder="2026-10-10 18:30";hint.textContent="One time uses YYYY-MM-DD HH:MM in your computer's local timezone.";}
});
$("#automationForm").addEventListener("submit",async(e)=>{
  e.preventDefault();
  const payload={schedule_type:$("#scheduleType").value,schedule_value:$("#scheduleValue").value.trim(),action:$("#automationAction").value.trim()};
  if(!payload.action)return toast("Add an automation action.",true);
  try{
    await api("/api/automations",{method:"POST",body:JSON.stringify(payload)});
    $("#automationAction").value="";toast("Automation created.");await loadAutomations();await loadStatus();
  }catch(err){toast(err.message,true);}
});

async function loadReports(){
  try{
    const d=await api("/api/reports"),list=$("#reportList");list.innerHTML="";
    if(!(d.reports||[]).length){list.textContent="No research reports saved yet.";return;}
    d.reports.forEach(r=>{
      const el=document.createElement("div");el.className="report-item";
      const info=document.createElement("div"),strong=document.createElement("strong"),small=document.createElement("small");
      strong.textContent=r.name;small.textContent=new Date(r.modified).toLocaleString()+" • "+Math.round(r.size/1024)+" KB";
      info.append(strong,small);el.append(info);el.addEventListener("click",()=>openReport(r.name));list.append(el);
    });
  }catch(e){toast(e.message,true);}
}
async function openReport(name){
  $("#reportTitle").textContent=name;$("#reportContent").textContent="Loading…";
  try{const d=await api("/api/reports/"+encodeURIComponent(name));$("#reportContent").textContent=d.content;}
  catch(e){$("#reportContent").textContent=e.message;toast(e.message,true);}
}
$("#refreshReports").addEventListener("click",loadReports);

Promise.all([loadStatus(),loadAgents(),loadAutomations(),loadReports()]);
setInterval(loadStatus,30000);

// v4.4 Hands-Free Voice Command Center — Cirilla / Geralt
(function(){
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const voiceBtn = document.querySelector("#voiceBtn");
  const voiceMiniBtn = document.querySelector("#voiceMiniBtn");
  const voiceState = document.querySelector("#voiceState");
  const voiceHint = document.querySelector("#voiceHint");
  const sttBadge = document.querySelector("#sttBadge");
  const wakeBadge = document.querySelector("#wakeBadge");
  const wakeMode = document.querySelector("#wakeMode");
  const wakePersonaLabel = document.querySelector("#wakePersonaLabel");
  const input = document.querySelector("#chatInput");
  const form = document.querySelector("#chatForm");
  const lang = document.querySelector("#voiceLanguage");
  const engine = document.querySelector("#voiceEngine");
  const persona = document.querySelector("#voicePersona");
  const autoSend = document.querySelector("#voiceAutoSend");
  const speakReplies = document.querySelector("#speakReplies");
  const stopBtn = document.querySelector("#stopSpeechBtn");
  if(!voiceBtn || !voiceMiniBtn || !input || !form || !persona) return;

  const WAKE_CHUNK_MS = 3500;
  const COMMAND_RECORD_MS = 7000;

  const PERSONAS = {
    cirilla: {
      name: "Cirilla",
      gender: "female",
      wakePatterns: [
        /hey\s+cirilla[\s,.:;-]*/i,
        /cirilla[\s,.:;-]*/i,
        /hey\s+sirilla[\s,.:;-]*/i,
        /sirilla[\s,.:;-]*/i,
        /cirila[\s,.:;-]*/i,
        /হেই\s+সিরিলা[\s,.:;-]*/i,
        /সিরিলা[\s,.:;-]*/i
      ],
      preferredVoices: [
        "zira","aria","jenny","susan","samantha",
        "victoria","hazel","nabanita","female"
      ],
      pitch: 1.08,
      rate: 0.98
    },
    geralt: {
      name: "Geralt",
      gender: "male",
      wakePatterns: [
        /hey\s+geralt[\s,.:;-]*/i,
        /geralt[\s,.:;-]*/i,
        /hey\s+gerald[\s,.:;-]*/i,
        /gerald[\s,.:;-]*/i,
        /হেই\s+গেরাল্ট[\s,.:;-]*/i,
        /গেরাল্ট[\s,.:;-]*/i
      ],
      preferredVoices: [
        "david","mark","guy","george","daniel",
        "ryan","male"
      ],
      pitch: 0.82,
      rate: 0.94
    }
  };

  let recognition = null;
  let browserListening = false;
  let recorder = null;
  let stream = null;
  let chunks = [];
  let localRecording = false;
  let lastAgentText = "";
  let wakeRecorder = null;
  let wakeStream = null;
  let wakeChunks = [];
  let wakeTimer = null;
  let wakeListening = false;
  let wakePausedForCommand = false;
  let commandStopTimer = null;

  function profile(){
    return PERSONAS[persona.value] || PERSONAS.cirilla;
  }

  function personaName(){
    return profile().name;
  }

  function normalizedCommand(text){
    return String(text || "")
      .toLowerCase()
      .replace(/[.,!?;:]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function commandFeedback(message){
    toast(message);
    setState("VOICE COMMAND","ready",message);
    if(speakReplies.checked){
      speak(message);
    }else{
      resumeWakeAfterResponse();
    }
  }

  function executeVoiceCommand(text){
    const cmd = normalizedCommand(text);

    if(/^(switch to )?(geralt|male)( mode| voice)?$/.test(cmd) || /^(গেরাল্ট|মেল)( মোড| ভয়েস| ভয়েস)?$/.test(cmd)){
      persona.value = "geralt";
      savePrefs();
      refreshPersonaUi();
      commandFeedback("Geralt mode active.");
      return true;
    }

    if(/^(switch to )?(cirilla|female)( mode| voice)?$/.test(cmd) || /^(সিরিলা|ফিমেল)( মোড| ভয়েস| ভয়েস)?$/.test(cmd)){
      persona.value = "cirilla";
      savePrefs();
      refreshPersonaUi();
      commandFeedback("Cirilla mode active.");
      return true;
    }

    const views = [
      {id:"overview", patterns:[/^open overview$/, /^show overview$/, /^open dashboard$/, /^go home$/, /^ওভারভিউ খোলো$/, /^ড্যাশবোর্ড খোলো$/]},
      {id:"chat", patterns:[/^open chat$/, /^open neural chat$/, /^show chat$/, /^চ্যাট খোলো$/, /^নিউরাল চ্যাট খোলো$/]},
      {id:"agents", patterns:[/^open agents$/, /^show agents$/, /^agents$/, /^এজেন্ট খোলো$/, /^এজেন্টস খোলো$/]},
      {id:"automation", patterns:[/^open automation$/, /^open automation center$/, /^show automation$/, /^অটোমেশন খোলো$/, /^অটোমেশন সেন্টার খোলো$/]},
      {id:"research", patterns:[/^open research$/, /^open research vault$/, /^show research$/, /^রিসার্চ খোলো$/, /^রিসার্চ ভল্ট খোলো$/]}
    ];

    for(const view of views){
      if(view.patterns.some(function(pattern){ return pattern.test(cmd); })){
        setView(view.id);
        commandFeedback("Opened " + view.id + ".");
        return true;
      }
    }

    if(/^(wake mode on|turn on wake mode|start wake mode)$/.test(cmd) || /^(ওয়েক মোড অন|ওয়েক মোড অন|ওয়েক মোড চালু|ওয়েক মোড চালু)$/.test(cmd)){
      wakeMode.checked = true;
      engine.value = "local";
      savePrefs();
      commandFeedback("Wake mode on for " + personaName() + ".");
      return true;
    }

    if(/^(wake mode off|turn off wake mode|stop wake mode|stop listening)$/.test(cmd) || /^(ওয়েক মোড অফ|ওয়েক মোড অফ|ওয়েক মোড বন্ধ|ওয়েক মোড বন্ধ|শোনা বন্ধ)$/.test(cmd)){
      wakeMode.checked = false;
      wakePausedForCommand = false;
      stopWakeListener();
      savePrefs();
      setWakeBadge("off",personaName().toUpperCase() + " OFF");
      commandFeedback("Wake mode off.");
      return true;
    }

    if(/^(speak replies on|voice replies on|turn on voice replies)$/.test(cmd)){
      speakReplies.checked = true;
      savePrefs();
      commandFeedback("Spoken replies on.");
      return true;
    }

    if(/^(speak replies off|voice replies off|turn off voice replies)$/.test(cmd)){
      speakReplies.checked = false;
      savePrefs();
      toast("Spoken replies off.");
      setState("VOICE COMMAND","ready","Spoken replies off.");
      resumeWakeAfterResponse();
      return true;
    }

    if(/^(auto send on|turn on auto send)$/.test(cmd)){
      autoSend.checked = true;
      savePrefs();
      commandFeedback("Auto-send on.");
      return true;
    }

    if(/^(auto send off|turn off auto send)$/.test(cmd)){
      autoSend.checked = false;
      savePrefs();
      commandFeedback("Auto-send off.");
      return true;
    }

    if(/^(gmail status|check gmail status)$/.test(cmd)){
      setView("overview");
      document.querySelector("#gmailStatusBtn").click();
      commandFeedback("Checking Gmail status.");
      return true;
    }

    if(/^(github summary|check github|check github summary)$/.test(cmd)){
      setView("overview");
      document.querySelector("#githubSummaryBtn").click();
      commandFeedback("Checking GitHub summary.");
      return true;
    }

    if(/^(voice commands|show voice commands|voice help|help voice)$/.test(cmd)){
      const guide = document.querySelector("#voiceCommandGuide");
      if(guide){
        guide.open = true;
        setView("chat");
      }
      commandFeedback("Voice command guide opened.");
      return true;
    }

    return false;
  }

  function handleRecognizedCommand(text){
    if(!executeVoiceCommand(text)) return false;
    input.value = "";
    return true;
  }

  function setState(label, mode, hint){
    voiceState.textContent = label;
    voiceState.className = mode === "listening"
      ? "listening"
      : (mode === "error" ? "error" : "");
    voiceBtn.classList.toggle("listening", mode === "listening");
    voiceMiniBtn.classList.toggle("listening", mode === "listening");
    voiceBtn.classList.toggle("processing", mode === "processing");
    voiceMiniBtn.classList.toggle("processing", mode === "processing");
    if(hint) voiceHint.textContent = hint;
  }

  function setWakeBadge(mode, text){
    wakeBadge.textContent = text;
    wakeBadge.className = "wake-badge " + mode;
  }

  function refreshPersonaUi(){
    const name = personaName();
    wakePersonaLabel.textContent = name;
    if(!wakeMode.checked){
      setWakeBadge("off", name.toUpperCase() + " OFF");
    }
  }

  function savePrefs(){
    localStorage.setItem("masum.voice.lang", lang.value);
    localStorage.setItem("masum.voice.engine", engine.value);
    localStorage.setItem("masum.voice.persona", persona.value);
    localStorage.setItem("masum.voice.auto", autoSend.checked ? "1" : "0");
    localStorage.setItem("masum.voice.speak", speakReplies.checked ? "1" : "0");
    localStorage.setItem("masum.voice.wake", wakeMode.checked ? "1" : "0");
  }

  function loadPrefs(){
    const savedLang = localStorage.getItem("masum.voice.lang");
    const savedEngine = localStorage.getItem("masum.voice.engine");
    const savedPersona = localStorage.getItem("masum.voice.persona");

    if(savedLang) lang.value = savedLang;
    if(savedEngine) engine.value = savedEngine;
    if(savedPersona && PERSONAS[savedPersona]) persona.value = savedPersona;

    const savedAuto = localStorage.getItem("masum.voice.auto");
    autoSend.checked = savedAuto === null ? true : savedAuto === "1";
    speakReplies.checked = localStorage.getItem("masum.voice.speak") === "1";
    wakeMode.checked = localStorage.getItem("masum.voice.wake") === "1";
  }

  function selectedLanguage(){
    if(lang.value.indexOf("bn") === 0) return "bn";
    if(lang.value.indexOf("en") === 0) return "en";
    return "auto";
  }

  async function refreshSttStatus(){
    try{
      const response = await fetch("/api/stt/status");
      const data = await response.json();
      const online = Boolean(data.online);
      sttBadge.textContent = online ? "WHISPER ONLINE" : "WHISPER OFF";
      sttBadge.className = "stt-badge " + (online ? "online" : "offline");
      return online;
    }catch(error){
      sttBadge.textContent = "WHISPER OFF";
      sttBadge.className = "stt-badge offline";
      return false;
    }
  }

  function cleanSpeech(text){
    return String(text || "")
      .replace(/https?:\/\/\S+/g, " link ")
      .replace(/[#*_>~]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function scoreVoice(voice){
    const p = profile();
    const name = (voice.name || "").toLowerCase();
    const voiceLang = (voice.lang || "").toLowerCase();
    const target = lang.value.toLowerCase();
    const base = target.split("-")[0];
    let score = 0;

    if(voiceLang === target) score += 8;
    else if(voiceLang.startsWith(base)) score += 5;

    for(const keyword of p.preferredVoices){
      if(name.includes(keyword)) score += 4;
    }

    if(p.gender === "female" && /(female|woman|girl)/.test(name)) score += 3;
    if(p.gender === "male" && /(male|man|boy)/.test(name)) score += 3;

    if(voice.default) score += 1;
    return score;
  }

  function choosePersonaVoice(){
    if(!("speechSynthesis" in window)) return null;
    const voices = window.speechSynthesis.getVoices();
    if(!voices.length) return null;

    return voices
      .map(function(v){ return {voice:v, score:scoreVoice(v)}; })
      .sort(function(a,b){ return b.score - a.score; })[0].voice;
  }

  function speak(text){
    if(!("speechSynthesis" in window) || !speakReplies.checked){
      resumeWakeAfterResponse();
      return;
    }

    const clean = cleanSpeech(text);
    if(!clean){
      resumeWakeAfterResponse();
      return;
    }

    stopWakeListener();
    window.speechSynthesis.cancel();

    const p = profile();
    const utter = new SpeechSynthesisUtterance(clean.slice(0,1800));
    utter.lang = lang.value;
    utter.pitch = p.pitch;
    utter.rate = p.rate;

    const selectedVoice = choosePersonaVoice();
    if(selectedVoice) utter.voice = selectedVoice;

    setState(
      "SPEAKING",
      "ready",
      p.name + " is speaking" +
      (selectedVoice ? " — " + selectedVoice.name : "") + "."
    );

    utter.onend = function(){
      setState(
        "READY",
        "ready",
        "Say Hey " + p.name + ", or use MIC."
      );
      resumeWakeAfterResponse();
    };

    utter.onerror = function(){
      setState("TTS ERROR","error","Browser voice output failed.");
      resumeWakeAfterResponse();
    };

    window.speechSynthesis.speak(utter);
  }

  function stopTracks(){
    if(stream){
      stream.getTracks().forEach(function(track){ track.stop(); });
      stream = null;
    }
  }

  function stopWakeTracks(){
    if(wakeStream){
      wakeStream.getTracks().forEach(function(track){ track.stop(); });
      wakeStream = null;
    }
  }

  function preferredMimeType(){
    const types = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/ogg"
    ];
    for(const type of types){
      if(window.MediaRecorder && MediaRecorder.isTypeSupported(type)) return type;
    }
    return "";
  }

  async function transcribeLocal(blob){
    setState("TRANSCRIBING","processing","Local Whisper is decoding your speech…");
    try{
      const response = await fetch(
        "/api/stt/transcribe?language=" + encodeURIComponent(selectedLanguage()),
        {
          method:"POST",
          headers:{"Content-Type":blob.type || "audio/webm"},
          body:blob
        }
      );

      let data = {};
      try{ data = await response.json(); }catch(error){}
      if(!response.ok) throw new Error(data.detail || "Local transcription failed.");

      const text = String(data.text || "").trim();
      if(!text) throw new Error("Whisper did not detect clear speech.");

      if(handleRecognizedCommand(text)){
        return;
      }

      input.value = text;
      const detected = data.language ? ("Detected " + data.language) : "Local transcription";
      setState("HEARD","ready",detected + ": " + text);

      if(autoSend.checked){
        wakePausedForCommand = true;
        setTimeout(function(){ form.requestSubmit(); },180);
      }else{
        resumeWakeAfterResponse();
      }
    }catch(error){
      setState("STT ERROR","error",error.message || "Local Whisper failed.");
      resumeWakeAfterResponse();
    }
  }

  async function startLocal(autoStopMs=0){
    stopWakeListener();

    if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder){
      setState("UNSUPPORTED","error","MediaRecorder microphone capture is unavailable.");
      return;
    }

    const online = await refreshSttStatus();
    if(!online){
      setState("WHISPER OFF","error","Start local_stt_server.py, then try again.");
      return;
    }

    try{
      if("speechSynthesis" in window) window.speechSynthesis.cancel();
      stream = await navigator.mediaDevices.getUserMedia({
        audio:{
          echoCancellation:true,
          noiseSuppression:true,
          autoGainControl:true
        }
      });

      chunks = [];
      const mimeType = preferredMimeType();
      recorder = mimeType
        ? new MediaRecorder(stream,{mimeType:mimeType})
        : new MediaRecorder(stream);

      recorder.ondataavailable = function(event){
        if(event.data && event.data.size) chunks.push(event.data);
      };

      recorder.onstop = async function(){
        localRecording = false;
        clearTimeout(commandStopTimer);
        voiceBtn.classList.remove("listening");
        voiceMiniBtn.classList.remove("listening");

        const type = recorder && recorder.mimeType
          ? recorder.mimeType
          : "audio/webm";

        const blob = new Blob(chunks,{type:type});
        chunks = [];
        stopTracks();

        if(blob.size < 800){
          setState("NO AUDIO","error","Recording was too short. Try again.");
          resumeWakeAfterResponse();
          return;
        }

        await transcribeLocal(blob);
      };

      recorder.start(250);
      localRecording = true;

      setState(
        autoStopMs ? personaName().toUpperCase() + " AWAKE" : "LOCAL LISTENING",
        "listening",
        autoStopMs
          ? "I’m listening for your command…"
          : "Speak clearly, then click MIC again."
      );

      if(autoStopMs){
        commandStopTimer = setTimeout(function(){
          if(localRecording && recorder && recorder.state !== "inactive"){
            recorder.stop();
          }
        },autoStopMs);
      }
    }catch(error){
      stopTracks();
      localRecording = false;
      setState("MIC ERROR","error",error.message || "Could not access microphone.");
      resumeWakeAfterResponse();
    }
  }

  function stopLocal(){
    clearTimeout(commandStopTimer);
    if(recorder && recorder.state !== "inactive") recorder.stop();
  }

  function extractCommand(text){
    let value = String(text || "").trim();
    const patterns = profile().wakePatterns;

    for(const pattern of patterns){
      if(pattern.test(value)){
        value = value.replace(pattern,"").trim();
        break;
      }
    }
    return value;
  }

  function acknowledgeWake(){
    if(!("speechSynthesis" in window)) return;

    window.speechSynthesis.cancel();
    const p = profile();
    const utter = new SpeechSynthesisUtterance(
      p.gender === "male" ? "Yes?" : "Yes?"
    );
    utter.lang = "en-US";
    utter.pitch = p.pitch;
    utter.rate = p.rate;
    const selectedVoice = choosePersonaVoice();
    if(selectedVoice) utter.voice = selectedVoice;
    window.speechSynthesis.speak(utter);
  }

  async function sendWakeChunk(blob){
    try{
      const response = await fetch(
        "/api/stt/wake?language=auto&persona=" +
        encodeURIComponent(persona.value),
        {
          method:"POST",
          headers:{"Content-Type":blob.type || "audio/webm"},
          body:blob
        }
      );

      let data = {};
      try{ data = await response.json(); }catch(error){}
      if(!response.ok) return;

      if(data.wake_detected){
        const heard = String(data.text || "").trim();
        const command = extractCommand(heard);
        const name = personaName();

        stopWakeListener();
        setWakeBadge("awake",name.toUpperCase() + " AWAKE");
        setState(name.toUpperCase() + " AWAKE","listening","Wake phrase detected.");

        if(command.length >= 2){
          if(handleRecognizedCommand(command)){
            return;
          }
          input.value = command;
          wakePausedForCommand = true;
          setTimeout(function(){ form.requestSubmit(); },180);
        }else{
          acknowledgeWake();
          setTimeout(function(){
            startLocal(COMMAND_RECORD_MS);
          },450);
        }
      }
    }catch(error){
      setWakeBadge("error",personaName().toUpperCase() + " ERROR");
    }
  }

  async function recordWakeChunk(){
    if(!wakeMode.checked || wakePausedForCommand || wakeListening) return;
    if(!navigator.mediaDevices || !window.MediaRecorder) return;

    const online = await refreshSttStatus();
    if(!online){
      setWakeBadge("error",personaName().toUpperCase() + " OFF");
      return;
    }

    try{
      wakeStream = await navigator.mediaDevices.getUserMedia({
        audio:{
          echoCancellation:true,
          noiseSuppression:true,
          autoGainControl:true
        }
      });

      wakeChunks = [];
      const mimeType = preferredMimeType();
      wakeRecorder = mimeType
        ? new MediaRecorder(wakeStream,{mimeType:mimeType})
        : new MediaRecorder(wakeStream);

      wakeListening = true;

      wakeRecorder.ondataavailable = function(event){
        if(event.data && event.data.size) wakeChunks.push(event.data);
      };

      wakeRecorder.onstop = async function(){
        wakeListening = false;

        const type = wakeRecorder && wakeRecorder.mimeType
          ? wakeRecorder.mimeType
          : "audio/webm";

        const blob = new Blob(wakeChunks,{type:type});
        wakeChunks = [];
        stopWakeTracks();

        if(blob.size >= 800 && wakeMode.checked && !wakePausedForCommand){
          await sendWakeChunk(blob);
        }

        if(wakeMode.checked && !wakePausedForCommand){
          wakeTimer = setTimeout(recordWakeChunk,180);
        }
      };

      wakeRecorder.start(250);
      setWakeBadge(
        "listening",
        personaName().toUpperCase() + " LISTENING"
      );

      wakeTimer = setTimeout(function(){
        if(wakeRecorder && wakeRecorder.state !== "inactive"){
          wakeRecorder.stop();
        }
      },WAKE_CHUNK_MS);
    }catch(error){
      wakeListening = false;
      stopWakeTracks();
      setWakeBadge("error",personaName().toUpperCase() + " ERROR");
      setState("WAKE ERROR","error",error.message || "Wake microphone failed.");
    }
  }

  function startWakeMode(){
    if(!wakeMode.checked) return;

    if(engine.value !== "local"){
      engine.value = "local";
      savePrefs();
    }

    wakePausedForCommand = false;
    setWakeBadge(
      "listening",
      personaName().toUpperCase() + " LISTENING"
    );
    recordWakeChunk();
  }

  function stopWakeListener(){
    clearTimeout(wakeTimer);

    if(wakeRecorder && wakeRecorder.state !== "inactive"){
      wakeRecorder.onstop = function(){
        wakeListening = false;
        wakeChunks = [];
        stopWakeTracks();
      };
      try{ wakeRecorder.stop(); }catch(error){}
    }else{
      wakeListening = false;
      stopWakeTracks();
    }
  }

  function resumeWakeAfterResponse(){
    if(!wakeMode.checked) return;
    wakePausedForCommand = false;
    setTimeout(startWakeMode,500);
  }

  function setupBrowser(){
    if(!SR) return;

    recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.lang = lang.value;

    recognition.onstart = function(){
      browserListening = true;
      setState("BROWSER LISTENING","listening","Speak now…");
    };

    recognition.onresult = function(event){
      let interim = "";
      let finalText = "";

      for(let i=event.resultIndex;i<event.results.length;i++){
        const text = event.results[i][0].transcript;
        if(event.results[i].isFinal) finalText += text;
        else interim += text;
      }

      const transcript = (finalText || interim).trim();
      if(transcript){
        input.value = transcript;
        setState(
          finalText ? "HEARD" : "BROWSER LISTENING",
          finalText ? "ready" : "listening",
          transcript
        );
      }

      if(finalText){
        if(handleRecognizedCommand(finalText)){
          return;
        }
        if(autoSend.checked){
          setTimeout(function(){ form.requestSubmit(); },180);
        }
      }
    };

    recognition.onerror = function(event){
      browserListening = false;
      const errors = {
        "not-allowed":"Microphone permission was blocked.",
        "audio-capture":"No working microphone was found.",
        "no-speech":"No speech was detected.",
        "network":"Browser speech service had a network error."
      };

      setState(
        "VOICE ERROR",
        "error",
        errors[event.error] || ("Speech error: " + event.error)
      );
    };

    recognition.onend = function(){
      browserListening = false;
      voiceBtn.classList.remove("listening");
      voiceMiniBtn.classList.remove("listening");
    };
  }

  function toggleBrowser(){
    if(!recognition){
      setState("UNSUPPORTED","error","Browser Speech is unavailable.");
      return;
    }

    if(browserListening){
      try{ recognition.stop(); }catch(error){}
      return;
    }

    recognition.lang = lang.value;

    try{ recognition.start(); }
    catch(error){
      setState("VOICE ERROR","error",error.message || "Could not start browser speech.");
    }
  }

  async function toggleVoice(){
    if(engine.value === "local"){
      if(localRecording) stopLocal();
      else await startLocal();
    }else{
      toggleBrowser();
    }
  }

  function stopAll(){
    clearTimeout(commandStopTimer);
    stopWakeListener();

    if(localRecording) stopLocal();

    if(recognition && browserListening){
      try{ recognition.stop(); }catch(error){}
    }

    if("speechSynthesis" in window) window.speechSynthesis.cancel();

    stopTracks();
    setState("READY","ready","Voice stopped.");
    setWakeBadge("off",personaName().toUpperCase() + " OFF");
  }

  loadPrefs();
  refreshPersonaUi();
  setupBrowser();
  refreshSttStatus();
  setInterval(refreshSttStatus,15000);

  if("speechSynthesis" in window){
    window.speechSynthesis.onvoiceschanged = function(){};
  }

  lang.addEventListener("change",function(){
    if(recognition) recognition.lang = lang.value;
    savePrefs();
  });

  persona.addEventListener("change",function(){
    stopWakeListener();
    if("speechSynthesis" in window) window.speechSynthesis.cancel();
    savePrefs();
    refreshPersonaUi();

    if(wakeMode.checked){
      setState(
        "WAKE MODE",
        "ready",
        "Say Hey " + personaName() + " or " + personaName() + "."
      );
      setTimeout(startWakeMode,350);
    }else{
      setState(
        "READY",
        "ready",
        personaName() + " voice mode selected."
      );
    }
  });

  engine.addEventListener("change",function(){
    stopWakeListener();
    stopTracks();
    savePrefs();

    if(wakeMode.checked && engine.value !== "local"){
      wakeMode.checked = false;
      savePrefs();
      setWakeBadge("off",personaName().toUpperCase() + " OFF");
    }

    setState(
      "READY",
      "ready",
      engine.value === "local"
        ? "Local Whisper ready. Say Hey " + personaName() + " with Wake Mode on."
        : "Browser Speech ready. Click MIC and speak."
    );
  });

  wakeMode.addEventListener("change",function(){
    savePrefs();

    if(wakeMode.checked){
      engine.value = "local";
      savePrefs();
      startWakeMode();
      setState(
        "WAKE MODE",
        "ready",
        "Say Hey " + personaName() + " or " + personaName() + "."
      );
    }else{
      wakePausedForCommand = false;
      stopWakeListener();
      setWakeBadge("off",personaName().toUpperCase() + " OFF");
      setState("READY","ready","Wake Mode is off.");
    }
  });

  autoSend.addEventListener("change",savePrefs);
  speakReplies.addEventListener("change",savePrefs);
  stopBtn.addEventListener("click",stopAll);
  voiceBtn.addEventListener("click",toggleVoice);
  voiceMiniBtn.addEventListener("click",toggleVoice);

  document.addEventListener("keydown",function(event){
    if(event.ctrlKey && event.code === "Space"){
      event.preventDefault();
      toggleVoice();
    }
  });

  const messages = document.querySelector("#messages");
  if(messages && "MutationObserver" in window){
    const observer = new MutationObserver(function(){
      const nodes = messages.querySelectorAll(".agent-message p");
      if(!nodes.length) return;

      const text = nodes[nodes.length - 1].textContent || "";

      if(
        text &&
        text !== lastAgentText &&
        text.indexOf("Routing request") !== 0
      ){
        lastAgentText = text;

        if(wakePausedForCommand){
          if(speakReplies.checked) speak(text);
          else resumeWakeAfterResponse();
        }else{
          speak(text);
        }
      }
    });

    observer.observe(messages,{childList:true,subtree:true});
  }

  setState(
    "READY",
    "ready",
    wakeMode.checked
      ? "Say Hey " + personaName() + " or " + personaName() + "."
      : personaName() + " voice mode ready."
  );

  if(wakeMode.checked){
    setTimeout(startWakeMode,800);
  }else{
    setWakeBadge("off",personaName().toUpperCase() + " OFF");
  }
})();