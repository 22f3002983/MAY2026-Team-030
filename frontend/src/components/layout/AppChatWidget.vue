<script setup>
import { ref, nextTick } from 'vue'
import api from '../../api/axios'
import { useAuthStore } from '../../stores/auth'


const auth = useAuthStore()


const open = ref(false)
const draft = ref('')
const typing = ref(false)
const messageList = ref(null)


const messages = ref([
  { from: 'assistant', text: "Hi! I'm the Niwaas Assistant. Ask me things like 'how do I raise a complaint' or 'where do I pay my dues'." },
])


function toggle() {
  open.value = !open.value
}


async function scrollToBottom() {
  await nextTick()
  if (messageList.value) {
    messageList.value.scrollTop = messageList.value.scrollHeight
  }
}


async function sendMessage() {
  const text = draft.value.trim()
  if (!text || typing.value) return


  messages.value.push({ from: 'user', text })
  draft.value = ''
  scrollToBottom()


  typing.value = true
  try {
    const res = await api.post('/ai-assistant/chat', { message: text, role: auth.role })
    messages.value.push({ from: 'assistant', text: res.data.reply })
  } catch (err) {
    messages.value.push({ from: 'assistant', text: 'Sorry, something went wrong. Please try again.' })
  } finally {
    typing.value = false
    scrollToBottom()
  }
}
</script>


<template>
  <div class="chat-widget">
    <div v-if="open" class="chat-panel">
      <div class="chat-header">
        <span>Niwaas Assistant</span>
        <button class="chat-close" @click="toggle">✕</button>
      </div>


      <div class="chat-messages" ref="messageList">
        <div
          v-for="(m, i) in messages"
          :key="i"
          :class="['chat-bubble', m.from === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant']"
        >
          {{ m.text }}
        </div>


        <div v-if="typing" class="chat-bubble chat-bubble-assistant chat-typing">
          <span></span><span></span><span></span>
        </div>
      </div>


      <div class="chat-input-row">
        <input
          v-model="draft"
          type="text"
          placeholder="Ask a question..."
          class="chat-input"
          @keyup.enter="sendMessage"
        />
        <button class="chat-send" :disabled="!draft.trim() || typing" @click="sendMessage">➤</button>
      </div>
    </div>


    <button class="chat-fab" @click="toggle" :aria-label="open ? 'Close assistant' : 'Open assistant'">
      {{ open ? '✕' : '💬' }}
    </button>
  </div>
</template>


<style scoped>
.chat-widget {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 500;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}


.chat-fab {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: var(--c-800);
  color: #fff;
  font-size: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-btn);
  transition: background var(--transition-fast);
}


.chat-fab:hover { background: var(--c-900); }


.chat-panel {
  width: 320px;
  max-width: calc(100vw - 48px);
  height: 420px;
  max-height: calc(100vh - 120px);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}


.chat-header {
  background: var(--c-800);
  color: #fff;
  padding: 14px 16px;
  font-size: var(--font-size-md);
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}


.chat-close {
  width: 26px;
  height: 26px;
  border-radius: var(--radius-sm);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition-fast);
}


.chat-close:hover { background: rgba(255,255,255,0.15); }


.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--color-surface-soft);
}


.chat-bubble {
  max-width: 85%;
  padding: 9px 12px;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  line-height: 1.45;
  white-space: pre-line;
}


.chat-bubble-assistant {
  align-self: flex-start;
  background: var(--color-surface);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}


.chat-bubble-user {
  align-self: flex-end;
  background: var(--c-800);
  color: #fff;
}


.chat-typing {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px;
}


.chat-typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-text-muted);
  animation: chat-typing-bounce 1s infinite ease-in-out;
}


.chat-typing span:nth-child(2) { animation-delay: 0.15s; }
.chat-typing span:nth-child(3) { animation-delay: 0.3s; }


@keyframes chat-typing-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-4px); opacity: 1; }
}


.chat-input-row {
  display: flex;
  gap: 8px;
  padding: 10px;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
  flex-shrink: 0;
}


.chat-input {
  flex: 1;
  height: 38px;
  padding: 0 12px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  background: var(--color-surface-soft);
  color: var(--color-text-primary);
  outline: none;
  transition: border-color var(--transition-fast);
}


.chat-input:focus { border-color: var(--c-600); }


.chat-send {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  flex-shrink: 0;
  transition: background var(--transition-fast);
}


.chat-send:hover:not(:disabled) { background: var(--c-900); }
.chat-send:disabled { opacity: 0.5; cursor: not-allowed; }
</style>



