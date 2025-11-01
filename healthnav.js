// script.js — EMS Assist frontend logic (no backend)

// ====== CLOCK ======
function updateClock() {
  const clock = document.getElementById("clock");
  const now = new Date();
  clock.textContent = now.toLocaleString();
}
setInterval(updateClock, 1000);
updateClock();

// ====== SEVERITY TOGGLE ======
const btnCritical = document.getElementById("btn-critical");
const btnStable = document.getElementById("btn-stable");

btnCritical.addEventListener("click", () => toggleSeverity("critical"));
btnStable.addEventListener("click", () => toggleSeverity("stable"));

let severity = "critical";
function toggleSeverity(state) {
  severity = state;
  btnCritical.classList.toggle("active", state === "critical");
  btnStable.classList.toggle("active", state === "stable");
  btnCritical.setAttribute("aria-pressed", state === "critical");
  btnStable.setAttribute("aria-pressed", state === "stable");
  showToast(`Status set to: ${state.toUpperCase()}`);
}

// ====== CHAT HANDLING ======
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatLog = document.getElementById("chat-log");
const resultsBox = document.getElementById("results-box");

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  addMessage("user", text);
  chatInput.value = "";
  simulateAIResponse(text);
});

function addMessage(type, text) {
  const msg = document.createElement("div");
  msg.className = `msg ${type}`;
  msg.textContent = text;
  chatLog.appendChild(msg);
  chatLog.scrollTop = chatLog.scrollHeight;
}

// Simulate an AI reply (no backend)
function simulateAIResponse(input) {
  addMessage("meta", "AI is thinking...");

  setTimeout(() => {
    // Remove "thinking" message
    chatLog.lastChild.remove();

    const response = getMockResponse(input);
    addMessage("ai", response.message);
    showRecommendations(response.recommendations);
  }, 1000);
}

// ====== MOCK RECOMMENDATION LOGIC ======
function getMockResponse(input) {
  input = input.toLowerCase();
  let message, recs;

  if (input.includes("cardiac") || input.includes("heart")) {
    message = "Detected possible cardiac emergency. Recommending cardiac-capable hospitals.";
    recs = [
      { name: "Saint Mary's Medical Center", eta: "6 min", tags: ["Cardiology", "ICU", "24/7 ER"] },
      { name: "Mercy Heart Institute", eta: "10 min", tags: ["Cardiac Surgery", "Cath Lab"] },
    ];
  } else if (input.includes("stroke")) {
    message = "Suspected stroke. Prioritizing stroke-certified facilities.";
    recs = [
      { name: "Riverfront General", eta: "7 min", tags: ["Stroke Center", "Neurology"] },
      { name: "Metro Hospital", eta: "12 min", tags: ["CT Scan", "Emergency Department"] },
    ];
  } else if (input.includes("trauma")) {
    message = "Trauma incident detected. Showing nearest trauma centers.";
    recs = [
      { name: "County Trauma Center", eta: "5 min", tags: ["Level I Trauma", "Helipad"] },
      { name: "Westfield Medical", eta: "8 min", tags: ["ER", "Surgery Team"] },
    ];
  } else {
    message = "General condition noted. Displaying nearby hospitals.";
    recs = [
      { name: "Downtown Hospital", eta: "5 min", tags: ["Emergency", "X-Ray"] },
      { name: "Lakeside Clinic", eta: "9 min", tags: ["Urgent Care"] },
    ];
  }

  return { message, recommendations: recs };
}

// ====== RECOMMENDATION DISPLAY ======
function showRecommendations(list) {
  resultsBox.innerHTML = "";
  list.forEach((rec) => {
    const div = document.createElement("div");
    div.className = "rec";
    div.innerHTML = `
      <div class="title">
        <span class="name">${rec.name}</span>
        <span class="eta">${rec.eta}</span>
      </div>
      <div class="badges">
        ${rec.tags.map((t) => `<span class="badge">${t}</span>`).join("")}
      </div>
    `;
    resultsBox.appendChild(div);
  });
}

// ====== MAP SETUP (Leaflet) ======
const map = L.map("map").setView([0, 0], 13);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap",
}).addTo(map);

let incidentMarker;

function setIncident(lat, lng) {
  if (incidentMarker) map.removeLayer(incidentMarker);
  incidentMarker = L.marker([lat, lng]).addTo(map).bindPopup("Incident location").openPopup();
  showToast("Incident location set.");
}

// Try to locate user
map.on("click", (e) => setIncident(e.latlng.lat, e.latlng.lng));

map.on("locationfound", (e) => {
  map.setView(e.latlng, 13);
  setIncident(e.latlng.lat, e.latlng.lng);
});

map.on("locationerror", () => {
  showToast("Could not access location — click map to set manually.");
});

// Trigger geolocation
map.locate({ setView: true, maxZoom: 13 });

// Add mock hospital markers
const hospitals = [
  { name: "Saint Mary's Medical Center", lat: 37.7749, lng: -122.4194, tags: ["Cardiology", "ICU"] },
  { name: "Riverfront General", lat: 37.7849, lng: -122.4094, tags: ["Stroke Center", "Neurology"] },
  { name: "County Trauma Center", lat: 37.7649, lng: -122.4294, tags: ["Trauma", "ER"] },
];
hospitals.forEach((h) => {
  const marker = L.marker([h.lat, h.lng]).addTo(map);
  marker.bindPopup(
    `<b>${h.name}</b><br>${h.tags.map((t) => `<span class="badge">${t}</span>`).join(" ")}`
  );
});

// ====== TOAST NOTIFICATIONS ======
function showToast(msg, duration = 3000) {
  const toasts = document.getElementById("toasts");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = msg;
  toasts.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}
