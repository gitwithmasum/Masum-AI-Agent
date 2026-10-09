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

// v4.0 Voice Agent
(function(){
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const voiceBtn = document.querySelector("#voiceBtn");
  const voiceMiniBtn = document.querySelector("#voiceMiniBtn");
  const voiceState = document.querySelector("#voiceState");
  const voiceHint = document.querySelector("#voiceHint");
  const voiceConsole = document.querySelector("#voiceConsole");
  const input = document.querySelector("#chatInput");
  const form = document.querySelector("#chatForm");
  const lang = document.querySelector("#voiceLanguage");
  const autoSend = document.querySelector("#voiceAutoSend");
  const speakReplies = document.querySelector("#speakReplies");
  const stopBtn = document.querySelector("#stopSpeechBtn");
  if(!voiceBtn || !voiceMiniBtn || !input || !form) return;
  let recognition = null;
  let listening = false;
  let lastAgentText = "";

  function setState(label, mode, hint){
    voiceState.textContent = label;
    voiceState.className = mode === "listening" ? "listening" : (mode === "error" ? "error" : "");
    voiceBtn.classList.toggle("listening", mode === "listening");
    voiceMiniBtn.classList.toggle("listening", mode === "listening");
    if(hint) voiceHint.textContent = hint;
  }

  function savePrefs(){
    localStorage.setItem("masum.voice.lang", lang.value);
    localStorage.setItem("masum.voice.auto", autoSend.checked ? "1" : "0");
    localStorage.setItem("masum.voice.speak", speakReplies.checked ? "1" : "0");
  }

  function loadPrefs(){
    const savedLang = localStorage.getItem("masum.voice.lang");
    if(savedLang) lang.value = savedLang;
    const savedAuto = localStorage.getItem("masum.voice.auto");
    autoSend.checked = savedAuto === null ? true : savedAuto === "1";
    speakReplies.checked = localStorage.getItem("masum.voice.speak") === "1";
  }

  function cleanSpeech(text){
    return String(text || "").replace(/https?:\/\/\S+/g, " link ").replace(/[#*_>~]/g, " ").replace(/\s+/g, " ").trim();
  }

  function speak(text){
    if(!("speechSynthesis" in window) || !speakReplies.checked) return;
    const clean = cleanSpeech(text);
    if(!clean) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(clean.slice(0, 1800));
    utter.lang = lang.value;
    utter.rate = lang.value.indexOf("bn") === 0 ? 0.95 : 1;
    setState("SPEAKING", "ready", "Masum AI is speaking.");
    utter.onend = function(){ setState("READY", "ready", "Click MIC or press Ctrl + Space and speak."); };
    utter.onerror = function(){ setState("TTS ERROR", "error", "Browser voice output failed."); };
    window.speechSynthesis.speak(utter);
  }

  function toggle(){
    if(!recognition) return;
    if("speechSynthesis" in window) window.speechSynthesis.cancel();
    if(listening){ try{ recognition.stop(); }catch(e){} return; }
    recognition.lang = lang.value;
    try{ recognition.start(); }catch(e){ setState("VOICE ERROR", "error", e.message || "Could not start microphone."); }
  }

  loadPrefs();
  lang.addEventListener("change", savePrefs);
  autoSend.addEventListener("change", savePrefs);
  speakReplies.addEventListener("change", savePrefs);
  stopBtn.addEventListener("click", function(){
    if(recognition && listening){ try{ recognition.stop(); }catch(e){} }
    if("speechSynthesis" in window) window.speechSynthesis.cancel();
    setState("READY", "ready", "Voice stopped.");
  });

  if(!SR){
    voiceBtn.disabled = true;
    voiceMiniBtn.disabled = true;
    voiceConsole.classList.add("voice-unsupported");
    setState("UNSUPPORTED", "error", "Speech recognition is unavailable. Try Chrome or Edge.");
  }else{
    recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.lang = lang.value;
    recognition.onstart = function(){ listening = true; setState("LISTENING", "listening", "Speak now…"); };
    recognition.onresult = function(event){
      let interim = "";
      let finalText = "";
      for(let i=event.resultIndex;i<event.results.length;i++){
        const t = event.results[i][0].transcript;
        if(event.results[i].isFinal) finalText += t; else interim += t;
      }
      const transcript = (finalText || interim).trim();
      if(transcript){ input.value = transcript; setState(finalText ? "HEARD" : "LISTENING", finalText ? "ready" : "listening", transcript); }
      if(finalText && autoSend.checked){ setTimeout(function(){ form.requestSubmit(); }, 180); }
    };
    recognition.onerror = function(event){
      listening = false;
      const errors = {"not-allowed":"Microphone permission was blocked.","audio-capture":"No working microphone was found.","no-speech":"No speech was detected.","network":"Browser speech service had a network error."};
      setState("VOICE ERROR", "error", errors[event.error] || ("Speech error: " + event.error));
    };
    recognition.onend = function(){ listening = false; voiceBtn.classList.remove("listening"); voiceMiniBtn.classList.remove("listening"); };
    voiceBtn.addEventListener("click", toggle);
    voiceMiniBtn.addEventListener("click", toggle);
    setState("READY", "ready", "Click MIC or press Ctrl + Space and speak.");
  }

  document.addEventListener("keydown", function(event){
    if(event.ctrlKey && event.code === "Space"){ event.preventDefault(); toggle(); }
  });

  const messages = document.querySelector("#messages");
  if(messages && "MutationObserver" in window){
    const observer = new MutationObserver(function(){
      const nodes = messages.querySelectorAll(".agent-message p");
      if(!nodes.length) return;
      const text = nodes[nodes.length - 1].textContent || "";
      if(text && text !== lastAgentText && text.indexOf("Routing request") !== 0){
        lastAgentText = text;
        speak(text);
      }
    });
    observer.observe(messages, {childList:true, subtree:true});
  }
})();
