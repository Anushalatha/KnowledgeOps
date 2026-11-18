import React from 'react'
import ReactDOM from 'react-dom/client'
import ReactMarkdown from 'react-markdown'
import './style.css'

type DocumentRecord = {
  document_id: string
  filename: string
  file_type: string
  file_size?: number
  status: string
  created_at: string
  uploaded_at?: string | null
  project_name?: string | null
  category?: string | null
  source_type?: string | null
}

type DocumentContent = {
  document_id: string
  filename: string
  text: string
  word_count: number
}

type PointRecord = {
  point_id?: string
  document_id?: string
  document_name?: string
  filename?: string
  chunk_id?: string
  chunk_index?: number
  page_number?: number | string | null
  project_name?: string | null
  category?: string | null
  source_type?: string | null
  text?: string
  [key: string]: unknown
}

type SearchResult = {
  filename: string
  chunk_id: string
  text: string
  score: number
  point_id?: string
  document_id?: string
  document_name?: string
  chunk_index?: number
  page_number?: number | string | null
  project_name?: string | null
  category?: string | null
  source_type?: string | null
  content_hash?: string
  uploaded_at?: string | null
  retrieval_score?: number
  reranking_score?: number
  mmr_score?: number
  [key: string]: unknown
}

type SearchResponse = {
  query: string
  count: number
  candidate_count: number
  reranker: string
  reranking_latency_ms: number
  results: SearchResult[]
}

type HumanBenchmarkRun = {
  query_id: string
  query: string
  created_at: string
  retrieval_method: string | null
  candidate_count: number
  retrieval_latency_ms: number | null
  reranking_latency_ms: number
  results: SearchResult[]
  metrics: {
    hit_at_5: boolean
    relevant_chunks_retrieved: number
    judged_relevant_chunks: number
    recall_at_5: number
    judged_results: number
    precision_at_5: number | null
    ndcg_at_5: number | null
    reciprocal_rank: number | null
  }
}

type AskSource = {
  citation: number
  filename: string
  chunk_id?: string
  document_id?: string
  document_name?: string
  point_id?: string
  chunk_index?: number
  text?: string
  project_name?: string | null
  category?: string | null
  source_type?: string | null
  retrieval_score?: number
  reranking_score?: number
  mmr_score?: number
  page_number?: number | null
}

type SystemStatus = {
  api: string
  llm: string
  embeddings: string
  qdrant: string
  database?: string
}

type DashboardStats = {
  document_count: number
  chunk_count: number
  vector_count?: number | null
  collection_count?: number | null
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

type CollectionDetails = CollectionSummary & {
  distance?: string | null
  vectors?: { name: string; size: number; distance: string }[]
  payload_fields?: string[]
  payload_field_statistics?: Record<string, {
    present_points: number
    missing_points: number
    unknown_points: number
    known_points: number
    completeness_percent: number | null
    types: string[]
  }>
  document_count?: number
  sqlite_document_count?: number
  distinct_qdrant_document_ids?: number
  matched_sqlite_document_count?: number
  unmatched_document_id_count?: number
  matched_points?: number
  unmatched_points?: number | null
  metadata_completeness?: Record<string, { unknown_points: number; known_points: number }>
  optimizer_config?: Record<string, unknown> | null
  hnsw_config?: Record<string, unknown> | null
  indexed_payload_schema?: string[]
}

type MonitoringData = {
  documents: number
  indexed_documents: number
  pending_documents: number
  queries: number
  collection: Omit<CollectionSummary, 'points_count' | 'dimensions'> & { points_count: number | null; dimensions: number | null }
  models: { llm: string; embeddings: string }
  health?: Record<string, unknown>
  requests: {
    requests: number
    errors: number
    successes?: number
    success_rate: number | null
    average_latency_ms: number | null
    status_distribution?: Record<string, number>
    requests_last_hour?: number
    request_rate_per_minute_last_hour?: number | null
    by_endpoint?: {
      method: string
      path: string
      requests: number
      successes: number
      errors: number
      average_latency_ms: number | null
    }[]
    recent_failures?: {
      request_id: string
      method: string
      path: string
      status_code: number
      latency_ms: number
      created_at: string
    }[]
  }
  recent_requests?: { request_id: string; method: string; path: string; status_code: number; latency_ms: number; created_at: string }[]
  operation_metrics?: {
    operations: number
    by_operation: {
      operation: string
      count: number
      average_embedding_latency_ms: number | null
      average_vector_retrieval_latency_ms: number | null
      average_reranking_latency_ms: number | null
      average_generation_latency_ms: number | null
      average_total_latency_ms: number | null
    }[]
  }
}

type SettingsData = {
  application: Record<string, string>
  llm: Record<string, string>
  embeddings: Record<string, string>
  vector_database: Record<string, string>
  retrieval: Record<string, string | number | boolean>
  database: Record<string, string>
}

type HumanJudgments = {
  query_id: string
  query: string
  judgment_count: number
  source_file: string
  identifier_validation: string
  human_review_provenance: string
  validation_errors: string[]
  relevant_chunks: (PointRecord & { relevance_grade: number; identifier_found: boolean })[]
}

type EvaluationCaseResult = {
  id?: string
  question: string
  category?: string
  difficulty?: string
  expected_documents?: string[]
  retrieved_chunks?: number
  relevant_rank?: number | null
  retrieval_hit?: boolean | null
  reciprocal_rank?: number | null
  recall_at_3?: number | null
  recall_at_5?: number | null
  precision_at_3?: number | null
  precision_at_5?: number | null
  answer: string | null
  answer_relevance?: number | null
  relevance_reason?: string | null
  missing_aspects?: string[]
  target_type?: string
  insufficient_evidence_correctness?: boolean | null
  groundedness?: number | null
  unsupported_claim_count?: number
  citation_correctness: boolean | null
  citation_reason?: string | null
  retrieval_latency_ms?: number
  answer_latency_ms: number | null
  total_latency_ms?: number
  retrieval_source?: string
  answer_source?: string
  sources?: { filename: string; chunk_id: string; score: number }[]
}

type EvaluationRun = {
  run_id: string
  evaluation_version?: string
  scoring_definitions?: Record<string, string>
  retrieval_source_counts?: Record<string, number>
  answer_source_counts?: Record<string, number>
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
    targeted_case_count?: number
    expected_document_case_count?: number
    retrieval_hit_rate: number | null
    mean_reciprocal_rank: number | null
    recall_at_3?: number | null
    recall_at_5?: number | null
    precision_at_3?: number | null
    precision_at_5?: number | null
    answer_relevance?: number | null
    groundedness?: number | null
    citation_correctness?: number | null
    insufficient_evidence_correctness?: number | null
    average_embedding_latency_ms?: number
    average_retrieval_latency_ms?: number | null
    average_reranking_latency_ms?: number
    average_answer_latency_ms?: number | null
    average_total_latency_ms?: number | null
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

function displayMetadataValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Not provided'
  if (value === 'unknown') return 'Unknown (stored)'
  return String(value)
}

function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string
  title: string
  description?: string
  actions?: React.ReactNode
}) {
  return (
    <header className="topbar page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        {description && <p className="page-description">{description}</p>}
      </div>
      {actions && <div className="topbar-actions">{actions}</div>}
    </header>
  )
}

