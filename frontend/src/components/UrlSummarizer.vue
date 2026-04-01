<template>
  <div class="summarizer">

    <!-- Input form -->
    <div class="input-card">
      <label class="field-label">PASTE A URL</label>
      <div class="input-row">
        <input
          v-model="urlInput"
          type="url"
          class="url-input"
          placeholder="https://example.com/article"
          :disabled="loading"
          @keydown.enter="submit"
          spellcheck="false"
        />
        <button class="submit-btn" :disabled="loading || !urlInput.trim()" @click="submit">
          <span v-if="!loading">→</span>
          <span v-else class="spinner" />
        </button>
      </div>

      <div class="options-row">
        <div class="select-wrap">
          <label class="field-label small">MODEL</label>
          <select v-model="selectedModel" class="model-select" :disabled="loading">
            <option v-for="m in models" :key="m.id" :value="m.id">{{ m.label }}</option>
          </select>
        </div>
        <label class="checkbox-label">
          <input type="checkbox" v-model="forceRefresh" :disabled="loading" />
          <span>Skip cache</span>
        </label>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="error-bar">
      <span>⚠ {{ error }}</span>
      <button class="clear-btn" @click="error = null">✕</button>
    </div>

    <!-- Current result -->
    <transition name="fade-slide">
      <div v-if="currentResult" class="result-card">
        <div class="result-meta">
          <span class="badge" :class="{ cached: currentResult.cached }">
            {{ currentResult.cached ? 'CACHED' : 'FRESH' }}
          </span>
          <span class="result-model">{{ currentResult.summary.model }}</span>
          <a :href="currentResult.summary.url" target="_blank" rel="noopener" class="result-url">
            {{ truncateUrl(currentResult.summary.url) }} ↗
          </a>
        </div>

        <h2 v-if="currentResult.summary.title" class="result-title">
          {{ currentResult.summary.title }}
        </h2>

        <div class="result-body" v-html="parsedSummary" />

        <div class="result-footer">
          <span class="result-ts">{{ formatDate(currentResult.summary.created_at) }}</span>
        </div>
      </div>
    </transition>

    <!-- History -->
    <div v-if="history.length" class="history-section">
      <div class="section-header">
        <span class="field-label">RECENT SUMMARIES</span>
        <button class="refresh-btn" @click="loadHistory">↻</button>
      </div>

      <div class="history-list">
        <div
          v-for="item in history"
          :key="item.id"
          class="history-item"
          @click="openHistoryItem(item)"
        >
          <div class="history-meta">
            <span class="history-model">{{ item.model }}</span>
            <span class="history-ts">{{ formatDate(item.created_at) }}</span>
          </div>
          <div class="history-title">{{ item.title || item.url }}</div>
          <div class="history-url">{{ truncateUrl(item.url) }}</div>
          <button class="delete-btn" @click.stop="removeItem(item.id)" title="Delete">✕</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import { summarizeURL, listSummaries, deleteSummary } from '../api/client.js'

// ── State ────────────────────────────────────────────────────────────────────
const urlInput      = ref('')
const selectedModel = ref('openai/gpt-4o-mini')
const forceRefresh  = ref(false)
const loading       = ref(false)
const error         = ref(null)
const currentResult = ref(null)
const history       = ref([])

const models = [
  { id: 'openai/gpt-4o-mini',          label: 'GPT-4o Mini'      },
  { id: 'openai/gpt-4o',               label: 'GPT-4o'           },
  { id: 'anthropic/claude-3-haiku',     label: 'Claude 3 Haiku'   },
  { id: 'anthropic/claude-3.5-sonnet',  label: 'Claude 3.5 Sonnet'},
  { id: 'google/gemini-flash-1.5',      label: 'Gemini Flash 1.5' },
  { id: 'meta-llama/llama-3-8b-instruct', label: 'Llama 3 8B'    },
]

// ── Computed ─────────────────────────────────────────────────────────────────
const parsedSummary = computed(() => {
  if (!currentResult.value) return ''
  return marked.parse(currentResult.value.summary.summary)
})

// ── Methods ──────────────────────────────────────────────────────────────────
async function submit() {
  const url = urlInput.value.trim()
  if (!url || loading.value) return

  loading.value = true
  error.value   = null

  try {
    const result = await summarizeURL(url, selectedModel.value, forceRefresh.value)
    currentResult.value = result
    await loadHistory()
  } catch (err) {
    error.value = err.response?.data?.message ?? err.message ?? 'Something went wrong.'
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  try {
    history.value = await listSummaries()
  } catch {
    // silently fail for history
  }
}

async function removeItem(id) {
  try {
    await deleteSummary(id)
    history.value = history.value.filter(h => h.id !== id)
    if (currentResult.value?.summary?.id === id) currentResult.value = null
  } catch (err) {
    error.value = 'Failed to delete.'
  }
}

function openHistoryItem(item) {
  currentResult.value = { summary: item, cached: true }
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function truncateUrl(url) {
  try {
    const u = new URL(url)
    const path = u.pathname.length > 30
      ? u.pathname.slice(0, 30) + '…'
      : u.pathname
    return u.hostname + path
  } catch {
    return url.slice(0, 50)
  }
}

function formatDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

onMounted(loadHistory)
</script>

<style scoped>
.summarizer { display: flex; flex-direction: column; gap: 28px; }

/* ── Input card ── */
.input-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
}

.field-label {
  display: block;
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--muted);
  margin-bottom: 8px;
}
.field-label.small { font-size: 9px; }

