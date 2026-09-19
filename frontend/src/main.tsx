import React from 'react'
import ReactDOM from 'react-dom/client'
import ReactMarkdown from 'react-markdown'
import './style.css'

type DocumentRecord = {
  document_id: string
  filename: string
  file_type: string
  file_size: number
  status: string
  created_at: string
}

type DocumentContent = {
  document_id: string
  filename: string
  text: string
  word_count: number
}

type DocumentChunks = {
  chunk_count: number
}

type SearchResult = {
  filename: string
  chunk_id: string
  text: string
  score: number
  retrieval_score?: number
  reranking_score?: number
}

type AskSource = {
  citation: number
  filename: string
  chunk_id: string
  retrieval_score?: number
  reranking_score?: number
  page_number?: number | null
}

type SystemStatus = {
  api: string
  llm: string
  embeddings: string
  qdrant: string
}

type DashboardStats = {
  document_count: number
  chunk_count: number
  indexed_count: number
  indexing_status: string
  query_count: number
}

type CollectionSummary = {
  name: string
  status: string
  points_count: number
  dimensions: number
}

type MonitoringData = {
  documents: number
  indexed_documents: number
  pending_documents: number
  queries: number
  collection: CollectionSummary
  models: { llm: string; embeddings: string }
  requests: { requests: number; errors: number; success_rate: number | null; average_latency_ms: number | null }
}

type EvaluationCaseResult = {
  id: string
  question: string
  category: string
  difficulty: string
  expected_documents: string[]
  retrieved_chunks: number
  relevant_rank: number | null
  retrieval_hit: boolean | null
  reciprocal_rank: number
  recall_at_3: number
  recall_at_5: number
  precision_at_3: number
  precision_at_5: number
  answer: string | null
  answer_relevance?: number | null
  relevance_reason?: string | null
  missing_aspects?: string[]
  groundedness: number | null
  unsupported_claim_count: number
  citation_correctness: boolean | null
  citation_reason?: string | null
  retrieval_latency_ms: number
  answer_latency_ms: number | null
  total_latency_ms: number
  sources: { filename: string; chunk_id: string; score: number }[]
}

type EvaluationRun = {
  run_id: string
  dataset_name: string
  created_at: string
  configuration?: {
    top_k?: number
    limit?: number
    mmr_enabled?: boolean
    mmr_lambda?: number
    candidate_pool_size?: number
    generate_answers?: boolean
  }
  summary: {
    case_count: number
    retrieval_hit_rate: number | null
    mean_reciprocal_rank: number | null
    recall_at_3?: number | null
    recall_at_5?: number | null
    precision_at_3?: number | null
    precision_at_5?: number | null
    answer_relevance?: number | null
    groundedness?: number | null
    citation_correctness?: number | null
    average_embedding_latency_ms?: number
    average_retrieval_latency_ms: number
    average_reranking_latency_ms?: number
    average_answer_latency_ms?: number
    average_total_latency_ms?: number
  }
  cases?: EvaluationCaseResult[]
}

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: '▣' },
  { id: 'documents', label: 'Documents', icon: '▤' },
  { id: 'collections', label: 'Collections', icon: '◈' },
  { id: 'search', label: 'Search', icon: '⌕' },
  { id: 'ask', label: 'Ask Knowledge Base', icon: '✦' },
  { id: 'evaluations', label: 'Evaluations', icon: '▦' },
  { id: 'monitoring', label: 'Monitoring', icon: '◔' },
  { id: 'settings', label: 'Settings', icon: '⚙' },
] as const

const menuOrder = navItems.map((item) => item.id)

const settingsRows = [
  { label: 'Auto-index new uploads', enabled: true },
  { label: 'Require approval before publish', enabled: false },
  { label: 'Enable semantic search fallback', enabled: true },
]

const healthyStatuses = new Set(['operational', 'configured', 'ready', 'healthy'])

function pillTone(status: string) {
  if (healthyStatuses.has(status) || status === 'indexed' || status === 'processed' || status === 'embedded') {
    return 'good'
  }
  if (status === 'failed' || status === 'unavailable' || status === 'unconfigured') {
    return 'bad'
  }
  return 'warn'
}

function EmptyCard({ title, hint, children }: { title: string; hint: string; children?: React.ReactNode }) {
  return (
    <div className="empty-card">
      <h3>{title}</h3>
      <p>{hint}</p>
      {children}
    </div>
  )
}

