// mode settings
const modeSet = document.getElementById("mode-set");
if (localStorage.getItem("mode-set") == null || localStorage.getItem("mode-set") == '') {
  localStorage.setItem("mode-set", "0");
} else {
  if (localStorage.getItem("mode-set") == "1") {
    modeSet.innerText = "Mode: Rubric";
    modeSet.style.color = "red";
    modeSet.style.border = "1px solid red";
  }
}

function escapeHTML(str) {
  const entityMap = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  };
  return String(str).replace(/[&<>"']/g, match => entityMap[match]);
}

modeSet.onclick = function () {
  switch (localStorage.getItem("mode-set")) {
    case "0":
      modeSet.innerText = "Mode: Rubric";
      modeSet.style.color = "red";
      modeSet.style.border = "1px solid red";

      localStorage.setItem("mode-set", "1");
      break;
    case "1":
      modeSet.innerText = "Mode: Agentic";
      modeSet.style.color = "var(--matrix-glow)";
      modeSet.style.border = "1px solid rgba(57, 255, 20, 0.3)";

      localStorage.setItem("mode-set", "0");
      break;
  }  
}

const messageContainer = document.getElementById("message-container");
function scrollToBottom() {
  if (messageContainer) {
    messageContainer.scrollTop = messageContainer.scrollHeight;
  }
}

function addAgentOutput (agentText, agentCode) {
  messageContainer.innerHTML += `
  <div class="msg-block assistant">
    <div class="msg-meta">Agent</div>
    <div class="msg-body">
      <span>` + agentText + `</span>
      <code>` + agentCode + `</code>
    </div>
  </div>
  `;
  scrollToBottom();
}

function addUserOutput (userText) {
  messageContainer.innerHTML += `
  <div class="msg-block user">
    <div class="msg-meta">User</div>
    <div class="msg-body">
      <span>` + userText + `</span>
    </div>
  </div>
  `;
  scrollToBottom();
}

const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-btn");

let isAwaitingResponse = 0;

sendButton.onclick = function () {
  if (isAwaitingResponse == 1) {
    return false;
  }
  isAwaitingResponse = 1;

  addUserOutput(chatInput.value);
  addAgentOutput("Cogitating response...", "");

  fetch ("/llm_comm", {
    method : "POST",
    headers : {
      "Content-Type" : "application/json"
    },
    body : JSON.stringify({
      llm_prompt : chatInput.value,
      rubric : localStorage.getItem("mode-set")
    })
  })
  .then(response => response.text())
  .then(data => {
    addAgentOutput("Returned Template", escapeHTML(data));
    isAwaitingResponse = 0;
    chatInput.value = "";
  })
  .catch(error => {
    addAgentOutput("[Error] " + escapeHTML(String(error)));
    isAwaitingResponse = 0;
    chatInput.value = "";
  });
}