.input-row { display: flex; gap: 8px; margin-bottom: 16px; }

.url-input {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-family: 'DM Mono', monospace;
  font-size: 13px;
  padding: 10px 14px;
  outline: none;
  transition: border-color 0.15s;
}
.url-input:focus { border-color: var(--accent); }
.url-input::placeholder { color: var(--muted); }

.submit-btn {
  background: var(--accent);
  border: none;
  border-radius: var(--radius);
  color: #0c0c0d;
  cursor: pointer;
  font-size: 18px;
  font-weight: 600;
  padding: 0 20px;
  transition: background 0.15s, transform 0.1s;
  display: flex; align-items: center; justify-content: center;
  min-width: 52px;
}
.submit-btn:hover:not(:disabled) { background: var(--accent-d); }
.submit-btn:active:not(:disabled) { transform: scale(0.96); }
.submit-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(0,0,0,0.3);
  border-top-color: #000;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }

.options-row {
  display: flex;
  align-items: flex-end;
  gap: 20px;
}

.select-wrap { display: flex; flex-direction: column; }

.model-select {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-family: 'DM Mono', monospace;
  font-size: 12px;
  padding: 7px 10px;
  cursor: pointer;
  outline: none;
}
.model-select:focus { border-color: var(--accent); }

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
  padding-bottom: 8px;
}
.checkbox-label input[type=checkbox] { accent-color: var(--accent); }

/* ── Error ── */
.error-bar {
  background: rgba(255, 95, 95, 0.1);
  border: 1px solid var(--danger);
  border-radius: var(--radius);
  color: var(--danger);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  padding: 12px 16px;
}
.clear-btn {
  background: none; border: none; color: var(--danger);
  cursor: pointer; font-size: 14px;
}

/* ── Result card ── */
.result-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 28px;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.badge {
  font-size: 9px;
  letter-spacing: 0.1em;
  background: var(--accent);
  color: #0c0c0d;
  padding: 2px 7px;
  border-radius: 3px;
  font-weight: 600;
}
.badge.cached { background: var(--border); color: var(--muted); }

.result-model { font-size: 11px; color: var(--muted); }

.result-url {
  font-size: 11px;
  color: var(--muted);
  text-decoration: none;
  margin-left: auto;
  transition: color 0.15s;
}
.result-url:hover { color: var(--accent); }

.result-title {
  font-family: 'Instrument Serif', serif;
  font-size: 22px;
  font-weight: 400;
  line-height: 1.3;
  margin-bottom: 20px;
  letter-spacing: -0.3px;
}

.result-body :deep(p)  { margin-bottom: 12px; font-size: 13px; line-height: 1.7; }
.result-body :deep(ul) { margin: 0 0 12px 18px; }
.result-body :deep(li) { font-size: 13px; line-height: 1.7; margin-bottom: 4px; }
.result-body :deep(strong) { color: var(--text); font-weight: 600; }

.result-footer { margin-top: 20px; border-top: 1px solid var(--border); padding-top: 12px; }
.result-ts { font-size: 11px; color: var(--muted); }

/* ── History ── */
.history-section { margin-top: 8px; }

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.refresh-btn {
  background: none; border: none; color: var(--muted);
  cursor: pointer; font-size: 16px;
  transition: color 0.15s;
}
.refresh-btn:hover { color: var(--text); }

.history-list { display: flex; flex-direction: column; gap: 1px; }

.history-item {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.history-item:hover { border-color: var(--accent); }

.history-meta {
  display: flex;
  gap: 10px;
  margin-bottom: 4px;
}
.history-model { font-size: 10px; color: var(--muted); }
.history-ts    { font-size: 10px; color: var(--muted); margin-left: auto; }

.history-title {
  font-family: 'Instrument Serif', serif;
  font-size: 15px;
  margin-bottom: 2px;
  padding-right: 28px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.history-url { font-size: 11px; color: var(--muted); }

.delete-btn {
  position: absolute; top: 14px; right: 14px;
  background: none; border: none; color: var(--muted);
  cursor: pointer; font-size: 12px;
  transition: color 0.15s;
}
.delete-btn:hover { color: var(--danger); }

/* ── Transitions ── */
.fade-slide-enter-active { transition: all 0.3s ease; }
.fade-slide-enter-from   { opacity: 0; transform: translateY(10px); }
</style>
