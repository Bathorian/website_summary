<template>
  <div class="app">
    <header class="app-header">
      <div class="logo">
        <span class="logo-icon">⬡</span>
        <span class="logo-text">Distill</span>
      </div>
      <p class="tagline">Drop a URL. Get the essence.</p>
    </header>

    <main class="app-main">
      <UrlSummarizer />
    </main>
  </div>
</template>

<script setup>
import UrlSummarizer from './components/UrlSummarizer.vue'
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Mono:wght@300;400&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:       #0c0c0d;
  --surface:  #141416;
  --border:   #242428;
  --accent:   #c8f135;
  --accent-d: #a8d020;
  --text:     #e8e8ea;
  --muted:    #6b6b72;
  --danger:   #ff5f5f;
  --radius:   6px;
}

html, body {
  background: var(--bg);
  color: var(--text);
  font-family: 'DM Mono', monospace;
  font-size: 14px;
  line-height: 1.6;
  min-height: 100dvh;
}

.app {
  max-width: 780px;
  margin: 0 auto;
  padding: 0 20px 80px;
}

.app-header {
  padding: 60px 0 48px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 48px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.logo-icon {
  font-size: 22px;
  color: var(--accent);
}

.logo-text {
  font-family: 'Instrument Serif', serif;
  font-size: 28px;
  letter-spacing: -0.5px;
  color: var(--text);
}

.tagline {
  color: var(--muted);
  font-size: 13px;
  letter-spacing: 0.02em;
}
</style>
