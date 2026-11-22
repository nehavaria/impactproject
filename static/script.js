// Apply data-width and data-color attributes
document.querySelectorAll(".stat-fill, .prod-bar-fill, .aqi-bar-fill").forEach(function(el) {
    var w = el.getAttribute("data-width");
    var c = el.getAttribute("data-color");
    if (w) el.style.width = w + "%";
    if (c) el.style.background = c;
});
document.querySelectorAll(".aqi-number, .aqi-level").forEach(function(el) {
    var c = el.getAttribute("data-color");
    if (c) el.style.color = c;
});

function toggleFavorite(city) {
    const btn = document.getElementById("fav-btn");
    fetch("/favorite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ city: city })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === "added") {
            btn.innerHTML = "&#11088; Saved";
            btn.classList.add("fav-active");
        } else {
            btn.innerHTML = "&#9734; Save City";
            btn.classList.remove("fav-active");
        }
    });
}

// ========================= AI CHATBOT =========================
function toggleChat() {
    document.getElementById("chat-widget").classList.toggle("open");
    if (document.getElementById("chat-widget").classList.contains("open")) {
        document.getElementById("chat-input").focus();
    }
}

function sendChat() {
    const input = document.getElementById("chat-input");
    const msg = input.value.trim();
    if (!msg) return;
    input.value = "";
    appendMsg(msg, "user");
    const typing = appendMsg("NEBULA is thinking...", "bot", true);
    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, weather: WEATHER_DATA })
    })
    .then(r => r.json())
    .then(data => { typing.remove(); appendMsg(data.reply, "bot"); })
    .catch(() => { typing.remove(); appendMsg("Sorry, I couldn't connect. Please try again.", "bot"); });
}

function appendMsg(text, who, isTyping = false) {
    const box = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "chat-msg " + who + (isTyping ? " chat-typing" : "");
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.textContent = text;
    div.appendChild(bubble);
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    return div;
}

// ========================= CLOCK + DATE =========================
function updateClock() {
    const now = new Date();
    const clockEl = document.getElementById("clock");
    const dateEl = document.getElementById("date-display");
    if (clockEl) clockEl.textContent = now.toLocaleTimeString();
    if (dateEl) dateEl.textContent = now.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
}
setInterval(updateClock, 1000);
updateClock();

// ========================= GREETING =========================
const greetEl = document.getElementById("greeting");
if (greetEl) {
    const h = new Date().getHours();
    greetEl.textContent = h < 12 ? "Morning" : h < 17 ? "Afternoon" : "Evening";
}

// ========================= SEARCH LOADING =========================
const form = document.getElementById("search-form");
if (form) {
    form.addEventListener("submit", function () {
        document.getElementById("btn-text").style.display = "none";
        document.getElementById("btn-spinner").style.display = "inline";
        document.getElementById("search-btn").disabled = true;
    });
}

// ========================= FLASH AUTO-DISMISS =========================
document.querySelectorAll(".flash").forEach(function (el) {
    setTimeout(function () {
        el.style.transition = "opacity 0.5s";
        el.style.opacity = "0";
        setTimeout(function () { el.remove(); }, 500);
    }, 5000);
});

// ========================= C / F TOGGLE =========================
let currentUnit = "C";
function setUnit(unit) {
    currentUnit = unit;
    document.getElementById("btn-c").classList.toggle("active", unit === "C");
    document.getElementById("btn-f").classList.toggle("active", unit === "F");
    const tempEl = document.getElementById("temp-display");
    const feelsEl = document.getElementById("feels-display");
    if (tempEl) tempEl.textContent = (unit === "C" ? tempEl.dataset.c : tempEl.dataset.f) + "\u00b0" + unit;
    if (feelsEl) feelsEl.textContent = (unit === "C" ? feelsEl.dataset.c : feelsEl.dataset.f) + "\u00b0" + unit;
}

// ========================= SIDEBAR TOGGLE =========================
function toggleSidebar() {
    document.getElementById("sidebar").classList.toggle("open");
}
document.addEventListener("click", function (e) {
    const sidebar = document.getElementById("sidebar");
    const hamburger = document.getElementById("hamburger");
    if (sidebar && hamburger && !sidebar.contains(e.target) && !hamburger.contains(e.target)) {
        sidebar.classList.remove("open");
    }
});

// ========================= VOICE SEARCH =========================
function startVoice() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { alert("Voice search is not supported in your browser. Try Chrome."); return; }
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    const btn = document.getElementById("voice-btn");
    btn.classList.add("listening");
    btn.textContent = "\uD83D\uDD34";
    recognition.start();
    recognition.onresult = function (e) {
        let transcript = e.results[0][0].transcript.replace(/weather in /i, "").trim();
        document.getElementById("city-input").value = transcript;
        btn.classList.remove("listening");
        btn.textContent = "\uD83C\uDF99";
        document.getElementById("search-form").submit();
    };
    recognition.onerror = function () {
        btn.classList.remove("listening");
        btn.textContent = "\uD83C\uDF99";
    };
    recognition.onend = function () {
        btn.classList.remove("listening");
        btn.textContent = "\uD83C\uDF99";
    };
}

// ========================= TEXT-TO-SPEECH =========================
function speakWeather() {
    if (!window.speechSynthesis) { alert("Text-to-speech not supported in your browser."); return; }
    window.speechSynthesis.cancel();
    const d = WEATHER_DATA;
    if (!d.city) return;
    const unit = currentUnit === "C" ? "degrees Celsius" : "degrees Fahrenheit";
    const tempEl = document.getElementById("temp-display");
    const temp = tempEl ? tempEl.textContent.replace("\u00b0C", "").replace("\u00b0F", "").trim() : d.temp;
    const text = "Current weather in " + d.city + ". Temperature is " + temp + " " + unit + ". Conditions: " + d.desc + ". Humidity is " + d.humidity + " percent. Wind speed is " + d.wind + " kilometers per hour.";
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
}

