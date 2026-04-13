<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useAuth, SignInButton, UserButton, UserProfile, useClerk, useSession, useUser } from '@clerk/vue'



const url = ref('')
const selectedModel = ref('google/gemini-2.5-flash')
const loading = ref(false)
const result = ref<any>(null)
const error = ref<string | null>(null)
const history = ref<any[]>([])
const sidebarCollapsed = ref(false)
const isMobile = ref(false)
const showProfile = ref(false)

const auth = useAuth()
const clerk = useClerk()
const { session } = useSession()
const { user } = useUser()

const getAuthToken = async () => {
  try {
    const a = auth as any
    if (a.getToken && typeof a.getToken === 'function') {
      return await a.getToken()
    }
  } catch (e) {
    console.warn('auth.getToken failed', e)
  }
  
  if (session.value && typeof session.value.getToken === 'function') {
    return await session.value.getToken()
  }
  console.error('Authentication not fully ready (getToken not found)')
  return null
}

async function handleSignOut() {
  if (confirm('Are you sure you want to sign out?')) {
    const c = clerk as any
    if (c.value?.signOut) {
      await c.value.signOut()
    } else if (c.signOut) {
      await c.signOut()
    }
  }
}

const { isSignedIn, isLoaded } = auth

watch(isLoaded, (newVal) => {
  console.log('Clerk Loaded:', newVal)
  console.log('getToken type:', typeof auth.getToken)
})

watch(isSignedIn, (newVal) => {
  console.log('User Signed In:', newVal)
  console.log('getToken type (isSignedIn):', typeof auth.getToken)
})

const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
  if (isMobile.value) {
    sidebarCollapsed.value = true
  }
}

