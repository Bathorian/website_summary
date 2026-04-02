<script setup lang="ts">
import { ref, onMounted } from 'vue'

const url = ref('')
const selectedModel = ref('anthropic/claude-sonnet-4.5')
const loading = ref(false)
const result = ref<any>(null)
const error = ref<string | null>(null)
const history = ref<any[]>([])
const sidebarCollapsed = ref(false)

const MODELS = [
  { id: 'anthropic/claude-sonnet-4.5', name: 'Claude 4.5 Sonnet' },
  { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini' },
  { id: 'google/gemini-2.5-flash', name: 'Gemini 2.5 Flash' },
]

const API_BASE = 'http://localhost:8000/api'
const VERSION = 'v-2026-04-02-02-05'

async function fetchHistory() {
  try {
    const res = await fetch(`${API_BASE}/summaries`)
    if (res.ok) {
      const data = await res.json()
      history.value = data.summaries
    }
  } catch (err) {
    console.error('Failed to fetch history', err)
  }
}

async function summarize() {
  if (!url.value) return
  loading.value = true
  error.value = null
  result.value = null

  try {
    const res = await fetch(`${API_BASE}/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: url.value,
        model: selectedModel.value,
        force_refresh: true
      })
    })

    if (!res.ok) {
      const errData = await res.json()
      throw new Error(errData.detail || 'Failed to summarize')
    }

    const data = await res.json()
    result.value = data.summary
    await fetchHistory()
  } catch (err: any) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function selectHistoryItem(item: any) {
  result.value = item
  url.value = item.url
}

function startNew() {
  result.value = null
  error.value = null
  url.value = ''
}

const copySuccess = ref(false)

async function copyToClipboard() {
  if (!result.value?.summary) return
  try {
    await navigator.clipboard.writeText(result.value.summary)
    copySuccess.value = true
    setTimeout(() => {
      copySuccess.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy', err)
  }
}

async function deleteSummary(id: string, event: Event) {
  event.stopPropagation()
  if (!confirm('Are you sure you want to delete this summary?')) return

  try {
    const res = await fetch(`${API_BASE}/summaries/${id}`, {
      method: 'DELETE'
    })

    if (res.ok) {
      if (result.value?.id === id) {
        result.value = null
        url.value = ''
      }
      await fetchHistory()
    } else {
      throw new Error('Failed to delete summary')
    }
  } catch (err: any) {
    console.error(err)
    alert(err.message)
  }
}

onMounted(fetchHistory)
</script>

<template>
  <div :id="VERSION" class="app-layout" :class="{ 'sidebar-hidden': sidebarCollapsed }">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <button @click="startNew" class="new-btn">
          <span class="icon">+</span> New Summary
        </button>
      </div>

      <div class="sidebar-content">
        <div class="history-label">Recents</div>
        <div v-if="history.length > 0" class="history-list">
          <div
            v-for="item in history"
            :key="item.id"
            class="history-item"
            :class="{ active: result?.id === item.id }"
            @click="selectHistoryItem(item)"
          >
            <div class="item-title">{{ item.title || 'Untitled' }}</div>
            <button @click="deleteSummary(item.id, $event)" class="delete-btn" title="Delete">×</button>
          </div>
        </div>
        <div v-else class="empty-history">No history yet</div>
      </div>

      <div class="sidebar-footer">
        <div class="user-profile">
          <div class="user-avatar">K</div>
          <div class="user-info">
            <div class="user-name">Kostas</div>
          </div>
        </div>
      </div>

      <button @click="sidebarCollapsed = !sidebarCollapsed" class="toggle-btn" :title="sidebarCollapsed ? 'Expand' : 'Collapse'">
        {{ sidebarCollapsed ? '→' : '←' }}
      </button>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <header class="top-nav">
        <button v-if="sidebarCollapsed" @click="sidebarCollapsed = false" class="menu-btn">☰</button>
        <div class="app-title">Web scraper with LLM summarization app ▾</div>
      </header>

      <div class="content-area">
        <div v-if="error" class="error-msg">
          {{ error }}
        </div>

        <div v-if="result" class="result-view">
          <div class="result-header">
            <div class="result-title-row">
              <h1 class="result-title">{{ result.title || 'Untitled Page' }}</h1>
              <button @click="copyToClipboard" class="copy-btn-top" :class="{ success: copySuccess }">
                <span class="icon">{{ copySuccess ? '✓' : '📋' }}</span>
                {{ copySuccess ? 'Copied!' : 'Copy' }}
              </button>
            </div>
            <div class="result-meta">
              <a :href="result.url" target="_blank" class="source-link">Source ↗</a>
            </div>
          </div>
          <div class="summary-content">
            <div class="summary-text">{{ result.summary }}</div>
          </div>
        </div>

        <div v-else-if="!loading" class="welcome-view">
          <div class="hero">
            <div class="branding">
              <div class="logo">
                <svg viewBox="0 0 24 24" fill="none" stroke="#d4ff00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 2l9 4.5v11L12 22l-9-4.5v-11z" />
                </svg>
              </div>
              <h1 class="brand-name">Distill</h1>
            </div>
            <p class="quote">Drop a URL. Get the essence.</p>
            <div class="center-input-wrapper">
              <input
                v-model="url"
                type="url"
                placeholder="Paste URL to summarize..."
                @keyup.enter="summarize"
                class="center-input"
              />
              <div class="center-actions">
                <select v-model="selectedModel" class="center-model-select">
                  <option v-for="m in MODELS" :key="m.id" :value="m.id">{{ m.name }}</option>
                </select>
                <button @click="summarize" :disabled="loading || !url" class="center-start-btn">
                  Start Summary
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="loading && !result" class="loading-view">
          <div class="spinner"></div>
          <p>Analyzing content...</p>
        </div>
      </div>

      <footer v-if="result || loading" class="input-container">
        <div class="chat-input-wrapper">
          <input
            v-model="url"
            type="url"
            placeholder="Paste URL to summarize..."
            @keyup.enter="summarize"
            :disabled="loading"
            class="chat-input"
          />
          <div class="input-actions">
            <select v-model="selectedModel" :disabled="loading" class="model-select">
              <option v-for="m in MODELS" :key="m.id" :value="m.id">{{ m.name }}</option>
            </select>
            <button @click="summarize" :disabled="loading || !url" class="send-btn">
              <span v-if="loading" class="spinner-small"></span>
              <span v-else>↑</span>
            </button>
          </div>
        </div>
        <p class="disclaimer">Summarizer is AI and can make mistakes. Please double-check responses.</p>
      </footer>
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: #121212;
  color: #e5e7eb;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  position: fixed;
  top: 0;
  left: 0;
}

/* Sidebar */
.sidebar {
  width: 260px;
  background-color: #0e0e0e;
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease, margin-left 0.3s ease;
  position: relative;
  z-index: 10;
  border-right: 1px solid #1f1f1f;
}

.sidebar-hidden .sidebar {
  margin-left: -260px;
}

.sidebar-header {
  padding: 1.5rem 1rem 1rem 1rem;
}

.new-btn {
  width: 100%;
  padding: 0.6rem;
  background-color: transparent;
  color: #e5e7eb;
  border: 1px solid #424242;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.75rem;
  transition: background-color 0.2s;
}

.new-btn:hover {
  background-color: #2f2f2f;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.history-label {
  padding: 0.75rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #9ca3af;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.history-item {
  padding: 0.6rem 0.75rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.history-item:hover {
  background-color: #2f2f2f;
}

.history-item.active {
  background-color: #2f2f2f;
}

.item-title {
  font-size: 0.875rem;
  color: #ececec;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.delete-btn {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0 0.25rem;
  line-height: 1;
  border-radius: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s, color 0.2s;
}

.history-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: #ef4444;
  background-color: rgba(239, 68, 68, 0.1);
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid #2f2f2f;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 0.5rem;
}

.user-profile:hover {
  background-color: #2f2f2f;
}

.user-avatar {
  width: 32px;
  height: 32px;
  background-color: #10b981;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
}

.user-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: #ececec;
}

.user-plan {
  font-size: 0.75rem;
  color: #9ca3af;
}

.toggle-btn {
  position: absolute;
  right: -30px;
  top: 50%;
  transform: translateY(-50%);
  width: 30px;
  height: 60px;
  background: transparent;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #9ca3af;
  opacity: 0;
  transition: opacity 0.2s;
}

.sidebar:hover .toggle-btn {
  opacity: 1;
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #121212;
  position: relative;
}

.top-nav {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
}

.app-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: #9ca3af;
  cursor: pointer;
}

.share-btn {
  background-color: transparent;
  border: 1px solid #424242;
  color: #ececec;
  padding: 0.4rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  cursor: pointer;
}

.menu-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: #9ca3af;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 2rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.result-view {
  width: 100%;
  max-width: 800px;
}

.result-header {
  margin-bottom: 2rem;
}

.result-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.result-title {
  font-size: 1.8rem;
  font-weight: 600;
  color: #ececec;
  flex: 1;
}

.copy-btn-top {
  background-color: #2a2a2a;
  color: #ececec;
  border: 1px solid #424242;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s;
  white-space: nowrap;
}

.copy-btn-top:hover {
  background-color: #3f3f3f;
}

.copy-btn-top.success {
  background-color: #10b981;
  color: white;
  border-color: #10b981;
}

.copy-btn-top .icon {
  font-size: 1rem;
}

.source-link {
  color: #10b981;
  text-decoration: none;
  font-size: 0.875rem;
}

.result-meta {
  display: flex;
  align-items: center;
}

.summary-content {
  background-color: #1a1a1a;
  padding: 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid #2a2a2a;
}

.summary-text {
  font-size: 1rem;
  line-height: 1.6;
  color: #ececec;
  white-space: pre-wrap;
}

.welcome-view {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #9ca3af;
}

.hero h2 {
  font-size: 1.5rem;
  color: #ececec;
  margin-bottom: 0.5rem;
}

.branding {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.logo {
  width: 48px;
  height: 48px;
}

.brand-name {
  font-family: serif;
  font-size: 3.5rem;
  color: #ffffff;
  margin: 0;
  font-weight: 400;
}

.quote {
  font-family: monospace;
  font-size: 1.25rem;
  color: #6b7280;
  margin-bottom: 2rem;
}

.error-msg {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
  padding: 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  width: 100%;
  max-width: 800px;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.loading-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin-top: 4rem;
}

.spinner {
  width: 30px;
  height: 30px;
  border: 3px solid #424242;
  border-top: 3px solid #10b981;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* Input Area */
.input-container {
  padding: 1rem 1rem 1.5rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.chat-input-wrapper {
  width: 100%;
  max-width: 800px;
  background-color: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 1rem;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  transition: border-color 0.2s;
}

.chat-input-wrapper:focus-within {
  border-color: #10b981;
}

.chat-input {
  background: transparent;
  border: none;
  color: #ececec;
  font-size: 1rem;
  width: 100%;
  outline: none;
  padding: 0.5rem 0;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-select {
  background: #2a2a2a;
  border: 1px solid #424242;
  border-radius: 2rem;
  color: #9ca3af;
  font-size: 0.875rem;
  cursor: pointer;
  outline: none;
  padding: 0.25rem 2rem 0.25rem 0.75rem;
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.5rem center;
  background-size: 1em;
}

.model-select option {
  background-color: #2f2f2f;
  color: #ececec;
}

.send-btn {
  width: 32px;
  height: 32px;
  background-color: #10b981;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  font-weight: bold;
}

.send-btn:disabled {
  background-color: #424242;
  color: #9ca3af;
  cursor: not-allowed;
}

.disclaimer {
  font-size: 0.75rem;
  color: #9ca3af;
}

.spinner-small {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.center-input-wrapper {
  margin-top: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  width: 100%;
  max-width: 500px;
}

.center-input {
  width: 100%;
  padding: 1rem 1.5rem;
  background-color: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 0.75rem;
  color: #ececec;
  font-size: 1rem;
  outline: none;
  transition: border-color 0.2s;
}

.center-input:focus {
  border-color: #10b981;
}

.center-start-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  background-color: #10b981;
  color: white;
  border: none;
  border-radius: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.center-start-btn:hover {
  background-color: #059669;
}

.center-start-btn:disabled {
  background-color: #2a2a2a;
  color: #666;
  cursor: not-allowed;
}

.center-actions {
  display: flex;
  gap: 1rem;
  width: 100%;
}

.center-model-select {
  flex: 1;
  background-color: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 2rem;
  color: #ececec;
  padding: 0.75rem 1.25rem;
  font-size: 1rem;
  outline: none;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 1rem center;
  background-size: 1em;
}

.center-model-select:focus {
  border-color: #10b981;
}

.center-model-select option {
  background-color: #2f2f2f;
  color: #ececec;
}
</style>
