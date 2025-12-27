const statusText = document.querySelector(".listening");
const aiText = document.querySelector(".ai-on");

function updateStatus() {
    fetch("/api/status")
        .then(res => res.json())
        .then(data => {
            if (data.silent) {
                statusText.textContent = "Silent";
                statusText.style.color = "red";
            } else if (data.speaking) {
                statusText.textContent = "Speaking";
                statusText.style.color = "#2196f3";
            } else {
                statusText.textContent = "Listening";
                statusText.style.color = "#4caf50";
            }

            aiText.textContent = data.ai ? "ON" : "OFF";
            aiText.style.color = data.ai ? "#00adb5" : "gray";
        });
}

setInterval(updateStatus, 1000);


// ---------------- BUTTON ACTIONS ----------------

function sendCommand(cmd) {
    fetch("/api/command", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({command: cmd})
    });
}

document.querySelectorAll("button")[0].onclick = () => sendCommand("rex type mode");
document.querySelectorAll("button")[1].onclick = () => fetch("/api/focus", {method: "POST"});
document.querySelectorAll("button")[2].onclick = () => fetch("/api/silent", {method: "POST"});
document.querySelectorAll("button")[3].onclick = () => fetch("/api/ai", {method: "POST"});


const micBtn = document.getElementById("micBtn");
let micRunning = false;

micBtn.onclick = () => {
    if (!micRunning) {
        fetch("/api/mic/start", { method: "POST" })
            .then(res => res.json())
            .then(data => {
                if (data.status === "started") {
                    micRunning = true;
                    micBtn.textContent = "🛑 Stop Mic";
                    micBtn.style.background = "#e53935";
                } else if (data.status === "pyaudio_missing") {
                    alert("PyAudio not installed. Mic unavailable.");
                }
            });
    } else {
        fetch("/api/mic/stop", { method: "POST" })
            .then(() => {
                micRunning = false;
                micBtn.textContent = "🎙 Start Mic";
                micBtn.style.background = "";
            });
    }
};