function PointDetailsDrawer({
  point,
  onClose,
  onCopy,
}: {
  point: PointRecord
  onClose: () => void
  onCopy: (value: string, label: string) => void
}) {
  const metadata = Object.fromEntries(
    Object.entries(point).filter(([key]) => key !== 'text'),
  )
  const metadataRows: [string, unknown][] = [
    ['Document name', point.document_name ?? point.filename],
    ['Document ID', point.document_id],
    ['Chunk ID', point.chunk_id],
    ['Qdrant point ID', point.point_id],
    ['Chunk index', point.chunk_index],
    ['Page number', point.page_number],
    ['Project', point.project_name],
    ['Category', point.category],
    ['Source type', point.source_type],
    ['Retrieval score', point.retrieval_score ?? point.score],
    ['Reranking score', point.reranking_score],
    ['MMR score', point.mmr_score],
  ]
  return (
    <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose()
    }}>
      <aside className="details-drawer" role="dialog" aria-modal="true" aria-label="Chunk details">
        <div className="drawer-header">
          <div>
            <p className="eyebrow">Read-only point inspection</p>
            <h3>{String(point.document_name ?? point.filename ?? 'Chunk details')}</h3>
          </div>
          <button type="button" className="secondary-button small" onClick={onClose}>Close</button>
        </div>
        <div className="drawer-copy-actions">
          {point.chunk_id && <button type="button" className="secondary-button small" onClick={() => onCopy(point.chunk_id!, 'Chunk ID')}>Copy chunk ID</button>}
          {point.document_id && <button type="button" className="secondary-button small" onClick={() => onCopy(point.document_id!, 'Document ID')}>Copy document ID</button>}
          {point.point_id && <button type="button" className="secondary-button small" onClick={() => onCopy(point.point_id!, 'Point ID')}>Copy point ID</button>}
          {typeof point.text === 'string' && <button type="button" className="secondary-button small" onClick={() => onCopy(point.text!, 'Chunk text')}>Copy text</button>}
          <button type="button" className="secondary-button small" onClick={() => onCopy(JSON.stringify(metadata, null, 2), 'Metadata JSON')}>Copy metadata JSON</button>
        </div>
        <dl className="metadata-grid">
          {metadataRows.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{displayMetadataValue(value)}</dd>
            </div>
          ))}
        </dl>
        <section className="full-chunk-text">
          <h4>Full chunk text</h4>
          <pre>{typeof point.text === 'string' ? point.text : 'Not available'}</pre>
        </section>
      </aside>
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
  const [selectedCollection, setSelectedCollection] = React.useState<string | null>(null)
  const [collectionDetails, setCollectionDetails] = React.useState<CollectionDetails | null>(null)
  const [collectionPoints, setCollectionPoints] = React.useState<PointRecord[]>([])
  const [collectionPointOffset, setCollectionPointOffset] = React.useState<string | null>(null)
  const [collectionPointTotal, setCollectionPointTotal] = React.useState<number | null>(null)
  const [collectionPointFilters, setCollectionPointFilters] = React.useState({
    point_query: '',
    filter_field: '',
    filter_value: '',
    unmatched_only: false,
  })
  const [collectionError, setCollectionError] = React.useState<string | null>(null)
  const [collectionLoading, setCollectionLoading] = React.useState(false)
  const [monitoringData, setMonitoringData] = React.useState<MonitoringData | null>(null)
  const [monitoringError, setMonitoringError] = React.useState<string | null>(null)
  const [settingsData, setSettingsData] = React.useState<SettingsData | null>(null)
  const [settingsError, setSettingsError] = React.useState<string | null>(null)
  const [evaluationRuns, setEvaluationRuns] = React.useState<EvaluationRun[]>([])
  const [selectedRunId, setSelectedRunId] = React.useState<string | null>(null)
  const [evaluationLoadError, setEvaluationLoadError] = React.useState<string | null>(null)
  const [humanJudgments, setHumanJudgments] = React.useState<HumanJudgments | null>(null)
  const [humanJudgmentsError, setHumanJudgmentsError] = React.useState<string | null>(null)
  const [humanBenchmarkRun, setHumanBenchmarkRun] = React.useState<HumanBenchmarkRun | null>(null)
  const [humanBenchmarkRunning, setHumanBenchmarkRunning] = React.useState(false)
  const [humanBenchmarkError, setHumanBenchmarkError] = React.useState<string | null>(null)
  const [evaluationQuestion, setEvaluationQuestion] = React.useState('')
  const [evaluationFilename, setEvaluationFilename] = React.useState('')
  const [evaluating, setEvaluating] = React.useState(false)
  const [evaluationError, setEvaluationError] = React.useState<string | null>(null)
  const [documents, setDocuments] = React.useState<DocumentRecord[]>([])
  const [documentFilter, setDocumentFilter] = React.useState('')
  const [selectedDocumentId, setSelectedDocumentId] = React.useState<string | null>(null)
  const [documentContent, setDocumentContent] = React.useState<DocumentContent | null>(null)
  const [chunkCount, setChunkCount] = React.useState<number | null>(null)
  const [indexedDocumentChunks, setIndexedDocumentChunks] = React.useState<PointRecord[]>([])
  const [indexedDocumentChunkOffset, setIndexedDocumentChunkOffset] = React.useState<string | null>(null)
  const [indexedDocumentChunkCount, setIndexedDocumentChunkCount] = React.useState<number | null>(null)
  const [documentError, setDocumentError] = React.useState<string | null>(null)
  const [uploading, setUploading] = React.useState(false)
  const [uploadMessage, setUploadMessage] = React.useState<string | null>(null)
  const [uploadError, setUploadError] = React.useState<string | null>(null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const [searchQuery, setSearchQuery] = React.useState('')
  const [searching, setSearching] = React.useState(false)
  const [searchResults, setSearchResults] = React.useState<SearchResult[]>([])
  const [searchResponse, setSearchResponse] = React.useState<SearchResponse | null>(null)
  const [searchMetadata, setSearchMetadata] = React.useState<{
    candidate_count: number
    retrieval_method?: string
    retrieval_latency_ms?: number
    reranking_latency_ms?: number
    retrieval_candidate_limit?: number
    configuration?: Record<string, unknown>
  } | null>(null)
  const [searchError, setSearchError] = React.useState<string | null>(null)
  const [searchExportError, setSearchExportError] = React.useState<string | null>(null)
  const [selectedPoint, setSelectedPoint] = React.useState<PointRecord | null>(null)
  const [notification, setNotification] = React.useState<string | null>(null)
  const [searchHasRun, setSearchHasRun] = React.useState(false)
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
      setDocumentError(null)
      if (data.length > 0 && !selectedDocumentId) {
        setSelectedDocumentId(data[0].document_id)
      }
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : 'Unable to fetch documents')
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
      if (!response.ok) throw new Error('Unable to load monitoring data')
      if (response.ok) {
        setMonitoringData((await response.json()) as MonitoringData)
      }
      setMonitoringError(null)
    } catch (error) {
      setMonitoringData(null)
      setMonitoringError(error instanceof Error ? error.message : 'Unable to load monitoring data')
    }
  }, [])

  const loadSettings = React.useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/settings')
      if (!response.ok) throw new Error('Unable to load configuration')
      setSettingsData((await response.json()) as SettingsData)
      setSettingsError(null)
    } catch (error) {
      setSettingsData(null)
      setSettingsError(error instanceof Error ? error.message : 'Unable to load configuration')
    }
  }, [])

  const loadCollectionPoints = async (
    collectionName: string,
    append = false,
    offset: string | null = null,
    filters = collectionPointFilters,
  ) => {
    setCollectionLoading(true)
    setCollectionError(null)
    try {
      const params = new URLSearchParams({ limit: '50' })
      if (offset) params.set('offset', offset)
      if (filters.point_query.trim()) params.set('point_query', filters.point_query.trim())
      if (filters.filter_field && filters.filter_value.trim()) {
        params.set('filter_field', filters.filter_field)
        params.set('filter_value', filters.filter_value.trim())
      }
      if (filters.unmatched_only) params.set('unmatched_only', 'true')
      const response = await fetch(
        `http://localhost:8000/collections/${encodeURIComponent(collectionName)}/points?${params.toString()}`,
      )
      const data = (await response.json()) as { detail?: string; points?: PointRecord[]; next_offset?: string | null; total?: number | null }
      if (!response.ok) throw new Error(data.detail ?? 'Unable to load collection points')
      setCollectionPoints((previous) => append ? [...previous, ...(data.points ?? [])] : data.points ?? [])
      setCollectionPointOffset(data.next_offset ?? null)
      setCollectionPointTotal(data.total ?? null)
    } catch (error) {
      setCollectionError(error instanceof Error ? error.message : 'Unable to load collection points')
      if (!append) {
        setCollectionPoints([])
        setCollectionPointTotal(null)
      }
    } finally {
      setCollectionLoading(false)
    }
  }

  const openCollection = async (collectionName: string) => {
    setSelectedCollection(collectionName)
    setCollectionDetails(null)
    setCollectionPoints([])
    setCollectionPointOffset(null)
    setCollectionPointTotal(null)
    const defaultPointFilters = { point_query: '', filter_field: '', filter_value: '', unmatched_only: false }
    setCollectionPointFilters(defaultPointFilters)
    setCollectionLoading(true)
    setCollectionError(null)
    try {
      const response = await fetch(
        `http://localhost:8000/collections/${encodeURIComponent(collectionName)}/details`,
      )
      const data = (await response.json()) as CollectionDetails & { detail?: string }
      if (!response.ok) throw new Error(data.detail ?? 'Unable to load collection details')
      setCollectionDetails(data)
      await loadCollectionPoints(collectionName, false, null, defaultPointFilters)
    } catch (error) {
      setCollectionError(error instanceof Error ? error.message : 'Unable to load collection')
    } finally {
      setCollectionLoading(false)
    }
  }

  const loadEvaluations = React.useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/evaluations')
      const data = (await response.json()) as { runs?: EvaluationRun[]; detail?: string }
      if (!response.ok) throw new Error(data.detail ?? 'Unable to load evaluation history')
      const runs = data.runs ?? []
      setEvaluationRuns(runs)
      setSelectedRunId((selected) => selected && runs.some((run) => run.run_id === selected) ? selected : runs[0]?.run_id ?? null)
      setEvaluationLoadError(null)
    } catch (error) {
      setEvaluationLoadError(error instanceof Error ? error.message : 'Unable to load evaluation history')
    }
  }, [])

  const loadHumanJudgments = React.useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/evaluations/human-judgments')
      const data = (await response.json()) as HumanJudgments & { detail?: string }
      if (!response.ok) throw new Error(data.detail ?? 'Unable to load relevance judgments')
      setHumanJudgments(data)
      setHumanJudgmentsError(null)
    } catch (error) {
      setHumanJudgments(null)
      setHumanJudgmentsError(error instanceof Error ? error.message : 'Unable to load relevance judgments')
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
      const chunksResponse = await fetch(`http://localhost:8000/documents/${encodeURIComponent(documentId)}/indexed-chunks?limit=50`)
      const chunksData = (await chunksResponse.json()) as {
        detail?: string
        total_chunk_count?: number
        chunks?: PointRecord[]
        next_offset?: string | null
      }
      if (!chunksResponse.ok) throw new Error(chunksData.detail ?? 'Unable to load indexed chunks')
      setIndexedDocumentChunks(chunksData.chunks ?? [])
      setIndexedDocumentChunkOffset(chunksData.next_offset ?? null)
      setIndexedDocumentChunkCount(chunksData.total_chunk_count ?? 0)
      setChunkCount(chunksData.total_chunk_count ?? 0)
      setDocumentError(null)
    } catch (error) {
      setDocumentContent(null)
      setChunkCount(null)
      setIndexedDocumentChunks([])
      setIndexedDocumentChunkCount(null)
      setDocumentError(error instanceof Error ? error.message : 'Unable to load document details')
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
    void loadSettings()
    void loadHumanJudgments()
  }, [loadCollections, loadDashboardStats, loadDocuments, loadEvaluations, loadHumanJudgments, loadMonitoring, loadSettings])

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

  const copyToClipboard = async (value: string, label: string) => {
    try {
      await navigator.clipboard.writeText(value)
      setNotification(`${label} copied`)
    } catch {
      setNotification(`Unable to copy ${label.toLowerCase()}`)
    }
    window.setTimeout(() => setNotification(null), 3000)
  }

  const loadMoreIndexedDocumentChunks = async (documentId: string) => {
    if (!indexedDocumentChunkOffset) return
    try {
      const params = new URLSearchParams({ limit: '50', offset: indexedDocumentChunkOffset })
      const response = await fetch(
        `http://localhost:8000/documents/${encodeURIComponent(documentId)}/indexed-chunks?${params.toString()}`,
      )
      const data = (await response.json()) as { detail?: string; chunks?: PointRecord[]; next_offset?: string | null }
      if (!response.ok) throw new Error(data.detail ?? 'Unable to load more chunks')
      setIndexedDocumentChunks((previous) => [...previous, ...(data.chunks ?? [])])
      setIndexedDocumentChunkOffset(data.next_offset ?? null)
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : 'Unable to load more chunks')
    }
  }

  const runSearch = async () => {
    if (!searchQuery.trim()) {
      return
    }
    setSearchError(null)
    setSearchExportError(null)
    setSearchHasRun(true)
    setSearching(true)
    try {
      const response = await fetch('http://localhost:8000/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, limit: 5, candidate_limit: 12 }),
      })
      const data = (await response.json()) as {
        detail?: string
      } | SearchResponse
      if (!response.ok) {
        throw new Error(('detail' in data ? data.detail : undefined) ?? 'Search failed')
      }
      const searchData = data as SearchResponse
      setSearchResponse(searchData)
      setSearchResults(searchData.results)
      setSearchMetadata({
        candidate_count: searchData.candidate_count,
        retrieval_method: response.headers.get('X-Retrieval-Method') ?? undefined,
        retrieval_latency_ms: response.headers.get('X-Retrieval-Latency-Ms') === null
          ? undefined
          : Number(response.headers.get('X-Retrieval-Latency-Ms')),
        reranking_latency_ms: searchData.reranking_latency_ms,
        retrieval_candidate_limit: response.headers.get('X-Retrieval-Candidate-Limit') === null
          ? undefined
          : Number(response.headers.get('X-Retrieval-Candidate-Limit')),
        configuration: { limit: 5, candidate_limit: 12, filters: {} },
      })
      setSelectedPoint(null)
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : 'Search failed')
    } finally {
      setSearching(false)
    }
  }

  const clearSearch = () => {
    setSearchQuery('')
    setSearchResults([])
    setSearchResponse(null)
    setSearchMetadata(null)
    setSearchError(null)
    setSearchExportError(null)
    setSearchHasRun(false)
    setSelectedPoint(null)
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
      const data = (await response.json()) as {
        detail?: string
        answer?: string
        citations?: AskSource[]
        request_id?: string
        latency?: { total_ms: number; retrieval_ms: number; reranking_ms: number; generation_ms: number }
      }
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

  const exportSearchResults = (format: 'json' | 'csv') => {
    if (!searchResponse || !searchMetadata) return
    setSearchExportError(null)
    let objectUrl: string | null = null
    try {
      let contents: string
      let mimeType: string
      let filename: string
      if (format === 'json') {
        contents = JSON.stringify({
          ...searchResponse,
          retrieval_metadata: {
            method: searchMetadata.retrieval_method ?? null,
            latency_ms: searchMetadata.retrieval_latency_ms ?? null,
            candidate_limit: searchMetadata.retrieval_candidate_limit ?? null,
            configuration: searchMetadata.configuration ?? null,
          },
        }, null, 2)
        mimeType = 'application/json'
        filename = 'knowledgeops-search-results.json'
      } else {
        const resultFields = [...new Set(searchResponse.results.flatMap((result) => Object.keys(result)))]
        const fields = [
          'query',
          'rank',
          ...resultFields.filter((field) => field !== 'query' && field !== 'rank'),
          'retrieval_method',
          'retrieval_latency_ms',
          'reranking_latency_ms',
          'candidate_count',
          'result_count',
        ]
        const escapeCell = (value: unknown) => {
          const text = value === null || value === undefined
            ? ''
            : typeof value === 'object'
              ? JSON.stringify(value)
              : String(value)
          return `"${text.replaceAll('"', '""')}"`
        }
        const rows = searchResponse.results.map((result, index) => {
          const row: Record<string, unknown> = {
            ...result,
            query: searchResponse.query,
            rank: index + 1,
            retrieval_method: searchMetadata.retrieval_method,
            retrieval_latency_ms: searchMetadata.retrieval_latency_ms,
            reranking_latency_ms: searchResponse.reranking_latency_ms,
            candidate_count: searchResponse.candidate_count,
            result_count: searchResponse.count,
          }
          return fields.map((field) => escapeCell(row[field])).join(',')
        })
        contents = [fields.map(escapeCell).join(','), ...rows].join('\r\n')
        mimeType = 'text/csv;charset=utf-8'
        filename = 'knowledgeops-search-results.csv'
      }

      objectUrl = URL.createObjectURL(new Blob([contents], { type: mimeType }))
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => {
        if (objectUrl) URL.revokeObjectURL(objectUrl)
      }, 1000)
    } catch (error) {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      setSearchExportError(error instanceof Error ? error.message : 'Unable to export search results')
    }
  }

  const openCitation = (citation: number) => {
    const source = askSources.find((item) => item.citation === citation)
    if (source) setSelectedPoint(source)
  }

  const runHumanBenchmark = async () => {
    if (!humanJudgments || humanJudgments.identifier_validation !== 'passed') return
    const gradeByChunk = new Map(
      humanJudgments.relevant_chunks
        .filter((judgment) => judgment.identifier_found)
        .map((judgment) => [judgment.chunk_id, judgment.relevance_grade]),
    )
    const relevantChunkIds = new Set(
      [...gradeByChunk.entries()]
        .filter(([, grade]) => grade > 0)
        .map(([chunkId]) => chunkId),
    )
    if (relevantChunkIds.size === 0) {
      setHumanBenchmarkError('No validated relevant chunk labels are available for this query.')
      return
    }

    setHumanBenchmarkRunning(true)
    setHumanBenchmarkError(null)
    try {
      const response = await fetch('http://localhost:8000/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: humanJudgments.query, limit: 5, candidate_limit: 12 }),
      })
      const data = (await response.json()) as SearchResponse & { detail?: string }
      if (!response.ok) throw new Error(data.detail ?? 'Unable to run the judged query')

      const firstRelevantRank = data.results.findIndex((result) => relevantChunkIds.has(result.chunk_id))
      const relevantChunksRetrieved = data.results.filter((result) => relevantChunkIds.has(result.chunk_id)).length
      const topResults = data.results.slice(0, 5)
      const topGrades = topResults.map((result) => gradeByChunk.get(result.chunk_id))
      const allTopResultsJudged = topGrades.length > 0 && topGrades.every((grade) => grade !== undefined)
      const reciprocalRankIsDeterminate = firstRelevantRank < 0
        ? topGrades.every((grade) => grade !== undefined)
        : topGrades.slice(0, firstRelevantRank + 1).every((grade) => grade !== undefined)
      const judgedGrades = [...gradeByChunk.values()]
      const dcg = allTopResultsJudged
        ? topGrades.reduce((sum, grade, index) => sum + ((2 ** (grade ?? 0) - 1) / Math.log2(index + 2)), 0)
        : null
      const idealDcg = [...judgedGrades]
        .sort((left, right) => right - left)
        .slice(0, 5)
        .reduce((sum, grade, index) => sum + ((2 ** grade - 1) / Math.log2(index + 2)), 0)
      const reciprocalRank = reciprocalRankIsDeterminate
        ? firstRelevantRank < 0 ? 0 : 1 / (firstRelevantRank + 1)
        : null
      setHumanBenchmarkRun({
        query_id: humanJudgments.query_id,
        query: data.query,
        created_at: new Date().toISOString(),
        retrieval_method: response.headers.get('X-Retrieval-Method'),
        candidate_count: data.candidate_count,
        retrieval_latency_ms: Number(response.headers.get('X-Retrieval-Latency-Ms')) || null,
        reranking_latency_ms: data.reranking_latency_ms,
        results: data.results,
        metrics: {
          hit_at_5: relevantChunksRetrieved > 0,
          relevant_chunks_retrieved: relevantChunksRetrieved,
          judged_relevant_chunks: relevantChunkIds.size,
          recall_at_5: relevantChunksRetrieved / relevantChunkIds.size,
          judged_results: topGrades.filter((grade) => grade !== undefined).length,
          precision_at_5: allTopResultsJudged ? relevantChunksRetrieved / 5 : null,
          ndcg_at_5: dcg != null && idealDcg > 0 ? dcg / idealDcg : null,
          reciprocal_rank: reciprocalRank,
        },
      })
    } catch (error) {
      setHumanBenchmarkError(error instanceof Error ? error.message : 'Unable to run the judged query')
    } finally {
      setHumanBenchmarkRunning(false)
    }
  }

  const [benchmarkTopK, setBenchmarkTopK] = React.useState<number>(5)
  const [mmrEnabled, setMmrEnabled] = React.useState<boolean>(true)
  const [mmrLambda, setMmrLambda] = React.useState<number>(0.70)
  const [candidateK, setCandidateK] = React.useState<number>(15)
  const [selectedCaseId, setSelectedCaseId] = React.useState<string | null>(null)
  const [benchmarkRunning, setBenchmarkRunning] = React.useState<boolean>(false)
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
      setEvaluationRuns((runs) => [run, ...runs])
      setSelectedRunId(run.run_id)
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
      const run = data as EvaluationRun
      setEvaluationRuns((runs) => [run, ...runs])
      setSelectedRunId(run.run_id)
      setEvaluationQuestion('')
      setEvaluationFilename('')
    } catch (error) {
      setEvaluationError(error instanceof Error ? error.message : 'Evaluation failed')
    } finally {
      setEvaluating(false)
    }
  }

  const renderDashboard = () => (
    <>
      <PageHeader
        eyebrow="Operations"
        title="Dashboard"
        description="Operational overview of the knowledge base and retrieval services."
        actions={
          <>
          <button className="secondary-button" type="button" onClick={() => void indexPendingDocuments()} disabled={batchIndexing}>
            {batchIndexing ? 'Indexing…' : 'Index pending'}
          </button>
          <button className="primary-button" type="button" onClick={() => void Promise.all([loadDocuments(), loadDashboardStats(), loadCollections(), loadMonitoring()])}>Refresh</button>
          </>
        }
      />

      <section className="stats-grid">
        {[
          { label: 'Total Documents', value: String(dashboardStats.document_count), tone: 'blue' },
          { label: 'Indexed Vectors', value: dashboardStats.vector_count == null ? 'Not available' : String(dashboardStats.vector_count), tone: 'purple' },
          { label: 'Collections', value: dashboardStats.collection_count == null ? 'Not available' : String(dashboardStats.collection_count), tone: 'blue' },
          { label: 'Indexing Status', value: dashboardStats.indexing_status, tone: 'green' },
          { label: 'Queries', value: String(dashboardStats.query_count), tone: 'orange' },
          { label: 'Successful Requests', value: monitoringData ? String(monitoringData.requests.requests - monitoringData.requests.errors) : 'Not available', tone: 'green' },
          { label: 'Failed Requests', value: monitoringData?.requests.errors == null ? 'Not available' : String(monitoringData.requests.errors), tone: 'orange' },
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
              ...(systemStatus.database ? [{ label: 'Database', status: systemStatus.database }] : []),
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

      <section className="view-panel">
        <div className="view-panel-header"><strong>Recent requests</strong><span className="chip neutral">Request telemetry</span></div>
        {monitoringData?.recent_requests?.length ? (
          <div className="table-shell">
            <table>
              <thead><tr><th>Time</th><th>Route</th><th>Status</th><th>Latency</th><th>Request ID</th></tr></thead>
              <tbody>{monitoringData.recent_requests.slice(0, 8).map((request) => (
                <tr key={request.request_id}>
                  <td>{new Date(request.created_at).toLocaleString()}</td>
                  <td>{request.method} {request.path}</td>
                  <td>{request.status_code}</td>
                  <td>{request.latency_ms} ms</td>
                  <td><code>{request.request_id}</code></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <p className="muted-copy">Recent request history is not available.</p>}
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

  const visibleDocuments = documents.filter((document) => {
    const filter = documentFilter.trim().toLocaleLowerCase()
    return !filter || [
      document.filename,
      document.document_id,
      document.project_name ?? '',
      document.category ?? '',
    ].some((value) => value.toLocaleLowerCase().includes(filter))
  })

  const renderDocumentsSection = () => (
    <>
      <PageHeader
        eyebrow="Knowledge Base"
        title="Documents"
        description="Manage SQLite document records, indexing state, and associated chunks."
        actions={<button className="primary-button" type="button" onClick={openUploadPicker} disabled={uploading}>
          {uploading ? 'Uploading…' : 'Add document'}
        </button>}
      />

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
        <div className="inspection-toolbar">
          <input
            type="search"
            value={documentFilter}
            onChange={(event) => setDocumentFilter(event.target.value)}
            placeholder="Filter by name, ID, project, or category"
            aria-label="Filter documents"
          />
        </div>
        {documentError && <div className="inline-message error">{documentError}</div>}

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
              {visibleDocuments.length > 0 ? visibleDocuments.map((doc) => (
                <tr key={doc.document_id} onClick={() => void loadDocumentContent(doc.document_id)} className={selectedDocumentId === doc.document_id ? 'selected-row' : ''}>
                  <td>
                    <strong>{doc.filename}</strong>
                    <small className="table-subtext">{doc.document_id}</small>
                  </td>
                  <td>{(doc.source_type ?? doc.file_type ?? 'Not available').toUpperCase()}</td>
                  <td><span className={`table-badge ${doc.status}`}>{doc.status}</span></td>
                  <td>{doc.uploaded_at ?? doc.created_at ?? 'Not available'}</td>
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
                  <td colSpan={5}>{documentFilter ? 'No documents match this filter.' : 'No documents uploaded yet.'}</td>
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
            <dl className="metadata-grid document-metadata-grid">
              <div><dt>Document ID</dt><dd>{documentContent.document_id}</dd></div>
              <div><dt>Project</dt><dd>{documents.find((doc) => doc.document_id === documentContent.document_id)?.project_name || 'Not available'}</dd></div>
              <div><dt>Category</dt><dd>{documents.find((doc) => doc.document_id === documentContent.document_id)?.category || 'Not available'}</dd></div>
              <div><dt>Source type</dt><dd>{documents.find((doc) => doc.document_id === documentContent.document_id)?.source_type || 'Not available'}</dd></div>
              <div><dt>File size</dt><dd>{documents.find((doc) => doc.document_id === documentContent.document_id)?.file_size == null ? 'Not available' : `${documents.find((doc) => doc.document_id === documentContent.document_id)?.file_size} bytes`}</dd></div>
            </dl>
            <p>{documentContent.text}</p>
            <div className="indexed-chunk-list">
              <div className="view-panel-header">
                <strong>Indexed chunks</strong>
                <span className="chip blue">{indexedDocumentChunkCount ?? 'Not available'} stored</span>
              </div>
              {indexedDocumentChunks.map((chunk) => (
                <article key={chunk.point_id ?? chunk.chunk_id ?? `${chunk.document_id}-${chunk.chunk_index}`} className="indexed-chunk-row">
                  <div className="indexed-chunk-heading">
                    <strong>{chunk.chunk_id ?? 'Chunk ID not available'}</strong>
                    <span>Point {chunk.point_id ?? 'Not available'} · Index {chunk.chunk_index ?? 'Not available'} · Page {chunk.page_number ?? 'Not available'}</span>
                    <button type="button" className="secondary-button small" onClick={() => setSelectedPoint(chunk)}>Inspect</button>
                  </div>
                  <p>{chunk.text ?? 'Text not available'}</p>
                </article>
              ))}
              {indexedDocumentChunks.length === 0 && <p className="muted-copy">No indexed chunks are available for this document.</p>}
              {indexedDocumentChunkOffset && (
                <button type="button" className="secondary-button" onClick={() => void loadMoreIndexedDocumentChunks(documentContent.document_id)}>
                  Load more indexed chunks
                </button>
              )}
            </div>
            {indexMessage && <div className="inline-message success">{indexMessage}</div>}
            {indexError && <div className="inline-message error">{indexError}</div>}
          </div>
        )}
      </section>
    </>
  )

  const renderCollectionsSection = () => (
    <>
      <PageHeader
        eyebrow="Organization"
        title={selectedCollection ? selectedCollection : 'Collections'}
        description="Inspect collection health, vector configuration, and stored payloads without loading vectors."
        actions={selectedCollection && <button className="secondary-button" type="button" onClick={() => {
          setSelectedCollection(null)
          setCollectionDetails(null)
          setCollectionPoints([])
          setCollectionPointTotal(null)
        }}>Back to collections</button>}
      />

      <section className="view-panel">
        {!selectedCollection ? (
          <div className="view-grid cards-3">
            {collections.length > 0 ? collections.map((collection) => (
              <button key={collection.name} type="button" className="mini-card collection-card" onClick={() => void openCollection(collection.name)}>
                <span className="mini-label">Read-only collection</span>
                <strong>{collection.name}</strong>
                <div className="mini-meta-row">
                  <span>{collection.points_count} points</span>
                  <span>{collection.dimensions} dims</span>
                </div>
                <span className={`status-pill ${pillTone(collection.status)}`}>{collection.status}</span>
                <span className="muted-copy">Open details and inspect stored points</span>
              </button>
            )) : <div className="empty-state">No Qdrant collection has been created yet.</div>}
          </div>
        ) : (
          <>
            {collectionError && <div className="inline-message error">{collectionError}</div>}
            {collectionLoading && !collectionDetails && <div className="empty-state">Loading collection details…</div>}
            {collectionDetails && (
              <>
                <div className="stats-grid">
                  {[
                    ['Status', collectionDetails.status],
                    ['Points', collectionDetails.points_count],
                    ['Dimensions', collectionDetails.dimensions],
                    ['Distance', collectionDetails.distance ?? 'Not available'],
                    ['SQLite documents', collectionDetails.sqlite_document_count ?? 'Not available'],
                    ['Qdrant payload document IDs', collectionDetails.distinct_qdrant_document_ids ?? collectionDetails.document_count ?? 'Not available'],
                    ['Matched points', collectionDetails.matched_points ?? 'Not available'],
                    ['Unmatched points', collectionDetails.unmatched_points ?? 'Not available'],
                  ].map(([label, value]) => (
                    <article key={label} className="stat-card tone-blue"><span className="label">{label}</span><strong>{value}</strong></article>
                  ))}
                </div>
                <div className="collection-config-grid collection-details-grid">
                  <section className="panel-card metadata-completeness-card">
                    <h3>Payload metadata completeness</h3>
                    <div className="table-shell metadata-table-shell">
                      <table className="metadata-completeness-table">
                        <thead><tr><th>Field</th><th>Present</th><th>Nonempty, non-unknown</th><th>Unknown value</th><th>Missing / empty</th><th>Stored types</th></tr></thead>
                        <tbody>
                          {Object.entries(collectionDetails.payload_field_statistics ?? {}).map(([field, stats]) => (
                            <tr key={field}>
                              <td><code className="metadata-field-name">{field}</code></td>
                              <td>{stats.present_points}/{collectionDetails.points_count}</td>
                              <td>{stats.known_points}</td>
                              <td>{stats.unknown_points}</td>
                              <td>{stats.missing_points}</td>
                              <td>{stats.types.join(', ') || 'None'}</td>
                            </tr>
                          ))}
                          {!Object.keys(collectionDetails.payload_field_statistics ?? {}).length && (
                            <tr><td colSpan={6}>No payload field statistics are available.</td></tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                    <p className="muted-copy">Missing, empty, explicit unknown, and other nonempty values are counted separately. A nonempty value is not independently verified against its source.</p>
                  </section>
                  <section className="panel-card payload-fields-card">
                    <h3>Payload fields</h3>
                    <div className="chip-row payload-field-chips">
                      {(collectionDetails.payload_fields ?? []).map((field) => <span className="chip neutral" key={field}>{field}</span>)}
                      {collectionDetails.payload_fields?.length === 0 && <span className="muted-copy">No payload keys found.</span>}
                    </div>
                    <details className="technical-details">
                      <summary>Technical collection configuration</summary>
                      <div className="technical-config-list">
                        {[
                          { label: 'Vector configuration', value: collectionDetails.vectors ?? [] },
                          { label: 'HNSW configuration', value: collectionDetails.hnsw_config ?? 'Not available' },
                          { label: 'Optimizer configuration', value: collectionDetails.optimizer_config ?? 'Not available' },
                        ].map(({ label, value }) => {
                          const json = JSON.stringify(value, null, 2) ?? 'null'
                          return (
                            <section className="technical-config-section" key={label}>
                              <div className="technical-config-heading">
                                <h4>{label}</h4>
                                <button type="button" className="secondary-button small" onClick={() => void copyToClipboard(json, label)}>
                                  Copy JSON
                                </button>
                              </div>
                              <pre><code>{json}</code></pre>
                            </section>
                          )
                        })}
                      </div>
                    </details>
                  </section>
                </div>

                <section className="point-inspector">
                  <div className="view-panel-header">
                    <div><strong>Vector inspector</strong><p className="muted-copy">Payload only; vectors are not loaded.</p></div>
                    <span className="chip blue">{collectionPoints.length} loaded{collectionPointTotal != null ? ` · ${collectionPointTotal} matches` : ''}</span>
                  </div>
                  <div className="inspection-toolbar filter-fields">
                    <input aria-label="Search point payloads" placeholder="Search any payload value" value={collectionPointFilters.point_query} onChange={(event) => setCollectionPointFilters((filters) => ({ ...filters, point_query: event.target.value }))} />
                    <select aria-label="Payload field to filter" value={collectionPointFilters.filter_field} onChange={(event) => setCollectionPointFilters((filters) => ({ ...filters, filter_field: event.target.value }))}>
                      <option value="">Exact field filter (optional)</option>
                      <option value="point_id">Point ID</option>
                      {(collectionDetails.payload_fields ?? []).map((field) => <option key={field} value={field}>{field}</option>)}
                    </select>
                    <input aria-label="Exact field value" placeholder="Exact value" value={collectionPointFilters.filter_value} onChange={(event) => setCollectionPointFilters((filters) => ({ ...filters, filter_value: event.target.value }))} />
                    <label className="inline-checkbox"><input type="checkbox" checked={collectionPointFilters.unmatched_only} onChange={(event) => setCollectionPointFilters((filters) => ({ ...filters, unmatched_only: event.target.checked }))} />Unmatched SQLite documents only</label>
                    <button type="button" className="primary-button small" onClick={() => void loadCollectionPoints(selectedCollection, false, null)}>Apply filters</button>
                  </div>
                  {collectionPointFilters.filter_field && !collectionPointFilters.filter_value.trim() && <p className="muted-copy">Enter an exact value to apply the selected field filter.</p>}
                  {collectionError && <div className="inline-message error">{collectionError}</div>}
                  <div className="point-list">
                    {collectionPoints.map((point) => (
                      <article key={point.point_id ?? point.chunk_id} className="indexed-chunk-row">
                        <div className="indexed-chunk-heading">
                          <strong>{point.document_name ?? point.filename ?? 'Unknown document'}</strong>
                          <span>{point.chunk_id ?? 'Chunk ID unavailable'} · Point {point.point_id ?? 'Unavailable'}</span>
                          <button type="button" className="secondary-button small" onClick={() => setSelectedPoint(point)}>Inspect point</button>
                        </div>
                        <p>{point.text ?? 'Text not available'}</p>
                      </article>
                    ))}
                    {!collectionLoading && collectionPoints.length === 0 && <div className="empty-state">No points match these filters.</div>}
                  </div>
                  {collectionPointOffset && (
                    <button type="button" className="secondary-button" disabled={collectionLoading} onClick={() => void loadCollectionPoints(selectedCollection, true, collectionPointOffset)}>
                      {collectionLoading ? 'Loading…' : 'Load next page'}
                    </button>
                  )}
                </section>
              </>
            )}
          </>
        )}
      </section>
    </>
  )

  const renderSearchSection = () => (
    <>
      <PageHeader
        eyebrow="Discovery"
        title="Search"
        description="Search indexed knowledge using semantic retrieval."
      />

      <section className="view-panel">
        <div className="search-box">
          <input
            type="text"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.nativeEvent.isComposing) void runSearch()
            }}
            placeholder="Ask a question or search indexed chunks"
            aria-label="Search query"
          />
          {searchQuery && <button type="button" className="secondary-button small" onClick={clearSearch}>Clear</button>}
          <button type="button" className="primary-button small" onClick={() => void runSearch()} disabled={searching || !searchQuery.trim()}>{searching ? 'Searching…' : 'Search'}</button>
          {searchResponse && (
            <>
              <button type="button" className="secondary-button small" onClick={() => exportSearchResults('json')}>Export JSON</button>
              <button type="button" className="secondary-button small" onClick={() => exportSearchResults('csv')}>Export CSV</button>
            </>
          )}
        </div>

        {searchResponse && <p className="muted-copy search-response-query">Showing the successful response for: <strong>{searchResponse.query}</strong></p>}
        {searchError && <div className="inline-message error" role="alert">{searchError}</div>}
        {searchExportError && <div className="inline-message error" role="alert">Export failed: {searchExportError}</div>}
        {searchMetadata && (
          <section className="retrieval-observability">
            <div className="view-panel-header"><strong>Retrieval details</strong><span className="chip neutral">{searchMetadata.retrieval_method ?? 'Not available'} · {searchResponse?.reranker ?? 'Reranker unavailable'}</span></div>
            <div className="metric-inline-list">
              <span>Candidates: <strong>{searchMetadata.candidate_count}</strong></span>
              <span>Candidate limit: <strong>{searchMetadata.retrieval_candidate_limit ?? 'Not available'}</strong></span>
              <span>Returned: <strong>{searchResponse?.count ?? searchResults.length}</strong></span>
              <span>Retrieval: <strong>{searchMetadata.retrieval_latency_ms == null ? 'Not available' : `${searchMetadata.retrieval_latency_ms} ms`}</strong></span>
              <span>Reranking: <strong>{searchMetadata.reranking_latency_ms == null ? 'Not available' : `${searchMetadata.reranking_latency_ms} ms`}</strong></span>
            </div>
            <p className="muted-copy">Retrieval latency measures embedding and candidate retrieval. Reranking latency is reported separately. Scores are ranking signals, not probabilities.</p>
            {searchMetadata.configuration && <details><summary>Retrieval configuration</summary><pre>{JSON.stringify(searchMetadata.configuration, null, 2)}</pre></details>}
          </section>
        )}
        <div className="result-list">
          {searchResults.map((result, index) => (
            <article key={result.point_id ?? result.chunk_id} className="result-card interactive-result">
              <div>
                <strong>{result.document_name ?? result.filename ?? 'Unknown document'}</strong>
                <span className="result-preview">{result.text.length > 360 ? `${result.text.slice(0, 360)}…` : result.text}</span>
                <small className="table-subtext">
                  Document {result.document_id ?? 'unavailable'} · Chunk {result.chunk_id}
                  {result.point_id ? ` · Point ${result.point_id}` : ''}
                  {result.page_number != null ? ` · Page ${result.page_number}` : ''}
                </small>
                <small className="table-subtext">
                  Project {result.project_name ?? 'Not available'} · Category {result.category ?? 'Not available'} · Source {result.source_type ?? 'Not available'}
                </small>
                <button type="button" className="secondary-button small" onClick={() => setSelectedPoint(result)}>View chunk details</button>
              </div>
              <div className="ranking-scores">
                <span>Rank {index + 1}</span>
                <span title="Qdrant dense-vector similarity score">Retrieval {result.retrieval_score ?? result.score}</span>
                <span title="Existing lexical/vector reranker score">Reranked {result.reranking_score ?? 'Not available'}</span>
                <span title="Existing maximal marginal relevance selection score">MMR {result.mmr_score ?? 'Not available'}</span>
              </div>
            </article>
          ))}
          {searching && <div className="empty-state">Searching the indexed collection…</div>}
          {!searching && searchHasRun && searchResponse && searchResults.length === 0 && <div className="empty-state">The search completed, but no matching chunks were returned.</div>}
          {!searching && !searchHasRun && <div className="empty-state">Enter a query to search the indexed corpus.</div>}
        </div>
      </section>
    </>
  )

  const renderAskSection = () => (
    <>
      <PageHeader
        eyebrow="Assistant"
        title="Ask Knowledge Base"
        description="Ask a question and inspect the retrieved evidence behind the answer."
      />

      <section className="view-panel">
        <div className="ask-box">
          <textarea value={askQuestion} onChange={(event) => setAskQuestion(event.target.value)} />
          <button type="button" className="primary-button small" onClick={() => void runAsk()} disabled={asking}>
            {asking ? 'Thinking…' : 'Run query'}
          </button>
        </div>

        {askError && <div className="inline-message error">{askError}</div>}
        {asking && <div className="empty-state">Retrieving context and generating an answer…</div>}
        {askAnswer && (
          <div className="answer-box">
            <div className="answer-content">
              <ReactMarkdown components={{
                a: ({ href, children }) => {
                  const match = href?.match(/^#citation-(\d+)$/)
                  if (match) {
                    return <button type="button" className="citation-link" onClick={() => openCitation(Number(match[1]))}>{children}</button>
                  }
                  return <a href={href}>{children}</a>
                },
              }}>
                {askAnswer.replace(/\[(\d+)\]/g, '[$1](#citation-$1)')}
              </ReactMarkdown>
            </div>
            <div className="answer-meta">
              <span>{askSources.length} cited source{askSources.length === 1 ? '' : 's'}</span>
              <div className="citation-list">
                {askSources.map((source) => (
                  <button type="button" key={source.citation} className="citation-source" onClick={() => openCitation(source.citation)}>
                    [{source.citation}] {source.document_name ?? source.filename}{source.page_number ? ` · p.${source.page_number}` : ''}
                    <small>{source.chunk_id ?? 'Chunk ID unavailable'}</small>
                  </button>
                ))}
              </div>
            </div>
            {askLatency && <div className="answer-meta"><span>Request {askRequestId}</span><span>{askLatency.total_ms} ms total · {askLatency.retrieval_ms} ms retrieval · {askLatency.reranking_ms} ms reranking · {askLatency.generation_ms} ms generation</span></div>}
          </div>
        )}
        {!askAnswer && !askError && <div className="empty-state">Ask a question about your indexed documents.</div>}
      </section>
    </>
  )

  const renderEvaluationsSection = () => {
    const activeRun = evaluationRuns.find((run) => run.run_id === selectedRunId) ?? evaluationRuns[0]
    const isBenchmarkRun = activeRun?.dataset_name === 'KnowledgeOps Benchmark Dataset v2'
    const cases = activeRun?.cases || []
    const metricCards = activeRun
      ? [
          { label: 'Cases', value: String(activeRun.summary.case_count ?? cases.length), tone: 'tone-blue' },
          ...(activeRun.summary.retrieval_hit_rate != null ? [{ label: isBenchmarkRun ? 'Expected-document hit rate (any)' : 'Target-match hit rate', value: `${(activeRun.summary.retrieval_hit_rate * 100).toFixed(1)}%`, tone: 'tone-purple' }] : []),
          ...(activeRun.summary.mean_reciprocal_rank != null ? [{ label: 'First target-match MRR', value: activeRun.summary.mean_reciprocal_rank.toFixed(3), tone: 'tone-green' }] : []),
          ...(activeRun.summary.recall_at_5 != null ? [{ label: 'Expected-document recall @ 5', value: `${(activeRun.summary.recall_at_5 * 100).toFixed(1)}%`, tone: 'tone-orange' }] : []),
          ...(activeRun.summary.precision_at_5 != null ? [{ label: 'Chunk precision by expected document @ 5', value: `${(activeRun.summary.precision_at_5 * 100).toFixed(1)}%`, tone: 'tone-blue' }] : []),
          ...(activeRun.summary.answer_relevance != null ? [{ label: 'Topic keyword coverage', value: `${(activeRun.summary.answer_relevance * 100).toFixed(1)}%`, tone: 'tone-purple' }] : []),
          ...(activeRun.summary.groundedness != null ? [{ label: 'Groundedness heuristic (token overlap)', value: `${(activeRun.summary.groundedness * 100).toFixed(1)}%`, tone: 'tone-green' }] : []),
          ...(activeRun.summary.citation_correctness != null ? [{ label: 'Citation structure / document coverage', value: `${(activeRun.summary.citation_correctness * 100).toFixed(1)}%`, tone: 'tone-orange' }] : []),
          ...(activeRun.summary.insufficient_evidence_correctness != null ? [{ label: 'Insufficient-evidence abstention', value: `${(activeRun.summary.insufficient_evidence_correctness * 100).toFixed(1)}%`, tone: 'tone-blue' }] : []),
          ...((activeRun.summary.average_total_latency_ms ?? activeRun.summary.average_retrieval_latency_ms) != null
            ? [{
                label: activeRun.summary.average_total_latency_ms != null ? 'Average Total Latency' : 'Average Retrieval Latency',
                value: `${(activeRun.summary.average_total_latency_ms ?? activeRun.summary.average_retrieval_latency_ms)?.toFixed(1)} ms`,
                tone: 'tone-blue',
              }]
            : []),
        ]
      : []

    const getFailureType = (c: EvaluationCaseResult): string => {
      if (c.retrieval_hit === false) return 'Retrieval'
      if (c.insufficient_evidence_correctness === false) return 'Generation'
      if (c.citation_correctness === false) return 'Citation'
      if (c.answer_relevance !== undefined && c.answer_relevance !== null && c.answer_relevance < 0.80) return 'Generation'
      if (c.precision_at_5 !== undefined && c.precision_at_5 !== null && c.precision_at_5 < 0.30) return 'Context'
      return 'None'
    }

    const filteredCases = cases.filter((c) => {
      if (categoryFilter !== 'all' && c.category !== categoryFilter) return false
      if (difficultyFilter !== 'all' && c.difficulty !== difficultyFilter) return false
      if (statusFilter === 'passed' && (c.retrieval_hit !== true || c.citation_correctness === false || c.insufficient_evidence_correctness === false)) return false
      if (statusFilter === 'failed' && (c.retrieval_hit !== false && c.citation_correctness !== false && c.insufficient_evidence_correctness !== false)) return false
      if (failureTypeFilter !== 'all' && getFailureType(c) !== failureTypeFilter) return false
      return true
    })

    const selectedCase = cases.find((c) => (c.id || c.question) === selectedCaseId)

    return (
      <>
        <PageHeader
          eyebrow="Quality Engineering & RAG Ops"
          title="Evaluations"
          description="Measure retrieval quality, inspect run history, and review supplied relevance labels."
        />

        <section className="view-panel human-judgment-panel">
          <div className="view-panel-header">
            <div>
              <strong>Supplied chunk relevance labels</strong>
              <p className="muted-copy">The judgment file contains suggested chunk grades; identifier checks do not prove human-review provenance. Retrieval runs query the configured global collection.</p>
            </div>
            {humanJudgments && <span className={`status-pill ${humanJudgments.identifier_validation === 'passed' ? 'good' : 'bad'}`}>Identifiers {humanJudgments.identifier_validation}</span>}
          </div>
          {humanJudgmentsError && <div className="inline-message error">{humanJudgmentsError}</div>}
          {!humanJudgments && !humanJudgmentsError && <div className="empty-state">Loading judgment data…</div>}
          {humanJudgments && (
            <>
              <div className="human-benchmark-summary">
                <article className="stat-card tone-blue"><span className="label">Supplied queries</span><strong>{humanJudgments ? 1 : 0}</strong><small>Single query file</small></article>
                <article className="stat-card tone-purple"><span className="label">Judged chunks</span><strong>{humanJudgments.judgment_count}</strong><small>Grades in supplied file</small></article>
                <article className="stat-card tone-orange"><span className="label">Review provenance</span><strong>{humanJudgments.human_review_provenance === 'verified' ? 'Verified' : 'Unverified'}</strong><small>{humanJudgments.human_review_provenance}</small></article>
                <article className="stat-card tone-green"><span className="label">Benchmark readiness</span><strong>{humanJudgments.identifier_validation === 'passed' && humanJudgments.human_review_provenance === 'verified' ? 'Ready' : 'Not verified'}</strong><small>{humanJudgments.identifier_validation === 'passed' ? 'IDs validate; review provenance is unrecorded' : 'Resolve identifier validation errors'}</small></article>
              </div>
              <div className="judged-query-card">
                <div>
                  <span className="eyebrow">{humanJudgments.query_id} · Supplied query</span>
                  <p>{humanJudgments.query}</p>
                </div>
                <button
                  type="button"
                  className="primary-button small"
                  onClick={() => void runHumanBenchmark()}
                  disabled={humanBenchmarkRunning || humanJudgments.identifier_validation !== 'passed'}
                >
                  {humanBenchmarkRunning ? 'Running query…' : 'Run labeled query'}
                </button>
              </div>
              <p className="muted-copy">A query is included as supplied; its human-review provenance is not recorded. Recall divides retrieved validated positive labels by all validated positive labels. Precision@5 and nDCG@5 require every returned top-five result to have a grade. Reciprocal rank is available only when all results through the first positive label are judged (or all results if no positive label is retrieved). Unjudged chunks are never treated as grade zero.</p>
              {humanBenchmarkError && <div className="inline-message error">{humanBenchmarkError}</div>}
              {humanJudgments.validation_errors.map((error) => <div className="inline-message error" key={error}>{error}</div>)}
              <div className="table-shell">
                <table>
                  <thead><tr><th>Grade</th><th>Chunk ID</th><th>Document</th><th>Point ID</th><th>Identifier</th><th></th></tr></thead>
                  <tbody>
                    {humanJudgments.relevant_chunks.map((judgment) => (
                      <tr key={judgment.chunk_id}>
                        <td><span className={`relevance-badge grade-${judgment.relevance_grade}`}>{judgment.relevance_grade}</span></td>
                        <td><code>{judgment.chunk_id}</code></td>
                        <td>{judgment.document_name ?? 'Not available'}</td>
                        <td><code>{judgment.point_id ?? 'Not found'}</code></td>
                        <td>{judgment.identifier_found ? 'Found in Qdrant' : 'Missing'}</td>
                        <td><button type="button" className="secondary-button small" onClick={() => setSelectedPoint(judgment)}>Inspect</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {humanBenchmarkRun && (
                <section className="human-run-panel">
                  <div className="view-panel-header">
                    <div><strong>{humanBenchmarkRun.query_id} retrieval run</strong><p className="muted-copy">Executed {new Date(humanBenchmarkRun.created_at).toLocaleString()} · {humanBenchmarkRun.retrieval_method ?? 'Retrieval method unavailable'}</p></div>
                    <span className="chip neutral">{humanBenchmarkRun.candidate_count} candidates</span>
                  </div>
                  <div className="human-benchmark-summary">
                    <article className="stat-card tone-green" title="At least one validated positive judgment was retrieved in the top five."><span className="label">Labeled hit @ 5</span><strong>{humanBenchmarkRun.metrics.hit_at_5 ? 'Yes' : 'No'}</strong></article>
                    <article className="stat-card tone-green"><span className="label">Judged relevant retrieved</span><strong>{humanBenchmarkRun.metrics.relevant_chunks_retrieved}/{humanBenchmarkRun.metrics.judged_relevant_chunks}</strong></article>
                    <article className="stat-card tone-blue"><span className="label">Recall @ 5</span><strong>{(humanBenchmarkRun.metrics.recall_at_5 * 100).toFixed(1)}%</strong></article>
                    <article className="stat-card tone-blue"><span className="label">Judged results @ 5</span><strong>{humanBenchmarkRun.metrics.judged_results}/{Math.min(5, humanBenchmarkRun.results.length)}</strong></article>
                    <article className="stat-card tone-purple" title="Only shown when each returned top-five result has an explicit judgment."><span className="label">Precision @ 5</span><strong>{humanBenchmarkRun.metrics.precision_at_5 == null ? 'Unavailable' : `${(humanBenchmarkRun.metrics.precision_at_5 * 100).toFixed(1)}%`}</strong></article>
                    <article className="stat-card tone-purple" title="Only shown when each returned top-five result has an explicit grade."><span className="label">nDCG @ 5</span><strong>{humanBenchmarkRun.metrics.ndcg_at_5 == null ? 'Unavailable' : humanBenchmarkRun.metrics.ndcg_at_5.toFixed(3)}</strong></article>
                    <article className="stat-card tone-purple" title="Requires judged ranks before the first positive result; if none is retrieved, all returned results must be judged."><span className="label">Reciprocal rank</span><strong>{humanBenchmarkRun.metrics.reciprocal_rank == null ? 'Unavailable' : humanBenchmarkRun.metrics.reciprocal_rank.toFixed(3)}</strong></article>
                    <article className="stat-card tone-orange"><span className="label">Retrieval / rerank</span><strong>{humanBenchmarkRun.retrieval_latency_ms == null ? 'Unavailable' : `${humanBenchmarkRun.retrieval_latency_ms} / ${humanBenchmarkRun.reranking_latency_ms} ms`}</strong></article>
                  </div>
                  <div className="table-shell">
                    <table>
                      <thead><tr><th>Rank</th><th>Chunk</th><th>Document</th><th>Judgment</th><th>Score</th><th></th></tr></thead>
                      <tbody>
                        {humanBenchmarkRun.results.map((result, index) => {
                          const grade = humanJudgments.relevant_chunks.find((item) => item.chunk_id === result.chunk_id)?.relevance_grade
                          return (
                            <tr key={result.point_id ?? result.chunk_id}>
                              <td>{index + 1}</td>
                              <td><code>{result.chunk_id}</code></td>
                              <td>{result.document_name ?? result.filename ?? 'Not available'}</td>
                              <td>{grade === undefined ? 'Unjudged' : <span className={`relevance-badge grade-${grade}`}>{grade}</span>}</td>
                              <td>{result.score ?? 'Not available'}</td>
                              <td><button type="button" className="secondary-button small" onClick={() => setSelectedPoint(result)}>Inspect</button></td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}
            </>
          )}
        </section>

        <section className="view-panel">
          <div className="notice-banner">The 30-case dataset remains v2; new runs use the versioned expected-document scorer and disclose whether they used Qdrant/LLM or benchmark fallback data. These results are not human-judged chunk relevance. Existing runs remain unchanged.</div>
          <div className="benchmark-controls">
            <div>
              <strong>v2 benchmark dataset settings</strong>
              <span>Run the existing compatibility evaluation suite.</span>
            </div>
            <label className="topk-selector">
              <span>MMR</span>
              <select value={mmrEnabled ? 'enabled' : 'disabled'} onChange={(e) => setMmrEnabled(e.target.value === 'enabled')}>
                <option value="enabled">Enabled</option>
                <option value="disabled">Disabled</option>
              </select>
            </label>
            {mmrEnabled && (
              <label className="topk-selector">
                <span>Diversity (λ)</span>
                <select value={mmrLambda} onChange={(e) => setMmrLambda(Number(e.target.value))}>
                  <option value={0.50}>0.50 · High relevance</option>
                  <option value={0.70}>0.70 · Balanced</option>
                  <option value={0.90}>0.90 · High diversity</option>
                </select>
              </label>
            )}
            <label className="topk-selector">
              <span>Top-K</span>
              <select value={benchmarkTopK} onChange={(e) => setBenchmarkTopK(Number(e.target.value))}>
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
              </select>
            </label>
            <button className="primary-button" type="button" onClick={() => void runBenchmarkV2()} disabled={benchmarkRunning}>
              {benchmarkRunning ? 'Running benchmark…' : 'Run benchmark'}
            </button>
          </div>

          <section className="evaluation-runs">
            <div className="view-panel-header"><div><strong>Evaluation runs</strong><p className="muted-copy">Historical runs are preserved and remain separate from supplied chunk relevance labels.</p></div></div>
            {evaluationLoadError && <div className="inline-message error">{evaluationLoadError}</div>}
            {evaluationRuns.length > 0 ? (
              <div className="table-shell">
                <table>
                  <thead><tr><th>Run ID</th><th>Executed</th><th>Evaluation type</th><th>Scoring version</th><th>Cases</th><th>Target-match hit rate</th><th>MRR</th><th></th></tr></thead>
                  <tbody>
                    {evaluationRuns.map((run) => (
                      <tr key={run.run_id} className={run.run_id === activeRun?.run_id ? 'selected-row' : ''}>
                        <td><code>{run.run_id}</code></td>
                        <td>{new Date(run.created_at).toLocaleString()}</td>
                        <td>{run.dataset_name === 'KnowledgeOps Benchmark Dataset v2' ? 'Legacy v2 compatibility' : run.dataset_name}</td>
                        <td>{run.evaluation_version ?? 'Legacy / unversioned'}</td>
                        <td>{run.summary.case_count}</td>
                        <td>{run.summary.retrieval_hit_rate == null ? 'Not measured' : `${(run.summary.retrieval_hit_rate * 100).toFixed(1)}%`}</td>
                        <td>{run.summary.mean_reciprocal_rank?.toFixed(3) ?? 'Not measured'}</td>
                        <td><button type="button" className="secondary-button small" onClick={() => setSelectedRunId(run.run_id)}>{run.run_id === activeRun?.run_id ? 'Selected' : 'Inspect'}</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : !evaluationLoadError ? <p className="muted-copy">No stored evaluation runs yet.</p> : null}
          </section>

          {activeRun ? (
            <div className="benchmark-header-box">
              <div className="benchmark-title-row">
                <div>
                  <h3>{activeRun.dataset_name}</h3>
                  <p>Run ID: <code>{activeRun.run_id}</code> · Executed: {new Date(activeRun.created_at).toLocaleString()}</p>
                  <span className="chip neutral">Evaluation version: {activeRun.evaluation_version ?? 'Legacy / unversioned'}</span>
                </div>
                {isBenchmarkRun && !activeRun.evaluation_version && (
                  <div className="notice-banner">Historical values are shown unchanged from an unversioned run. These document-match, keyword-coverage, token-overlap, and citation-structure metrics are not human relevance judgments or semantic validation.</div>
                )}
                {isBenchmarkRun && activeRun.evaluation_version && (
                  <div className="notice-banner">This version uses expected-document matching, not human chunk-relevance labels. A hit requires any one expected document; recall separately measures how many expected documents were found. No metric here proves semantic relevance.</div>
                )}
                {isBenchmarkRun && (
                  <div className="chip-row">
                    <span className="chip blue">Top-K = {activeRun.configuration?.top_k ?? activeRun.configuration?.limit ?? benchmarkTopK}</span>
                    <span className={`chip ${activeRun.configuration?.mmr_enabled !== false ? 'purple' : 'neutral'}`}>
                      {activeRun.configuration?.mmr_enabled !== false ? `MMR ON (λ=${activeRun.configuration?.mmr_lambda ?? 0.70})` : 'MMR OFF'}
                    </span>
                    <span className="chip green">Cases = {activeRun.summary.case_count ?? activeRun.cases?.length ?? 0}</span>
                  </div>
                )}
              </div>

              <div className="stats-grid benchmark-summary-grid">
                {metricCards.map((metric) => (
                  <article key={metric.label} className={`stat-card ${metric.tone}`}>
                    <span className="label">{metric.label}</span>
                    <strong>{metric.value}</strong>
                  </article>
                ))}
              </div>

              {activeRun.scoring_definitions ? (
                <details className="scoring-definitions">
                  <summary>Metric definitions and limitations</summary>
                  <dl className="metadata-grid">
                    {Object.entries(activeRun.scoring_definitions).map(([metric, definition]) => (
                      <div key={metric}><dt>{metric.replaceAll('_', ' ')}</dt><dd>{definition}</dd></div>
                    ))}
                  </dl>
                </details>
              ) : isBenchmarkRun ? (
                <p className="muted-copy">This historical run has no stored scoring-version metadata. It is not recalculated here; view its displayed values as legacy expected-document / heuristic metrics.</p>
              ) : null}
              {activeRun.retrieval_source_counts && (
                <div className="chip-row evaluation-source-summary">
                  <span className="muted-copy">Retrieval source:</span>
                  {Object.entries(activeRun.retrieval_source_counts).map(([source, count]) => (
                    <span className="chip neutral" key={source}>{source}: {count} cases</span>
                  ))}
                  {Object.entries(activeRun.answer_source_counts ?? {}).map(([source, count]) => (
                    <span className="chip neutral" key={`answer-${source}`}>Answer via {source}: {count} cases</span>
                  ))}
                </div>
              )}

              {isBenchmarkRun && (
                <div className="latency-breakdown-bar">
                  {activeRun.summary.average_embedding_latency_ms != null && <span className="latency-item">Embedding: <strong>{activeRun.summary.average_embedding_latency_ms.toFixed(1)} ms</strong></span>}
                  {activeRun.summary.average_retrieval_latency_ms != null && <span className="latency-item">Retrieval: <strong>{activeRun.summary.average_retrieval_latency_ms.toFixed(1)} ms</strong></span>}
                  {activeRun.summary.average_reranking_latency_ms != null && <span className="latency-item">MMR reranking: <strong>{activeRun.summary.average_reranking_latency_ms.toFixed(1)} ms</strong></span>}
                  {activeRun.summary.average_answer_latency_ms != null && <span className="latency-item">LLM generation: <strong>{activeRun.summary.average_answer_latency_ms.toFixed(1)} ms</strong></span>}
                </div>
              )}
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
                  <span>Category: <strong>{selectedCase.category ?? 'Unknown'}</strong></span>
                  <span>Difficulty: <strong>{selectedCase.difficulty ?? 'Unknown'}</strong></span>
                  <span>Target Documents: <strong>{selectedCase.expected_documents?.join(', ') || 'Not specified'}</strong></span>
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
              {isBenchmarkRun && (
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
              )}

              <div className="table-shell">
                <table>
                  <thead>
                    <tr>
                      <th>Case Question</th>
                      {isBenchmarkRun && <th>Category</th>}
                      {isBenchmarkRun && <th>Expected Document(s)</th>}
                      <th>Retrieved Document(s)</th>
                      {isBenchmarkRun && <th>Rank</th>}
                      <th>Target match</th>
                      {isBenchmarkRun && <th>MRR</th>}
                      {isBenchmarkRun && <th>Abstention</th>}
                      {isBenchmarkRun && <th>Topic coverage</th>}
                      {isBenchmarkRun && <th>Groundedness heuristic</th>}
                      {isBenchmarkRun && <th>Citation check</th>}
                      <th>Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCases.map((c) => {
                      const retrievedDocuments = [...new Set((c.sources ?? []).map((source) => source.filename).filter(Boolean))]
                      const isHit = c.retrieval_hit
                      const isCitValid = c.citation_correctness
                      const isSelected = (c.id || c.question) === selectedCaseId

                      return (
                        <tr
                          key={c.id || c.question}
                          className={`${isHit === false || isCitValid === false || c.insufficient_evidence_correctness === false ? 'warning-row' : ''} ${isSelected ? 'selected-row' : ''}`}
                          onClick={() => setSelectedCaseId(c.id || c.question)}
                          style={{ cursor: 'pointer' }}
                        >
                          <td>
                            <strong>{c.question}</strong>
                            {c.answer && <em className="table-answer-preview">"{c.answer.substring(0, 75)}..."</em>}
                          </td>
                          {isBenchmarkRun && <td><span className="chip neutral">{c.category ?? 'Unknown'}</span></td>}
                          {isBenchmarkRun && <td><code className="doc-code">{c.expected_documents?.join(', ') || 'Not specified'}</code></td>}
                          <td><code className="doc-code">{retrievedDocuments.join(', ') || 'None'}</code></td>
                          {isBenchmarkRun && <td>{c.relevant_rank != null ? `#${c.relevant_rank}` : 'N/A'}</td>}
                          <td>
                            <span className={`status-pill ${isHit == null ? 'neutral' : isHit ? 'good' : 'bad'}`}>
                              {isHit == null ? 'Not scored' : isHit ? '✓ Target found' : '✗ Target missing'}
                            </span>
                          </td>
                          {isBenchmarkRun && <td>{c.reciprocal_rank?.toFixed(3) ?? 'N/A'}</td>}
                          {isBenchmarkRun && <td>{c.insufficient_evidence_correctness == null ? 'Not applicable' : c.insufficient_evidence_correctness ? 'Correct abstention' : 'No abstention'}</td>}
                          {isBenchmarkRun && <td>{c.answer_relevance != null ? `${(c.answer_relevance * 100).toFixed(0)}%` : 'N/A'}</td>}
                          {isBenchmarkRun && <td>{c.groundedness != null ? `${(c.groundedness * 100).toFixed(0)}%` : 'N/A'}</td>}
                          {isBenchmarkRun && <td>
                            {isCitValid == null ? 'N/A' : (
                              <span className={`status-pill ${isCitValid ? 'good' : 'warn'}`}>
                                {isCitValid ? '✓ Structure valid' : '⚠ Issue'}
                              </span>
                            )}
                          </td>}
                          <td>
                            {c.total_latency_ms != null
                              ? `${c.total_latency_ms.toFixed(1)} ms`
                              : c.retrieval_latency_ms != null
                                ? `${(c.retrieval_latency_ms + (c.answer_latency_ms ?? 0)).toFixed(1)} ms`
                                : 'N/A'}
                          </td>
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
      <PageHeader
        eyebrow="Operations"
        title="Monitoring"
        description="Review service health and the request telemetry currently captured by KnowledgeOps."
      />

      <section className="view-panel">
        {monitoringError && <div className="inline-message error">{monitoringError}</div>}
        {monitoringData ? (
          <>
            <div className="stats-grid">
              {[
                ['Documents', monitoringData.documents],
                ['Indexed documents', monitoringData.indexed_documents],
                ['Pending documents', monitoringData.pending_documents],
                ['Queries', monitoringData.queries],
                ['Requests', monitoringData.requests.requests],
                ['Successful', monitoringData.requests.requests - monitoringData.requests.errors],
                ['Failed', monitoringData.requests.errors],
                ['Success rate', monitoringData.requests.success_rate == null ? 'Not available' : `${(monitoringData.requests.success_rate * 100).toFixed(1)}%`],
                ['Average request latency', monitoringData.requests.average_latency_ms == null ? 'Not available' : `${monitoringData.requests.average_latency_ms} ms`],
                ['Qdrant points', monitoringData.collection.points_count ?? 'Not available'],
                ['Vector dimensions', monitoringData.collection.dimensions ?? 'Not available'],
                ['Requests in last hour', monitoringData.requests.requests_last_hour ?? 'Not available'],
                ['Requests / minute (last hour)', monitoringData.requests.request_rate_per_minute_last_hour == null ? 'Not available' : monitoringData.requests.request_rate_per_minute_last_hour],
              ].map(([label, value]) => (
                <article key={label} className="stat-card tone-blue"><span className="label">{label}</span><strong>{value}</strong></article>
              ))}
            </div>
            <div className="collection-config-grid">
              <section className="panel-card">
                <h3>System health</h3>
                <div className="health-list">
                  {Object.entries(monitoringData.health ?? {}).filter(([key, value]) => typeof value === 'string').map(([key, value]) => (
                    <div className="health-row" key={key}><span>{key}</span><span className={`status-pill ${pillTone(String(value))}`}>{String(value)}</span></div>
                  ))}
                </div>
              </section>
              <section className="panel-card">
                <h3>Model configuration</h3>
                <dl className="metadata-grid">
                  <div><dt>LLM model</dt><dd>{monitoringData.models.llm}</dd></div>
                  <div><dt>Embedding model</dt><dd>{monitoringData.models.embeddings}</dd></div>
                  <div><dt>Token usage / cost</dt><dd>Not collected</dd></div>
                </dl>
              </section>
            </div>
            <section className="panel-card">
              <div className="view-panel-header"><h3>Request status distribution</h3><span className="chip neutral">All persisted requests</span></div>
              <div className="chip-row">
                {Object.entries(monitoringData.requests.status_distribution ?? {}).map(([status, count]) => (
                  <span className="chip neutral" key={status}>HTTP {status}: {count}</span>
                ))}
                {!Object.keys(monitoringData.requests.status_distribution ?? {}).length && <span className="muted-copy">No request records are available.</span>}
              </div>
            </section>
            <section className="panel-card">
              <div className="view-panel-header"><h3>Latency by operation</h3><span className="chip neutral">Successful Search / Ask requests since stage telemetry was enabled</span></div>
              <div className="table-shell">
                <table>
                  <thead><tr><th>Operation</th><th>Count</th><th>Embedding</th><th>Vector retrieval</th><th>Reranking</th><th>Generation</th><th>Total</th></tr></thead>
                  <tbody>
                    {(monitoringData.operation_metrics?.by_operation ?? []).map((operation) => (
                      <tr key={operation.operation}>
                        <td>{operation.operation}</td>
                        <td>{operation.count}</td>
                        <td>{operation.average_embedding_latency_ms == null ? '—' : `${operation.average_embedding_latency_ms} ms`}</td>
                        <td>{operation.average_vector_retrieval_latency_ms == null ? '—' : `${operation.average_vector_retrieval_latency_ms} ms`}</td>
                        <td>{operation.average_reranking_latency_ms == null ? '—' : `${operation.average_reranking_latency_ms} ms`}</td>
                        <td>{operation.average_generation_latency_ms == null ? '—' : `${operation.average_generation_latency_ms} ms`}</td>
                        <td>{operation.average_total_latency_ms == null ? '—' : `${operation.average_total_latency_ms} ms`}</td>
                      </tr>
                    ))}
                    {!monitoringData.operation_metrics?.by_operation.length && (
                      <tr><td colSpan={7}>No persisted Search or Ask stage timings are available yet.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
            <section className="panel-card">
              <div className="view-panel-header"><h3>Request volume by endpoint</h3><span className="chip neutral">All persisted request history</span></div>
              <div className="table-shell">
                <table>
                  <thead><tr><th>Method / route</th><th>Requests</th><th>Successful</th><th>Failed</th><th>Average latency</th></tr></thead>
                  <tbody>
                    {(monitoringData.requests.by_endpoint ?? []).map((endpoint) => (
                      <tr key={`${endpoint.method} ${endpoint.path}`}>
                        <td><code>{endpoint.method} {endpoint.path}</code></td>
                        <td>{endpoint.requests}</td><td>{endpoint.successes}</td><td>{endpoint.errors}</td>
                        <td>{endpoint.average_latency_ms == null ? '—' : `${endpoint.average_latency_ms} ms`}</td>
                      </tr>
                    ))}
                    {!monitoringData.requests.by_endpoint?.length && <tr><td colSpan={5}>No endpoint request records are available.</td></tr>}
                  </tbody>
                </table>
              </div>
            </section>
            <section className="panel-card">
              <div className="view-panel-header"><h3>Recent failures</h3><span className="chip neutral">Latest 10 errors</span></div>
              <div className="table-shell">
                <table>
                  <thead><tr><th>Time</th><th>Method / route</th><th>Status</th><th>Latency</th><th>Request ID</th></tr></thead>
                  <tbody>
                    {(monitoringData.requests.recent_failures ?? []).map((failure) => (
                      <tr key={failure.request_id}>
                        <td>{new Date(failure.created_at).toLocaleString()}</td>
                        <td>{failure.method} {failure.path}</td>
                        <td>{failure.status_code}</td><td>{failure.latency_ms} ms</td><td><code>{failure.request_id}</code></td>
                      </tr>
                    ))}
                    {!monitoringData.requests.recent_failures?.length && <tr><td colSpan={5}>No failed requests are recorded.</td></tr>}
                  </tbody>
                </table>
              </div>
            </section>
            <div className="view-panel-header"><strong>Recent requests</strong><span className="chip neutral">Most recent first</span></div>
            {monitoringData.recent_requests?.length ? (
              <div className="table-shell">
                <table>
                  <thead><tr><th>Time</th><th>Method / route</th><th>Status</th><th>Latency</th><th>Request ID</th></tr></thead>
                  <tbody>{monitoringData.recent_requests.map((request) => (
                    <tr key={request.request_id}>
                      <td>{new Date(request.created_at).toLocaleString()}</td>
                      <td>{request.method} {request.path}</td>
                      <td>{request.status_code}</td>
                      <td>{request.latency_ms} ms</td>
                      <td><code>{request.request_id}</code></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            ) : <p className="muted-copy">No request history is available.</p>}
          </>
        ) : <div className="empty-state">Monitoring data is unavailable.</div>}
      </section>
    </>
  )

  const renderSettingsSection = () => (
    <>
      <PageHeader
        eyebrow="System"
        title="Settings"
        description="Inspect the active provider and retrieval configuration. Secrets are not shown."
      />

      <section className="view-panel">
        {settingsError && <div className="inline-message error">{settingsError}</div>}
        {settingsData ? (
          <div className="settings-grid">
            {[
              ['Application', settingsData.application],
              ['LLM provider', settingsData.llm],
              ['Embedding configuration', settingsData.embeddings],
              ['Vector database', settingsData.vector_database],
              ['Retrieval', settingsData.retrieval],
              ['Database', settingsData.database],
            ].map(([group, values]) => (
              <section key={String(group)} className="panel-card">
                <h3>{String(group)}</h3>
                <dl className="metadata-grid">
                  {Object.entries(values as Record<string, string | number | boolean>).map(([key, value]) => (
                    <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{String(value)}</dd></div>
                  ))}
                </dl>
              </section>
            ))}
            <p className="muted-copy">Configuration is read-only. Secrets and credentials are never returned.</p>
          </div>
        ) : !settingsError ? <div className="empty-state">Loading safe configuration…</div> : null}
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
      <aside className={`sidebar ${mobileNavOpen ? 'open' : ''}`}>
        <div className="sidebar-top">
          <div className="brand-box">
            <div className="brand-mark">K</div>
            <div>
              <p className="eyebrow">AI Infrastructure</p>
              <h1>KnowledgeOps</h1>
            </div>
          </div>
          <button
            type="button"
            className="menu-toggle"
            aria-label={mobileNavOpen ? 'Close navigation' : 'Open navigation'}
            aria-expanded={mobileNavOpen}
            onClick={() => setMobileNavOpen((open) => !open)}
          >
            {mobileNavOpen ? 'Close' : 'Menu'}
          </button>
        </div>

        <nav className="nav" aria-label="Main navigation">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${activeView === item.id ? 'active' : ''}`}
              type="button"
              aria-current={activeView === item.id ? 'page' : undefined}
              onClick={() => {
                setActiveView(item.id)
                setMobileNavOpen(false)
              }}
            >
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
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
      {notification && <div className="toast-message" role="status">{notification}</div>}
      {selectedPoint && (
        <PointDetailsDrawer
          point={selectedPoint}
          onClose={() => setSelectedPoint(null)}
          onCopy={(value, label) => void copyToClipboard(value, label)}
        />
      )}
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