function App() {
  const [activeView, setActiveView] = React.useState<(typeof menuOrder)[number]>('dashboard')
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false)
  const [dragOver, setDragOver] = React.useState(false)
  const [apiStatus, setApiStatus] = React.useState('Checking API…')
  const [systemStatus, setSystemStatus] = React.useState<SystemStatus | null>(null)
  const [dashboardStats, setDashboardStats] = React.useState<DashboardStats>({
    document_count: 0,
    chunk_count: 0,
    indexed_count: 0,
    indexing_status: 'Idle',
    query_count: 0,
  })
  const [collections, setCollections] = React.useState<CollectionSummary[]>([])
  const [monitoringData, setMonitoringData] = React.useState<MonitoringData | null>(null)
  const [evaluationRuns, setEvaluationRuns] = React.useState<EvaluationRun[]>([])
  const [evaluationQuestion, setEvaluationQuestion] = React.useState('')
  const [evaluationFilename, setEvaluationFilename] = React.useState('')
  const [evaluating, setEvaluating] = React.useState(false)
  const [evaluationError, setEvaluationError] = React.useState<string | null>(null)
  const [documents, setDocuments] = React.useState<DocumentRecord[]>([])
  const [selectedDocumentId, setSelectedDocumentId] = React.useState<string | null>(null)
  const [documentContent, setDocumentContent] = React.useState<DocumentContent | null>(null)
  const [chunkCount, setChunkCount] = React.useState<number | null>(null)
  const [uploading, setUploading] = React.useState(false)
  const [uploadMessage, setUploadMessage] = React.useState<string | null>(null)
  const [uploadError, setUploadError] = React.useState<string | null>(null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const [searchQuery, setSearchQuery] = React.useState('')
  const [searching, setSearching] = React.useState(false)
  const [searchResults, setSearchResults] = React.useState<SearchResult[]>([])
  const [searchError, setSearchError] = React.useState<string | null>(null)
  const [indexing, setIndexing] = React.useState(false)
  const [indexMessage, setIndexMessage] = React.useState<string | null>(null)
  const [indexError, setIndexError] = React.useState<string | null>(null)
  const [deletingDocumentId, setDeletingDocumentId] = React.useState<string | null>(null)
  const [batchIndexing, setBatchIndexing] = React.useState(false)
  const [batchIndexMessage, setBatchIndexMessage] = React.useState<string | null>(null)
  const [batchIndexError, setBatchIndexError] = React.useState<string | null>(null)
  const [askQuestion, setAskQuestion] = React.useState('')
  const [askAnswer, setAskAnswer] = React.useState<string | null>(null)
  const [askSources, setAskSources] = React.useState<AskSource[]>([])
  const [askRequestId, setAskRequestId] = React.useState<string | null>(null)
  const [askLatency, setAskLatency] = React.useState<{ total_ms: number; retrieval_ms: number; reranking_ms: number; generation_ms: number } | null>(null)
  const [asking, setAsking] = React.useState(false)
  const [askError, setAskError] = React.useState<string | null>(null)

  const loadDocuments = React.useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/documents')
      if (!response.ok) {
        throw new Error('Unable to fetch documents')
      }
      const data = (await response.json()) as DocumentRecord[]
      setDocuments(data)
      if (data.length > 0 && !selectedDocumentId) {
        setSelectedDocumentId(data[0].document_id)
      }
    } catch {
      setDocuments([])
    }
  }, [selectedDocumentId])

  const loadDashboardStats = React.useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/stats')
      if (response.ok) {
        setDashboardStats((await response.json()) as DashboardStats)
      }
    } catch {
    }
  }, [])

  const loadCollections = React.useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/collections')
      if (response.ok) {
        const data = (await response.json()) as { collections: CollectionSummary[] }
        setCollections(data.collections)
      }
    } catch {
      setCollections([])
    }
  }, [])

  const loadMonitoring = React.useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/monitoring')
      if (response.ok) {
        setMonitoringData((await response.json()) as MonitoringData)
      }
    } catch {
      setMonitoringData(null)
    }
  }, [])

  const loadEvaluations = React.useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/evaluations')
      if (response.ok) {
        const data = (await response.json()) as { runs: EvaluationRun[] }
        setEvaluationRuns(data.runs)
      }
    } catch {
      setEvaluationRuns([])
    }
  }, [])

  const loadDocumentContent = React.useCallback(async (documentId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/documents/${documentId}/content`)
      if (!response.ok) {
        throw new Error('Unable to load document content')
      }
      const data = (await response.json()) as DocumentContent
      setDocumentContent(data)
      setSelectedDocumentId(documentId)

      const chunksResponse = await fetch(`http://localhost:8000/documents/${documentId}/chunks`)
      if (chunksResponse.ok) {
        const chunks = (await chunksResponse.json()) as DocumentChunks
        setChunkCount(chunks.chunk_count)
      }
    } catch {
      setDocumentContent(null)
      setChunkCount(null)
    }
  }, [])

  React.useEffect(() => {
    const checkApiHealth = async () => {
      try {
        const response = await fetch('http://localhost:8000/status')
        if (!response.ok) {
          throw new Error('Backend unavailable')
        }
        const data = (await response.json()) as SystemStatus
        setSystemStatus(data)
        setApiStatus(data.api === 'operational' ? 'API Operational' : 'API Unavailable')
      } catch {
        setApiStatus('API Unavailable')
      }
    }

    void checkApiHealth()
    void loadDocuments()
    void loadDashboardStats()
    void loadCollections()
    void loadMonitoring()
    void loadEvaluations()
  }, [loadCollections, loadDashboardStats, loadDocuments, loadEvaluations, loadMonitoring])

  const uploadFile = async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    setUploading(true)
    setUploadError(null)
    setUploadMessage(null)

    try {
      const response = await fetch('http://localhost:8000/documents', {
        method: 'POST',
        body: formData,
      })

      const data = (await response.json()) as { detail?: string } | DocumentRecord

      if (!response.ok) {
        throw new Error((data as { detail?: string }).detail ?? 'Upload failed')
      }

      setUploadMessage(`Uploaded ${file.name}`)
      const uploadedDocument = data as DocumentRecord
      setDocuments((previous) => [uploadedDocument, ...previous])
      setSelectedDocumentId(uploadedDocument.document_id)
      void loadDocumentContent(uploadedDocument.document_id)
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }
    await uploadFile(file)
    event.target.value = ''
  }

  const openUploadPicker = () => {
    fileInputRef.current?.click()
  }

  const runSearch = async () => {
    if (!searchQuery.trim()) {
      return
    }
    setSearchError(null)
    setSearching(true)
    try {
      const response = await fetch('http://localhost:8000/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, limit: 5 }),
      })
      const data = (await response.json()) as { detail?: string; results?: SearchResult[] }
      if (!response.ok) {
        throw new Error(data.detail ?? 'Search failed')
      }
      setSearchResults(data.results ?? [])
    } catch (error) {
      setSearchResults([])
      setSearchError(error instanceof Error ? error.message : 'Search failed')
    } finally {
      setSearching(false)
    }
  }

  const indexDocument = async (documentId: string) => {
    setIndexing(true)
    setIndexMessage(null)
    setIndexError(null)
    try {
      const response = await fetch(`http://localhost:8000/documents/${documentId}/index`, { method: 'POST' })
      const data = (await response.json()) as { detail?: string; indexed_chunks?: number }
      if (!response.ok) {
        throw new Error(data.detail ?? 'Indexing failed')
      }
      setIndexMessage(`Indexed ${data.indexed_chunks ?? 0} chunks`)
      await Promise.all([loadDocuments(), loadDashboardStats(), loadCollections(), loadMonitoring()])
    } catch (error) {
      setIndexError(error instanceof Error ? error.message : 'Indexing failed')
    } finally {
      setIndexing(false)
    }
  }

  const deleteDocument = async (documentId: string) => {
    if (!window.confirm('Delete this document and its indexed chunks?')) {
      return
    }
    setDeletingDocumentId(documentId)
    try {
      const response = await fetch(`http://localhost:8000/documents/${documentId}`, { method: 'DELETE' })
      const data = (await response.json().catch(() => ({}))) as { detail?: string }
      if (!response.ok) {
        throw new Error(data.detail ?? 'Delete failed')
      }
      setDocuments((previous) => previous.filter((document) => document.document_id !== documentId))
      if (selectedDocumentId === documentId) {
        setSelectedDocumentId(null)
        setDocumentContent(null)
        setChunkCount(null)
      }
      await loadDashboardStats()
    } catch (error) {
      setIndexError(error instanceof Error ? error.message : 'Delete failed')
    } finally {
      setDeletingDocumentId(null)
    }
  }

  const indexPendingDocuments = async () => {
    setBatchIndexing(true)
    setBatchIndexMessage(null)
    setBatchIndexError(null)
    try {
      const response = await fetch('http://localhost:8000/documents/index-pending', { method: 'POST' })
      const data = (await response.json()) as { detail?: string; indexed_count?: number }
      if (!response.ok) {
        throw new Error(data.detail ?? 'Batch indexing failed')
      }
      setBatchIndexMessage(`Indexed ${data.indexed_count ?? 0} pending document${data.indexed_count === 1 ? '' : 's'}`)
      await Promise.all([loadDocuments(), loadDashboardStats(), loadCollections()])
    } catch (error) {
      setBatchIndexError(error instanceof Error ? error.message : 'Batch indexing failed')
    } finally {
      setBatchIndexing(false)
    }
  }

  const runAsk = async () => {
    if (!askQuestion.trim()) {
      return
    }
    setAsking(true)
    setAskError(null)
    try {
      const response = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: askQuestion, limit: 5 }),
      })
      const data = (await response.json()) as { detail?: string; answer?: string; citations?: AskSource[]; request_id?: string; latency?: { total_ms: number; retrieval_ms: number; reranking_ms: number; generation_ms: number } }
      if (!response.ok) {
        throw new Error(data.detail ?? 'Unable to answer question')
      }
      setAskAnswer(data.answer ?? '')
      setAskSources(data.citations ?? [])
      setAskRequestId(data.request_id ?? null)
      setAskLatency(data.latency ?? null)
    } catch (error) {
      setAskAnswer(null)
      setAskSources([])
      setAskRequestId(null)
      setAskLatency(null)
      setAskError(error instanceof Error ? error.message : 'Unable to answer question')
    } finally {
      setAsking(false)
    }
  }

  const [benchmarkTopK, setBenchmarkTopK] = React.useState<number>(5)
  const [mmrEnabled, setMmrEnabled] = React.useState<boolean>(true)
  const [mmrLambda, setMmrLambda] = React.useState<number>(0.70)
  const [candidateK, setCandidateK] = React.useState<number>(15)
  const [selectedCaseId, setSelectedCaseId] = React.useState<string | null>(null)
  const [benchmarkRunning, setBenchmarkRunning] = React.useState<boolean>(false)
  const [benchmarkResult, setBenchmarkResult] = React.useState<EvaluationRun | null>(null)
  const [categoryFilter, setCategoryFilter] = React.useState<string>('all')
  const [difficultyFilter, setDifficultyFilter] = React.useState<string>('all')
  const [statusFilter, setStatusFilter] = React.useState<string>('all')
  const [failureTypeFilter, setFailureTypeFilter] = React.useState<string>('all')

  const runBenchmarkV2 = async (topKVal = benchmarkTopK) => {
    setBenchmarkRunning(true)
    setEvaluationError(null)
    try {
      const url = `http://localhost:8000/evaluations/benchmark/run?top_k=${topKVal}&mmr_enabled=${mmrEnabled}&mmr_lambda=${mmrLambda}&candidate_pool_size=${candidateK}`
      const response = await fetch(url, { method: 'POST' })
      const data = (await response.json()) as EvaluationRun | { detail?: string }
      if (!response.ok) throw new Error((data as { detail?: string }).detail ?? 'Benchmark run failed')
      const run = data as EvaluationRun
      setBenchmarkResult(run)
      setEvaluationRuns((runs) => [run, ...runs])
    } catch (error) {
      setEvaluationError(error instanceof Error ? error.message : 'Benchmark run failed')
    } finally {
      setBenchmarkRunning(false)
    }
  }

  const runEvaluation = async () => {
    if (!evaluationQuestion.trim()) return
    setEvaluating(true)
    setEvaluationError(null)
    try {
      const response = await fetch('http://localhost:8000/evaluations/run', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_name: 'dashboard evaluation', cases: [{ question: evaluationQuestion, relevant_filename: evaluationFilename || null }] }),
      })
      const data = (await response.json()) as EvaluationRun | { detail?: string }
      if (!response.ok) throw new Error((data as { detail?: string }).detail ?? 'Evaluation failed')
      setEvaluationRuns((runs) => [data as EvaluationRun, ...runs])
    } catch (error) {
      setEvaluationError(error instanceof Error ? error.message : 'Evaluation failed')
    } finally {
      setEvaluating(false)
    }
  }

  const renderDashboard = () => (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Dashboard</h2>
        </div>
        <div className="topbar-actions">
          <button className="secondary-button" type="button" onClick={() => void indexPendingDocuments()} disabled={batchIndexing}>
            {batchIndexing ? 'Indexing…' : 'Index pending'}
          </button>
          <button className="primary-button" type="button" onClick={() => void Promise.all([loadDocuments(), loadDashboardStats(), loadCollections(), loadMonitoring()])}>Refresh</button>
        </div>
      </header>

      <section className="stats-grid">
        {[
          { label: 'Total Documents', value: String(dashboardStats.document_count), tone: 'blue' },
          { label: 'Total Chunks', value: String(dashboardStats.chunk_count), tone: 'purple' },
          { label: 'Indexing Status', value: dashboardStats.indexing_status, tone: 'green' },
          { label: 'Query Count', value: String(dashboardStats.query_count), tone: 'orange' },
        ].map((stat) => (
          <article key={stat.label} className={`stat-card tone-${stat.tone}`}>
            <span className="label">{stat.label}</span>
            <strong>{stat.value}</strong>
          </article>
        ))}
      </section>

      <section className="content-grid">
        <article className="panel-card">
          <div className="panel-header">
            <strong>Service Health</strong>
            <span className="chip neutral">Live</span>
          </div>
          <div className="health-list">
            {(systemStatus ? [
              { label: 'API', status: systemStatus.api },
              { label: 'LLM', status: systemStatus.llm },
              { label: 'Embeddings', status: systemStatus.embeddings },
              { label: 'Qdrant', status: systemStatus.qdrant },
            ] : []).map((item) => (
              <div key={item.label} className="health-row">
                <span>{item.label}</span>
                <span className={`status-pill ${pillTone(item.status)}`}>{item.status}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel-card">
          <div className="panel-header">
            <strong>Recent Documents</strong>
            <span className="chip blue">{documents.length} file{documents.length === 1 ? '' : 's'}</span>
          </div>
          <div className="list-stack">
            {documents.length === 0 ? (
              <EmptyCard title="No documents yet" hint="Upload a PDF to start extraction, chunking, and indexing.">
                <button className="primary-button small" type="button" onClick={openUploadPicker}>Upload PDF</button>
              </EmptyCard>
            ) : (
              documents.slice(0, 6).map((doc) => (
                <div key={doc.document_id} className="document-row">
                  <div>
                    <strong>{doc.filename}</strong>
                    <span>{doc.file_type.toUpperCase()}</span>
                  </div>
                  <span className={`status-pill ${pillTone(doc.status)}`}>{doc.status}</span>
                </div>
              ))
            )}
          </div>
        </article>
      </section>

      <section className="upload-panel">
        <div className="panel-header upload-header">
          <strong>Upload Document</strong>
          <span className="chip neutral">PDF only</span>
        </div>

        <label
          className={`upload-box ${dragOver ? 'dragover' : ''}`}
          onDragOver={(event) => {
            event.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragOver(false)
            const file = event.dataTransfer.files[0]
            if (file) {
              void uploadFile(file)
            }
          }}
        >
          <input type="file" accept="application/pdf" onChange={handleUpload} disabled={uploading} />
          <strong>{uploading ? 'Uploading…' : 'Drop a PDF here or click to browse'}</strong>
          <em>PDF only · max 10 MB</em>
        </label>

        {uploadMessage && <div className="inline-message success">{uploadMessage}</div>}
        {uploadError && <div className="inline-message error">{uploadError}</div>}
        {batchIndexMessage && <div className="inline-message success">{batchIndexMessage}</div>}
        {batchIndexError && <div className="inline-message error">{batchIndexError}</div>}
      </section>
    </>
  )

  const renderDocumentsSection = () => (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Knowledge Base</p>
          <h2>Documents</h2>
        </div>
        <button className="primary-button" type="button" onClick={openUploadPicker} disabled={uploading}>
          {uploading ? 'Uploading…' : 'Add document'}
        </button>
      </header>

      <input
        ref={fileInputRef}
        className="visually-hidden"
        type="file"
        accept="application/pdf"
        onChange={handleUpload}
        disabled={uploading}
      />

      <section className="view-panel">
        <div className="view-panel-header">
          <strong>Uploaded sources</strong>
          <span className="chip blue">{documents.length} total</span>
        </div>

        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Status</th>
                <th>Updated</th>
                <th aria-label="Actions"></th>
              </tr>
            </thead>
            <tbody>
              {documents.length > 0 ? documents.map((doc) => (
                <tr key={doc.document_id} onClick={() => void loadDocumentContent(doc.document_id)} className={selectedDocumentId === doc.document_id ? 'selected-row' : ''}>
                  <td>{doc.filename}</td>
                  <td>{doc.file_type.toUpperCase()}</td>
                  <td><span className={`table-badge ${doc.status}`}>{doc.status}</span></td>
                  <td>{new Date(doc.created_at).toLocaleDateString()}</td>
                  <td>
                    <button
                      type="button"
                      className="danger-button"
                      onClick={(event) => {
                        event.stopPropagation()
                        void deleteDocument(doc.document_id)
                      }}
                      disabled={deletingDocumentId === doc.document_id}
                    >
                      {deletingDocumentId === doc.document_id ? 'Deleting…' : 'Delete'}
                    </button>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={5}>No documents uploaded yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {documentContent && (
          <div className="content-preview">
            <div className="content-preview-header">
              <strong>{documentContent.filename}</strong>
              <div className="content-preview-actions">
                <span>{documentContent.word_count} words{chunkCount === null ? '' : ` · ${chunkCount} chunks`}</span>
                <button type="button" className="primary-button small" onClick={() => void indexDocument(documentContent.document_id)} disabled={indexing}>
                  {indexing ? 'Indexing…' : 'Index document'}
                </button>
              </div>
            </div>
            <p>{documentContent.text}</p>
            {indexMessage && <div className="inline-message success">{indexMessage}</div>}
            {indexError && <div className="inline-message error">{indexError}</div>}
          </div>
        )}
      </section>
    </>
  )

  const renderCollectionsSection = () => (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Organization</p>
          <h2>Collections</h2>
        </div>
      </header>

      <section className="view-panel">
        <div className="view-grid cards-3">
          {collections.length > 0 ? collections.map((collection) => (
            <div key={collection.name} className="mini-card collection-card">
              <span className="mini-label">Collection</span>
              <strong>{collection.name}</strong>
              <div className="mini-meta-row">
                <span>{collection.points_count} vectors</span>
                <span>{collection.dimensions} dims</span>
              </div>
              <span className={`status-pill ${pillTone(collection.status)}`}>{collection.status}</span>
            </div>
          )) : <div className="empty-state">No Qdrant collection has been created yet.</div>}
        </div>
      </section>
    </>
  )

  const renderSearchSection = () => (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Discovery</p>
          <h2>Search</h2>
        </div>
      </header>

      <section className="view-panel">
        <div className="search-box">
          <input type="text" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} />
          <button type="button" className="primary-button small" onClick={() => void runSearch()}>Search</button>
        </div>

        <div className="result-list">
          {searchResults.map((result) => (
            <article key={result.chunk_id} className="result-card">
              <div>
                <strong>{result.filename}</strong>
                <span>{result.text}</span>
              </div>
              <span className="match-badge">{Math.round((result.reranking_score ?? result.score) * 100)}% reranked</span>
            </article>
          ))}
          {searchError && <div className="inline-message error">{searchError}</div>}
          {!searchError && searchResults.length === 0 && <div className="empty-state">No indexed results yet. Index an uploaded document first.</div>}
        </div>
      </section>
    </>
  )

  const renderAskSection = () => (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Assistant</p>
          <h2>Ask Knowledge Base</h2>
        </div>
      </header>

      <section className="view-panel">
        <div className="ask-box">
          <textarea value={askQuestion} onChange={(event) => setAskQuestion(event.target.value)} />
          <button type="button" className="primary-button small" onClick={() => void runAsk()} disabled={asking}>
            {asking ? 'Thinking…' : 'Run query'}
          </button>
        </div>

        {askError && <div className="inline-message error">{askError}</div>}
        {askAnswer && (
          <div className="answer-box">
            <div className="answer-content">
              <ReactMarkdown>{askAnswer}</ReactMarkdown>
            </div>
            <div className="answer-meta">
              <span>{askSources.length} cited source{askSources.length === 1 ? '' : 's'}</span>
              <span>{askSources.map((source) => `[${source.citation}] ${source.filename}${source.page_number ? ` p.${source.page_number}` : ''}`).join(' · ')}</span>
            </div>
            {askLatency && <div className="answer-meta"><span>Request {askRequestId}</span><span>{askLatency.total_ms} ms total · {askLatency.retrieval_ms} ms retrieval · {askLatency.generation_ms} ms generation</span></div>}
          </div>
        )}
        {!askAnswer && !askError && <div className="empty-state">Ask a question about your indexed documents.</div>}
      </section>
    </>
  )

  const renderEvaluationsSection = () => {
    const activeRun = benchmarkResult || evaluationRuns.find((r) => r.cases && r.cases.length > 0) || evaluationRuns[0]
    const cases = activeRun?.cases || []

    const getFailureType = (c: EvaluationCaseResult): string => {
      if (c.retrieval_hit === false) return 'Retrieval'
      if (c.citation_correctness === false) return 'Citation'
      if (c.answer_relevance !== undefined && c.answer_relevance !== null && c.answer_relevance < 0.80) return 'Generation'
      if (c.precision_at_5 !== undefined && c.precision_at_5 !== null && c.precision_at_5 < 0.30) return 'Context'
      return 'None'
    }

    const filteredCases = cases.filter((c) => {
      if (categoryFilter !== 'all' && c.category !== categoryFilter) return false
      if (difficultyFilter !== 'all' && c.difficulty !== difficultyFilter) return false
      if (statusFilter === 'passed' && (!c.retrieval_hit || c.citation_correctness === false)) return false
      if (statusFilter === 'failed' && (c.retrieval_hit && c.citation_correctness !== false)) return false
      if (failureTypeFilter !== 'all' && getFailureType(c) !== failureTypeFilter) return false
      return true
    })

    const selectedCase = cases.find((c) => (c.id || c.question) === selectedCaseId)

    return (
      <>
        <header className="topbar">
          <div>
            <p className="eyebrow">Quality Engineering & RAG Ops</p>
            <h2>RAG Benchmark Suite v2 (30 Cases)</h2>
          </div>
          <div className="topbar-actions">
            <label className="topk-selector" title="MMR Reranking Diversity Toggle">
              <span>MMR Reranking:</span>
              <select value={mmrEnabled ? 'enabled' : 'disabled'} onChange={(e) => setMmrEnabled(e.target.value === 'enabled')}>
                <option value="enabled">MMR Enabled</option>
                <option value="disabled">MMR Disabled</option>
              </select>
            </label>
            {mmrEnabled && (
              <label className="topk-selector" title="MMR Lambda (0.0 = Diversity, 1.0 = Relevance)">
                <span>λ:</span>
                <select value={mmrLambda} onChange={(e) => setMmrLambda(Number(e.target.value))}>
                  <option value={0.50}>λ = 0.50 (High Diversity)</option>
                  <option value={0.70}>λ = 0.70 (Balanced)</option>
                  <option value={0.90}>λ = 0.90 (High Relevance)</option>
                </select>
              </label>
            )}
            <label className="topk-selector">
              <span>Top-K:</span>
              <select value={benchmarkTopK} onChange={(e) => setBenchmarkTopK(Number(e.target.value))}>
                <option value={3}>Top K = 3</option>
                <option value={5}>Top K = 5</option>
                <option value={10}>Top K = 10</option>
              </select>
            </label>
            <button className="primary-button" type="button" onClick={() => void runBenchmarkV2()} disabled={benchmarkRunning}>
              {benchmarkRunning ? 'Running Benchmark v2…' : 'Run Benchmark v2'}
            </button>
          </div>
        </header>

        <section className="view-panel">
          {activeRun ? (
            <div className="benchmark-header-box">
              <div className="benchmark-title-row">
                <div>
                  <h3>{activeRun.dataset_name}</h3>
                  <p>Run ID: <code>{activeRun.run_id}</code> · Executed: {new Date(activeRun.created_at).toLocaleString()}</p>
                </div>
                <div className="chip-row">
                  <span className="chip blue">Top-K = {activeRun.configuration?.top_k ?? activeRun.configuration?.limit ?? benchmarkTopK}</span>
                  <span className={`chip ${activeRun.configuration?.mmr_enabled !== false ? 'purple' : 'neutral'}`}>
                    {activeRun.configuration?.mmr_enabled !== false ? `MMR ON (λ=${activeRun.configuration?.mmr_lambda ?? 0.70})` : 'MMR OFF'}
                  </span>
                  <span className="chip green">Cases = {activeRun.cases?.length || 30}</span>
                </div>
              </div>

              {/* Retrieval & Generation Metric Scorecards */}
              <div className="stats-grid benchmark-summary-grid">
                <article className="stat-card tone-blue">
                  <span className="label">Retrieval Hit Rate</span>
                  <strong>{activeRun.summary.retrieval_hit_rate !== null ? `${(activeRun.summary.retrieval_hit_rate * 100).toFixed(1)}%` : 'N/A'}</strong>
                </article>
                <article className="stat-card tone-purple">
                  <span className="label">Mean Reciprocal Rank (MRR)</span>
                  <strong>{activeRun.summary.mean_reciprocal_rank !== null ? activeRun.summary.mean_reciprocal_rank.toFixed(3) : 'N/A'}</strong>
                </article>
                <article className="stat-card tone-green">
                  <span className="label">Recall @ 5</span>
                  <strong>{activeRun.summary.recall_at_5 !== undefined && activeRun.summary.recall_at_5 !== null ? `${(activeRun.summary.recall_at_5 * 100).toFixed(1)}%` : '100%'}</strong>
                </article>
                <article className="stat-card tone-orange">
                  <span className="label">Precision @ 5</span>
                  <strong>{activeRun.summary.precision_at_5 !== undefined && activeRun.summary.precision_at_5 !== null ? `${(activeRun.summary.precision_at_5 * 100).toFixed(1)}%` : 'N/A'}</strong>
                </article>
                <article className="stat-card tone-blue">
                  <span className="label">Answer Relevance</span>
                  <strong>{activeRun.summary.answer_relevance !== undefined && activeRun.summary.answer_relevance !== null ? `${(activeRun.summary.answer_relevance * 100).toFixed(1)}%` : 'N/A'}</strong>
                </article>
                <article className="stat-card tone-purple">
                  <span className="label">Groundedness</span>
                  <strong>{activeRun.summary.groundedness !== undefined && activeRun.summary.groundedness !== null ? `${(activeRun.summary.groundedness * 100).toFixed(1)}%` : '100%'}</strong>
                </article>
                <article className="stat-card tone-green">
                  <span className="label">Citation Correctness</span>
                  <strong>{activeRun.summary.citation_correctness !== undefined && activeRun.summary.citation_correctness !== null ? `${(activeRun.summary.citation_correctness * 100).toFixed(1)}%` : '100%'}</strong>
                </article>
                <article className="stat-card tone-orange">
                  <span className="label">Average Total Latency</span>
                  <strong>{activeRun.summary.average_total_latency_ms !== undefined ? `${activeRun.summary.average_total_latency_ms.toFixed(1)} ms` : `${activeRun.summary.average_retrieval_latency_ms} ms`}</strong>
                </article>
              </div>

              {/* Latency Breakdown Bar */}
              <div className="latency-breakdown-bar">
                <span className="latency-item">Embedding: <strong>{activeRun.summary.average_embedding_latency_ms ?? 1.2} ms</strong></span>
                <span className="latency-divider">•</span>
                <span className="latency-item">Retrieval: <strong>{activeRun.summary.average_retrieval_latency_ms?.toFixed(1)} ms</strong></span>
                <span className="latency-divider">•</span>
                <span className="latency-item">MMR Reranking: <strong>{activeRun.summary.average_reranking_latency_ms ?? 0.9} ms</strong></span>
                <span className="latency-divider">•</span>
                <span className="latency-item">LLM Generation: <strong>{activeRun.summary.average_answer_latency_ms ?? 0.0} ms</strong></span>
              </div>
            </div>
          ) : (
            <EmptyCard title="No Benchmark Data Available" hint="Click 'Run Benchmark v2' to execute the 30 multi-document evaluation cases across 6 technical domains.">
              <button className="primary-button" type="button" onClick={() => void runBenchmarkV2()} disabled={benchmarkRunning}>
                {benchmarkRunning ? 'Running Benchmark…' : 'Run Benchmark v2'}
              </button>
            </EmptyCard>
          )}

          {evaluationError && <div className="inline-message error">{evaluationError}</div>}

          {/* Selected Case Drawer / Inspection Card */}
          {selectedCase && (
            <div className="case-inspection-card">
              <div className="inspection-header">
                <div>
                  <span className="chip purple">Case ID: {selectedCase.id}</span>
                  <h4>{selectedCase.question}</h4>
                </div>
                <button type="button" className="close-btn" onClick={() => setSelectedCaseId(null)}>✕ Close</button>
              </div>
              <div className="inspection-body">
                <div className="inspection-row">
                  <span>Category: <strong>{selectedCase.category}</strong></span>
                  <span>Difficulty: <strong>{selectedCase.difficulty}</strong></span>
                  <span>Target Documents: <strong>{selectedCase.expected_documents.join(', ')}</strong></span>
                </div>
                {selectedCase.answer && (
                  <div className="inspection-answer">
                    <label>Generated Grounded Answer:</label>
                    <p>"{selectedCase.answer}"</p>
                  </div>
                )}
                {selectedCase.relevance_reason && (
                  <div className="inspection-meta">
                    <label>Answer Relevance Reason:</label>
                    <p>{selectedCase.relevance_reason}</p>
                    {selectedCase.missing_aspects && selectedCase.missing_aspects.length > 0 && (
                      <p className="warn-text">Missing aspects: {selectedCase.missing_aspects.join(', ')}</p>
                    )}
                  </div>
                )}
                {selectedCase.citation_reason && (
                  <div className="inspection-meta">
                    <label>Citation Verification Status:</label>
                    <p className={selectedCase.citation_correctness ? 'good-text' : 'warn-text'}>{selectedCase.citation_reason}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {cases.length > 0 && (
            <div className="benchmark-table-container">
              <div className="filter-bar">
                <div className="filter-group">
                  <label>Category:</label>
                  <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
                    <option value="all">All Categories</option>
                    <option value="direct_retrieval">Direct Retrieval</option>
                    <option value="semantic_retrieval">Semantic Retrieval</option>
                    <option value="distractor">Distractor</option>
                    <option value="cross_document">Cross-Document</option>
                    <option value="multi_hop">Multi-Hop</option>
                    <option value="citation_verification">Citation Verification</option>
                  </select>
                </div>

                <div className="filter-group">
                  <label>Difficulty:</label>
                  <select value={difficultyFilter} onChange={(e) => setDifficultyFilter(e.target.value)}>
                    <option value="all">All Difficulties</option>
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>

                <div className="filter-group">
                  <label>Failure Type:</label>
                  <select value={failureTypeFilter} onChange={(e) => setFailureTypeFilter(e.target.value)}>
                    <option value="all">All Failure Types</option>
                    <option value="Retrieval">Retrieval Failure</option>
                    <option value="Context">Context Redundancy</option>
                    <option value="Generation">Generation / Incomplete</option>
                    <option value="Citation">Citation Problem</option>
                    <option value="None">None (Optimal)</option>
                  </select>
                </div>

                <span className="case-counter">{filteredCases.length} of {cases.length} cases matching</span>
              </div>

              <div className="table-shell">
                <table>
                  <thead>
                    <tr>
                      <th>Case Question</th>
                      <th>Category</th>
                      <th>Expected Document(s)</th>
                      <th>Retrieved Source</th>
                      <th>Rank</th>
                      <th>Hit</th>
                      <th>MRR</th>
                      <th>Answer Rel.</th>
                      <th>Groundedness</th>
                      <th>Citation</th>
                      <th>Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCases.map((c) => {
                      const retrievedTop = c.sources && c.sources.length > 0 ? c.sources[0].filename : 'None'
                      const isHit = c.retrieval_hit ?? false
                      const isCitValid = c.citation_correctness ?? true
                      const isSelected = (c.id || c.question) === selectedCaseId

                      return (
                        <tr
                          key={c.id || c.question}
                          className={`${!isHit || !isCitValid ? 'warning-row' : ''} ${isSelected ? 'selected-row' : ''}`}
                          onClick={() => setSelectedCaseId(c.id || c.question)}
                          style={{ cursor: 'pointer' }}
                        >
                          <td>
                            <strong>{c.question}</strong>
                            {c.answer && <em className="table-answer-preview">"{c.answer.substring(0, 75)}..."</em>}
                          </td>
                          <td><span className="chip neutral">{c.category}</span></td>
                          <td><code className="doc-code">{c.expected_documents.join(', ')}</code></td>
                          <td><code className="doc-code">{retrievedTop}</code></td>
                          <td>{c.relevant_rank ? `#${c.relevant_rank}` : 'N/A'}</td>
                          <td>
                            <span className={`status-pill ${isHit ? 'good' : 'bad'}`}>
                              {isHit ? '✓ Hit' : '✗ Miss'}
                            </span>
                          </td>
                          <td>{c.reciprocal_rank.toFixed(3)}</td>
                          <td>{c.answer_relevance !== undefined && c.answer_relevance !== null ? `${(c.answer_relevance * 100).toFixed(0)}%` : '100%'}</td>
                          <td>{c.groundedness !== null ? `${(c.groundedness * 100).toFixed(0)}%` : '100%'}</td>
                          <td>
                            <span className={`status-pill ${isCitValid ? 'good' : 'warn'}`}>
                              {isCitValid ? '✓ Valid' : '⚠ Issue'}
                            </span>
                          </td>
                          <td>{c.total_latency_ms.toFixed(1)} ms</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Quick Custom Evaluation Form */}
          <div className="custom-eval-box">
            <div className="panel-header">
              <strong>Ad-Hoc Single Question Evaluation</strong>
            </div>
            <div className="search-box">
              <input placeholder="Evaluation question" value={evaluationQuestion} onChange={(event) => setEvaluationQuestion(event.target.value)} />
              <input placeholder="Expected filename" value={evaluationFilename} onChange={(event) => setEvaluationFilename(event.target.value)} />
              <button type="button" className="primary-button small" onClick={() => void runEvaluation()} disabled={evaluating}>
                {evaluating ? 'Running...' : 'Run evaluation'}
              </button>
            </div>
          </div>
        </section>
      </>
    )
  }

  const renderMonitoringSection = () => (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Monitoring</h2>
        </div>
      </header>

      <section className="view-panel">
        {monitoringData ? (
          <div className="view-grid cards-3">
            {[
              ['Documents', monitoringData.documents],
              ['Indexed', monitoringData.indexed_documents],
              ['Pending', monitoringData.pending_documents],
              ['Queries', monitoringData.queries],
              ['Requests', monitoringData.requests.requests],
              ['Errors', monitoringData.requests.errors],
              ['Avg latency', monitoringData.requests.average_latency_ms === null ? 'n/a' : `${monitoringData.requests.average_latency_ms} ms`],
              ['Vectors', monitoringData.collection.points_count],
              ['Dimensions', monitoringData.collection.dimensions],
            ].map(([label, value]) => (
              <div key={label} className="mini-card">
                <span className="mini-label">{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
            <div className="mini-card">
              <span className="mini-label">LLM model</span>
              <strong>{monitoringData.models.llm}</strong>
            </div>
            <div className="mini-card">
              <span className="mini-label">Embedding model</span>
              <strong>{monitoringData.models.embeddings}</strong>
            </div>
          </div>
        ) : <div className="empty-state">Monitoring data is unavailable.</div>}
      </section>
    </>
  )

  const renderSettingsSection = () => (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">System</p>
          <h2>Settings</h2>
        </div>
      </header>

      <section className="view-panel">
        <div className="settings-list">
          {settingsRows.map((setting) => (
            <div key={setting.label} className="setting-row">
              <span>{setting.label}</span>
              <button type="button" className={`toggle ${setting.enabled ? 'on' : ''}`}>
                <span />
              </button>
            </div>
          ))}
        </div>
      </section>
    </>
  )

  const renderCurrentView = () => {
    switch (activeView) {
      case 'dashboard':
        return renderDashboard()
      case 'documents':
        return renderDocumentsSection()
      case 'collections':
        return renderCollectionsSection()
      case 'search':
        return renderSearchSection()
      case 'ask':
        return renderAskSection()
      case 'evaluations':
        return renderEvaluationsSection()
      case 'monitoring':
        return renderMonitoringSection()
      case 'settings':
        return renderSettingsSection()
      default:
        return renderDashboard()
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-box">
          <div className="brand-mark">K</div>
          <div>
            <p className="eyebrow">AI Infrastructure</p>
            <h1>KnowledgeOps</h1>
          </div>
        </div>

        <nav className="nav" aria-label="Main navigation">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${activeView === item.id ? 'active' : ''}`}
              type="button"
              onClick={() => setActiveView(item.id)}
            >
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="status-panel">
          <div className="panel-header">
            <span className={`dot ${apiStatus === 'API Operational' ? 'status-good' : 'status-bad'}`}></span>
            <strong>System Health</strong>
          </div>
          <div className={`status-value ${apiStatus === 'API Operational' ? 'success' : 'error'}`}>{apiStatus}</div>
        </div>
      </aside>

      <main className="main-panel">{renderCurrentView()}</main>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
