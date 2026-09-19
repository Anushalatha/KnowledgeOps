import './style.css'

const appRoot = document.querySelector<HTMLDivElement>('#app')

if (!appRoot) {
  throw new Error('App root element not found')
}

appRoot.innerHTML = '<p>KnowledgeOps frontend ready.</p>'
