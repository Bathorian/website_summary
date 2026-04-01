<script setup lang="ts">
import { ref, onMounted } from 'vue'

const url = ref('')
const loading = ref(false)
const result = ref<any>(null)
const error = ref<string | null>(null)
const history = ref<any[]>([])

const API_BASE = 'http://localhost:8000/api'

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
      body: JSON.stringify({ url: url.value })
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

onMounted(fetchHistory)
</script>

<template>
  <div class="container">
    <header>
      <h1>Website Summarizer</h1>
    </header>

    <main>
      <div class="input-group">
        <input 
          v-model="url" 
          type="url" 
          placeholder="https://example.com" 
          @keyup.enter="summarize"
          :disabled="loading"
        />
        <button @click="summarize" :disabled="loading || !url">
          {{ loading ? 'Summarizing...' : 'Summarize' }}
        </button>
      </div>

      <div v-if="error" class="error">
        {{ error }}
      </div>

      <div v-if="result" class="result">
        <h2>{{ result.title || 'Summary' }}</h2>
        <p class="url-meta">{{ result.url }}</p>
        <div class="summary-text">{{ result.summary }}</div>
      </div>

      <hr v-if="history.length > 0" />

      <div v-if="history.length > 0" class="history">
        <h3>Recent Summaries</h3>
        <ul>
          <li v-for="item in history" :key="item.id" @click="url = item.url; summarize()">
            <strong>{{ item.title || item.url }}</strong>
            <span class="date">{{ new Date(item.created_at).toLocaleDateString() }}</span>
          </li>
        </ul>
      </div>
    </main>
  </div>
</template>

<style scoped>
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  font-family: sans-serif;
}

header {
  text-align: center;
  margin-bottom: 2rem;
}

.input-group {
  display: flex;
  gap: 10px;
  margin-bottom: 1rem;
}

input {
  flex: 1;
  padding: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 16px;
}

button {
  padding: 12px 24px;
  background-color: #42b883;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

button:disabled {
  background-color: #a8dcc3;
  cursor: not-allowed;
}

.error {
  color: #e74c3c;
  background: #fdf2f2;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.result {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  border-left: 4px solid #42b883;
  margin-bottom: 2rem;
}

.url-meta {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.summary-text {
  line-height: 1.6;
  white-space: pre-wrap;
}

.history {
  margin-top: 2rem;
}

.history ul {
  list-style: none;
  padding: 0;
}

.history li {
  padding: 10px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  cursor: pointer;
}

.history li:hover {
  background: #f0fdf4;
}

.date {
  color: #999;
  font-size: 0.8rem;
}

hr {
  margin: 2rem 0;
  border: 0;
  border-top: 1px solid #eee;
}
</style>
