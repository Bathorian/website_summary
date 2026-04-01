import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export async function summarizeURL(url, model = 'openai/gpt-4o-mini', forceRefresh = false) {
  const { data } = await http.post('/summarize', {
    url,
    model,
    force_refresh: forceRefresh,
  })
  return data
}

export async function listSummaries() {
  const { data } = await http.get('/summaries')
  return data.summaries ?? []
}

export async function deleteSummary(id) {
  await http.delete(`/summaries/${id}`)
}