const MODELS = [
  { id: 'anthropic/claude-sonnet-4.5', name: 'Claude 4.5 Sonnet' },
  { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini' },
  { id: 'google/gemini-2.5-flash', name: 'Gemini 2.5 Flash' },
]

const API_BASE = 'http://localhost:8000/api'
const VERSION = 'v-2026-04-11-23-15'

async function fetchHistory() {
  if (!isLoaded.value || !isSignedIn.value) {
    history.value = []
    return
  }
  try {
    const token = await getAuthToken()
    if (!token) return
    const res = await fetch(`${API_BASE}/summaries`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
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
  if (!isSignedIn.value) {
    error.value = 'Please sign in to summarize websites.'
    return
  }
  if (isMobile.value) {
    sidebarCollapsed.value = true
  }
  loading.value = true
  error.value = null
  result.value = null

  try {
    console.log('Summarize started for URL:', url.value)
    const token = await getAuthToken()
    if (!token) {
      throw new Error('Authentication not ready. Please try again.')
    }
    console.log('Token acquired')
    const res = await fetch(`${API_BASE}/summarize`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        url: url.value,
        model: selectedModel.value,
        force_refresh: true
      })
    })

    if (!res.ok) {
      const errData = await res.json()
      console.error('Summarize API error:', errData)
      throw new Error(errData.detail || 'Failed to summarize')
    }

    const data = await res.json()
    console.log('Summarize success:', data)
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
  if (isMobile.value) {
    sidebarCollapsed.value = true
  }
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
    const token = await getAuthToken()
    if (!token) {
      throw new Error('Authentication not ready.')
    }
    const res = await fetch(`${API_BASE}/summaries/${id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
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

onMounted(() => {
  if (isLoaded.value && isSignedIn.value) {
    fetchHistory()
  }
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

watch(isSignedIn, (newVal) => {
  if (newVal) {
    fetchHistory()
  } else {
    history.value = []
    result.value = null
  }
})


</script>

<template>
  <div v-if="!isLoaded" class="loading-overlay">
    <div class="spinner"></div>
    <p>Loading session...</p>
    <p style="font-size: 0.8rem; margin-top: 1rem; color: #666;">
      If this takes too long, check your Clerk publishable key and internet connection.
    </p>
  </div>
  <div v-else :id="VERSION" class="app-layout" :class="{ 'sidebar-hidden': sidebarCollapsed }">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="sidebar-top-row">
          <div v-if="!sidebarCollapsed" class="sidebar-title">Distill</div>
          <button @click="sidebarCollapsed = !sidebarCollapsed" class="inner-toggle-btn" :title="sidebarCollapsed ? 'Expand' : 'Collapse'">
            <svg v-if="!sidebarCollapsed" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="3" x2="9" y2="21"></line></svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><polyline points="9 12 15 12 15 21"></polyline></svg>
          </button>
        </div>
        
        <button @click="startNew" class="menu-action-btn new-chat" :class="{ 'collapsed': sidebarCollapsed }" title="New Summary">
          <span class="icon">+</span> <span v-if="!sidebarCollapsed">New summary</span>
        </button>
      </div>

      <div class="sidebar-content">
        <div class="history-label" v-if="!sidebarCollapsed">Recents</div>
        <div v-if="history.length > 0" class="history-list">
          <div
            v-for="item in history"
            :key="item.id"
            class="history-item"
            :class="{ active: result?.id === item.id, 'collapsed': sidebarCollapsed }"
            @click="selectHistoryItem(item)"
          >
            <div class="item-title" v-if="!sidebarCollapsed">{{ item.title || 'Untitled' }}</div>
            <div class="item-dot" v-else>•</div>
            <button v-if="!sidebarCollapsed" @click="deleteSummary(item.id, $event)" class="delete-btn" title="Delete">×</button>
          </div>
        </div>
        <div v-else-if="!sidebarCollapsed" class="empty-history">No history yet</div>
      </div>

      <div class="sidebar-footer" :class="{ 'collapsed': sidebarCollapsed }">
        <div v-if="isSignedIn" class="user-profile-wrapper">
          <div class="user-profile-clickable" title="Sign Out" @click="handleSignOut">
            <UserButton after-sign-out-url="/" @click.stop />
            <div class="user-info" v-if="!sidebarCollapsed">
              <div class="user-name">{{ user?.firstName || user?.username || 'User' }}</div>
              <div class="user-plan">Free plan</div>
            </div>
            <div class="sign-out-icon" v-if="!sidebarCollapsed">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
            </div>
          </div>
        </div>
        <div v-else class="user-profile">
           <SignInButton mode="modal">
             <button class="menu-action-btn sign-in-btn">
               <span class="icon">👤</span> <span v-if="!sidebarCollapsed">Sign In</span>
             </button>
           </SignInButton>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <header class="top-nav">

      </header>

      <div class="content-area">
        <div v-if="error" class="error-msg">
          {{ error }}
        </div>

        <template v-if="!isSignedIn">
          <div class="welcome-view">
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
              <p style="margin-bottom: 2rem; color: #9ca3af;">Please sign in to start summarizing websites.</p>
              <SignInButton mode="modal">
                <button class="center-start-btn">Sign In to Get Started</button>
              </SignInButton>
            </div>
          </div>
        </template>

        <template v-else>
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
            <div class="result-actions">This summary is editable
            </div>
          </div>
          <div class="summary-content">
            <textarea 
              class="summary-textarea" 
              v-model="result.summary"
              rows="25"
              placeholder="Edit the summary here..."
            ></textarea>
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
      </template>

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
      <div v-if="showProfile" class="profile-modal-overlay" @click.self="showProfile = false">
        <div class="profile-modal-content">
          <button class="close-profile-btn" @click="showProfile = false">×</button>
          <UserProfile />
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.loading-overlay {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: #121212;
  color: #e5e7eb;
}

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
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 100;
  border-right: 1px solid #1f1f1f;
  flex-shrink: 0;
}

.sidebar-hidden .sidebar {
  width: 68px;
}

.sidebar-hidden .sidebar-content {
  overflow: hidden;
}

.sidebar-header {
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.sidebar-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  min-height: 40px;
  padding: 0 0.25rem;
}

.sidebar-title {
  font-family: serif;
  font-size: 1.25rem;
  font-weight: 600;
  color: #fff;
}

.sidebar-hidden .sidebar-top-row {
  justify-content: center;
  padding: 0;
}

.menu-action-btn {
  width: 100%;
  padding: 0.6rem 0.75rem;
  background-color: transparent;
  color: #e5e7eb;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  transition: background-color 0.2s;
  white-space: nowrap;
  text-align: left;
}

.menu-action-btn.collapsed {
  justify-content: center;
  padding: 0.6rem 0;
  width: 40px;
  margin: 0 auto;
}

.menu-action-btn:hover {
  background-color: #202020;
}

.menu-action-btn.new-chat {
  margin-bottom: 0.25rem;
}

.menu-action-btn.new-chat .icon {
  font-size: 1.25rem;
  line-height: 1;
}

.inner-toggle-btn {
  background: transparent;
  border: none;
  border-radius: 0.4rem;
  color: #9ca3af;
  padding: 0.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.inner-toggle-btn:hover {
  background-color: #202020;
  color: #fff;
}


.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
  margin-top: 0.5rem;
}

.history-label {
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.history-item {
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  color: #ececec;
}

.history-item.collapsed {
  justify-content: center;
  padding: 0.5rem 0;
}

.item-dot {
  color: #4b5563;
  font-size: 1.5rem;
  line-height: 1;
}

.history-item:hover {
  background-color: #202020;
}

.history-item.active {
  background-color: #202020;
}

.item-title {
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.delete-btn {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0 0.25rem;
  line-height: 1;
  border-radius: 0.25rem;
  opacity: 0;
  transition: all 0.2s;
}

.history-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: #ef4444;
}

.sidebar-footer {
  padding: 0.75rem;
  border-top: 1px solid #1f1f1f;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.sidebar-footer.collapsed {
  align-items: center;
  padding: 0.75rem 0;
}

.user-profile,
.user-profile-clickable {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 0.5rem;
  width: 100%;
}

.user-profile:hover,
.user-profile-clickable:hover {
  background-color: #202020;
}

.user-profile-clickable:hover .sign-out-icon {
  color: #fff;
}

.sign-out-icon {
  color: #9ca3af;
  padding: 0.25rem;
  display: flex;
  align-items: center;
}

.user-avatar {
  width: 32px;
  height: 32px;
  background-color: #e5e7eb;
  color: #121212;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: #ececec;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-plan {
  font-size: 0.75rem;
  color: #9ca3af;
}

.footer-icons {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.footer-icon-btn {
  background: transparent;
  border: none;
  color: #9ca3af;
  padding: 0.25rem;
  cursor: pointer;
  font-size: 1.1rem;
  border-radius: 0.25rem;
}

.footer-icon-btn:hover {
  color: #fff;
  background-color: #333;
}

.download-icon-collapsed {
  font-size: 1.2rem;
  cursor: pointer;
  color: #9ca3af;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  margin-bottom: 0.5rem;
}

.download-icon-collapsed:hover {
  background-color: #202020;
  color: #fff;
}

/* Mobile Responsiveness */
@media (max-width: 768px) {
  .sidebar {
    position: absolute;
    height: 100%;
    transform: translateX(-100%);
    width: 280px;
  }

  .sidebar-hidden .sidebar {
    transform: translateX(-100%);
    width: 280px;
  }

  .app-layout:not(.sidebar-hidden) .sidebar {
    transform: translateX(0);
    box-shadow: 10px 0 30px rgba(0,0,0,0.5);
  }

  .main-content {
    width: 100vw;
  }

  .brand-name {
    font-size: 2.5rem;
  }

  .result-title {
    font-size: 1.4rem;
  }

  .result-title-row {
    flex-direction: column;
    align-items: stretch;
  }

  .copy-btn-top {
    justify-content: center;
  }

  .center-actions {
    flex-direction: column;
  }

  .input-container {
    padding-bottom: 2rem;
  }
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #121212;
  position: relative;
  min-width: 0;
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
  padding: 0.5rem;
  border-radius: 0.75rem;
  border: 1px solid #2a2a2a;
  display: flex;
}

.summary-textarea {
  width: 100%;
  min-height: 600px;
  background-color: transparent;
  border: none;
  color: #ececec;
  font-family: inherit;
  font-size: 1.1rem;
  line-height: 1.6;
  resize: vertical;
  padding: 1.5rem;
  outline: none;
  scrollbar-width: thin;
  scrollbar-color: #333 transparent;
}

.summary-textarea::-webkit-scrollbar {
  width: 6px;
}

.summary-textarea::-webkit-scrollbar-thumb {
  background-color: #333;
  border-radius: 10px;
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

.profile-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.profile-modal-content {
  background-color: #1a1a1a;
  border-radius: 1rem;
  padding: 1rem;
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  overflow: auto;
  border: 1px solid #333;
}

.close-profile-btn {
  position: absolute;
  top: 0.5rem;
  right: 1rem;
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 2rem;
  cursor: pointer;
  z-index: 2001;
  transition: color 0.2s;
}

.close-profile-btn:hover {
  color: #fff;
}
</style>