// ========================= WEATHER PARTICLE ANIMATIONS =========================
(function () {
    const canvas = document.getElementById("weather-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const type = typeof WEATHER_TYPE !== "undefined" ? WEATHER_TYPE : "default";

    function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
    resize();
    window.addEventListener("resize", resize);

    if (type === "rain" || type === "thunder") {
        const drops = Array.from({ length: 180 }, () => ({
            x: Math.random() * window.innerWidth,
            y: Math.random() * window.innerHeight,
            len: Math.random() * 18 + 8,
            speed: Math.random() * 8 + 10,
            opacity: Math.random() * 0.4 + 0.2
        }));
        let lightningTimer = 0;
        let lightningOn = false;

        function drawRain() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            if (type === "thunder") {
                lightningTimer++;
                if (lightningTimer > 180 && Math.random() < 0.03) {
                    lightningOn = true;
                    lightningTimer = 0;
                    setTimeout(function() { lightningOn = false; }, 120);
                }
                if (lightningOn) {
                    ctx.fillStyle = "rgba(200,210,255,0.08)";
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    ctx.strokeStyle = "rgba(180,200,255,0.7)";
                    ctx.lineWidth = 2;
                    ctx.shadowBlur = 20;
                    ctx.shadowColor = "#a5b4fc";
                    ctx.beginPath();
                    const lx = Math.random() * canvas.width * 0.6 + canvas.width * 0.2;
                    ctx.moveTo(lx, 0);
                    let cy = 0;
                    while (cy < canvas.height * 0.7) {
                        cy += Math.random() * 60 + 30;
                        ctx.lineTo(lx + (Math.random() - 0.5) * 80, cy);
                    }
                    ctx.stroke();
                    ctx.shadowBlur = 0;
                }
            }
            ctx.strokeStyle = "rgba(174,214,241,0.5)";
            ctx.lineWidth = 1;
            drops.forEach(function(d) {
                ctx.globalAlpha = d.opacity;
                ctx.beginPath();
                ctx.moveTo(d.x, d.y);
                ctx.lineTo(d.x - 1, d.y + d.len);
                ctx.stroke();
                d.y += d.speed;
                if (d.y > canvas.height) { d.y = -d.len; d.x = Math.random() * canvas.width; }
            });
            ctx.globalAlpha = 1;
            requestAnimationFrame(drawRain);
        }
        drawRain();

    } else if (type === "snow") {
        const flakes = Array.from({ length: 120 }, () => ({
            x: Math.random() * window.innerWidth,
            y: Math.random() * window.innerHeight,
            r: Math.random() * 3 + 1,
            speed: Math.random() * 1.2 + 0.4,
            drift: (Math.random() - 0.5) * 0.5,
            opacity: Math.random() * 0.5 + 0.3
        }));
        function drawSnow() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            flakes.forEach(function(f) {
                ctx.globalAlpha = f.opacity;
                ctx.fillStyle = "#e0f2fe";
                ctx.beginPath();
                ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
                ctx.fill();
                f.y += f.speed;
                f.x += f.drift;
                if (f.y > canvas.height) { f.y = -f.r; f.x = Math.random() * canvas.width; }
            });
            ctx.globalAlpha = 1;
            requestAnimationFrame(drawSnow);
        }
        drawSnow();

    } else if (type === "sunny") {
        let angle = 0;
        function drawSun() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            const cx = canvas.width - 120, cy = 120, rays = 12;
            angle += 0.003;
            for (let i = 0; i < rays; i++) {
                const a = (i / rays) * Math.PI * 2 + angle;
                const x1 = cx + Math.cos(a) * 55;
                const y1 = cy + Math.sin(a) * 55;
                const x2 = cx + Math.cos(a) * 110;
                const y2 = cy + Math.sin(a) * 110;
                const grad = ctx.createLinearGradient(x1, y1, x2, y2);
                grad.addColorStop(0, "rgba(251,191,36,0.35)");
                grad.addColorStop(1, "rgba(251,191,36,0)");
                ctx.strokeStyle = grad;
                ctx.lineWidth = 3;
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
            }
            const glow = ctx.createRadialGradient(cx, cy, 10, cx, cy, 60);
            glow.addColorStop(0, "rgba(251,191,36,0.18)");
            glow.addColorStop(1, "rgba(251,191,36,0)");
            ctx.fillStyle = glow;
            ctx.beginPath();
            ctx.arc(cx, cy, 60, 0, Math.PI * 2);
            ctx.fill();
            requestAnimationFrame(drawSun);
        }
        drawSun();

    } else if (type === "cloudy" || type === "fog") {
        const clouds = Array.from({ length: 6 }, function(_, i) {
            return {
                x: Math.random() * window.innerWidth,
                y: 60 + i * 80,
                w: Math.random() * 200 + 150,
                h: Math.random() * 50 + 40,
                speed: Math.random() * 0.3 + 0.1,
                opacity: type === "fog" ? 0.06 : 0.08
            };
        });
        function drawClouds() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            clouds.forEach(function(c) {
                ctx.globalAlpha = c.opacity;
                ctx.fillStyle = "#94a3b8";
                ctx.beginPath();
                ctx.ellipse(c.x, c.y, c.w, c.h, 0, 0, Math.PI * 2);
                ctx.fill();
                c.x += c.speed;
                if (c.x - c.w > canvas.width) c.x = -c.w;
            });
            ctx.globalAlpha = 1;
            requestAnimationFrame(drawClouds);
        }
        drawClouds();
    }
})();
