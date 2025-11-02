// ====== EMS Assist Frontend Logic (UI Only) ======

// ----- CLOCK -----
function updateClock() {
  const clock = document.getElementById("clock");
  clock.textContent = new Date().toLocaleString();
}
setInterval(updateClock, 1000);
updateClock();

// ----- SEVERITY TOGGLE -----
const btnCritical = document.getElementById("btn-critical");
const btnStable = document.getElementById("btn-stable");

let severity = "critical";

btnCritical.addEventListener("click", () => toggleSeverity("critical"));
btnStable.addEventListener("click", () => toggleSeverity("stable"));

function toggleSeverity(state) {
  severity = state;
  btnCritical.classList.toggle("active", state === "critical");
  btnStable.classList.toggle("active", state === "stable");
  btnCritical.setAttribute("aria-pressed", state === "critical");
  btnStable.setAttribute("aria-pressed", state === "stable");
  showToast(`Status set to: ${state.toUpperCase()}`);
}

// ----- CHAT FORM HANDLER -----
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatLog = document.getElementById("chat-log");
const resultsBox = document.getElementById("results-box");

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  addMessage("user", text);
  chatInput.value = "";

  try {
    const response = await fetch("http://192.168.0.55:5000/api/advice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symptoms: text }) // matches backend
    });
    const data = await response.json();

    addMessage("ai", data.message);// shows AI response

    // Optional: if your backend returns structured recommendations, show them
    if (data.recommendations) displayRecommendations(data.recommendations);

  } catch (err) {
    addMessage("meta", "Error contacting backend.");
    console.error(err);
  }
});

function addMessage(type, text) {
  const msg = document.createElement("div");
  msg.className = `msg ${type}`;
  msg.textContent = text;
  chatLog.appendChild(msg);
  chatLog.scrollTop = chatLog.scrollHeight;
}

// ----- DISPLAY RECOMMENDATIONS (OPTIONAL) -----
function displayRecommendations(list) {
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
        ${rec.tags.map(t => `<span class="badge">${t}</span>`).join(" ")}
      </div>
    `;
    resultsBox.appendChild(div);
  });
}

// ----- MAP SETUP (Leaflet) -----
const map = L.map("map").setView([37.7749, -122.4194], 13); // default view
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap",
}).addTo(map);

let incidentMarker;

map.on("click", (e) => setIncident(e.latlng.lat, e.latlng.lng));

function setIncident(lat, lng) {
  if (incidentMarker) map.removeLayer(incidentMarker);
  incidentMarker = L.marker([lat, lng]).addTo(map).bindPopup("Incident location").openPopup();
  showToast("Incident location set.");
}

map.locate({ setView: true, maxZoom: 13 });
map.on("locationfound", (e) => setIncident(e.latlng.lat, e.latlng.lng));
map.on("locationerror", () => showToast("Could not access location — click map to set manually."));

// ----- TOAST NOTIFICATIONS -----
function showToast(msg, duration = 3000) {
  const toasts = document.getElementById("toasts");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = msg;
  toasts.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}
