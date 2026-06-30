import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useCampaigns } from '../hooks/useCampaigns'
import { useMcpUrl } from '../hooks/useMcpUrl'
import { useAgentActions } from '../hooks/useAgentActions'
import { useStorefront } from '../hooks/useStorefront'
import CampaignCard from '../components/CampaignCard'
import ImportProducts from '../components/ImportProducts'
import InstallPrompt from '../components/InstallPrompt'

export default function DashboardPage() {
  const { user, logout } = useAuth()
  const {
    campaigns,
    loading,
    error,
    createCampaign,
    deleteCampaign,
    updateAffiliateLink,
    bulkImport,
  } = useCampaigns()
  const { mcpUrl, loading: mcpLoading, error: mcpError, regenerate } = useMcpUrl()
  const {
    settings: storefrontSettings,
    loading: storefrontLoading,
    error: storefrontError,
    updateSettings: updateStorefrontSettings,
  } = useStorefront()
  const [storefrontName, setStorefrontName] = useState('')
  const [storefrontBio, setStorefrontBio] = useState('')
  const [savingStorefront, setSavingStorefront] = useState(false)
  const [storefrontCopied, setStorefrontCopied] = useState(false)

  useEffect(() => {
    if (storefrontSettings) {
      setStorefrontName(storefrontSettings.storefront_name)
      setStorefrontBio(storefrontSettings.storefront_bio || '')
    }
  }, [storefrontSettings])

  const handleSaveStorefront = async (e) => {
    e.preventDefault()
    setSavingStorefront(true)
    try {
      await updateStorefrontSettings(storefrontName, storefrontBio || null)
    } finally {
      setSavingStorefront(false)
    }
  }

  const handleCopyStorefront = async () => {
    if (!storefrontSettings) return
    await navigator.clipboard.writeText(storefrontSettings.storefront_url)
    setStorefrontCopied(true)
    setTimeout(() => setStorefrontCopied(false), 2000)
  }
  const {
    actions: agentActions,
    loading: agentLoading,
    error: agentError,
    agentEnabled,
    settingsLoading,
    toggleAgentEnabled,
  } = useAgentActions()
  const [togglingAgent, setTogglingAgent] = useState(false)

  const handleToggleAgent = async () => {
    setTogglingAgent(true)
    try {
      await toggleAgentEnabled(!agentEnabled)
    } finally {
      setTogglingAgent(false)
    }
  }
  const [copied, setCopied] = useState(false)
  const [regenerating, setRegenerating] = useState(false)

  const handleCopy = async () => {
    if (!mcpUrl) return
    await navigator.clipboard.writeText(mcpUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRegenerate = async () => {
    if (!window.confirm('Isso invalida a URL atual e qualquer cliente conectado com ela. Continuar?')) return
    setRegenerating(true)
    try {
      await regenerate()
    } finally {
      setRegenerating(false)
    }
  }
  const [productName, setProductName] = useState('')
  const [productUrl, setProductUrl] = useState('')
  const [affiliateLink, setAffiliateLink] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  const handleCreate = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setFormError(null)
    try {
      await createCampaign({
        product_name: productName,
        product_url: productUrl,
        affiliate_link: affiliateLink || null,
      })
      setProductName('')
      setProductUrl('')
      setAffiliateLink('')
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Erro ao criar campanha')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-10 flex items-center justify-between gap-3 bg-white px-4 py-4 shadow-sm pt-[calc(1rem+env(safe-area-inset-top))] px-safe sm:px-6">
        <h1 className="shrink-0 text-xl font-bold text-shopee">ShopeeViral.AI</h1>
        <div className="flex min-w-0 items-center gap-3 sm:gap-4">
          <span className="truncate text-sm text-gray-600">{user?.full_name || user?.email}</span>
          <button onClick={logout} className="shrink-0 text-sm text-gray-500 hover:text-shopee">
            Sair
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8 pb-[calc(2rem+env(safe-area-inset-bottom))] px-safe sm:px-6">
        <InstallPrompt />

        {!loading && campaigns.length === 0 && (
          <section className="mb-8 rounded-xl border border-orange-100 bg-orange-50 p-5 sm:p-6">
            <h2 className="mb-2 text-lg font-semibold text-gray-900">
              Bem-vindo(a)! Vamos criar sua primeira campanha
            </h2>
            <ol className="space-y-1 text-sm text-gray-700">
              <li>1. Cole o nome e o link de um produto Shopee no formulário abaixo.</li>
              <li>2. A IA gera legenda e hashtags na hora — revise e poste onde quiser.</li>
              <li>
                3. Conecte sua URL de IA (mais abaixo) se quiser criar campanhas conversando com o
                Claude, em vez de usar este painel.
              </li>
              <li>4. James, o agente autônomo, já começa a acompanhar suas campanhas sozinho.</li>
            </ol>
          </section>
        )}

        <section className="mb-8 rounded-xl bg-white p-5 shadow-sm sm:p-6">
          <h2 className="mb-4 text-lg font-semibold">Nova campanha</h2>
          <form onSubmit={handleCreate} className="grid gap-3 sm:grid-cols-3">
            <input
              type="text"
              placeholder="Nome do produto"
              required
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              className="rounded-lg border px-3 py-2 text-sm sm:col-span-1"
            />
            <input
              type="url"
              placeholder="URL do produto na Shopee"
              required
              value={productUrl}
              onChange={(e) => setProductUrl(e.target.value)}
              className="rounded-lg border px-3 py-2 text-sm sm:col-span-1"
            />
            <input
              type="url"
              placeholder="Link de afiliado (opcional)"
              value={affiliateLink}
              onChange={(e) => setAffiliateLink(e.target.value)}
              className="rounded-lg border px-3 py-2 text-sm sm:col-span-1"
            />
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-shopee px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50 sm:col-span-3"
            >
              {submitting ? 'Gerando legenda com IA...' : 'Criar campanha'}
            </button>
          </form>
          {formError && <p className="mt-2 text-sm text-red-500">{formError}</p>}
        </section>

        <ImportProducts onImported={bulkImport} />

        <section className="mb-8 rounded-xl bg-white p-5 shadow-sm sm:p-6">
          <h2 className="mb-1 text-lg font-semibold">Conectar com IA</h2>
          <p className="mb-4 text-sm text-gray-500">
            Cole esta URL no Claude Desktop (Settings → Connectors) ou em outro cliente MCP para
            pedir por conversa: criar campanhas, listar e consultar comissões.
          </p>
          {mcpLoading && <p className="text-sm text-gray-500">Carregando...</p>}
          {mcpError && <p className="text-sm text-red-500">{mcpError}</p>}
          {mcpUrl && (
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <input
                type="text"
                readOnly
                value={mcpUrl}
                onFocus={(e) => e.target.select()}
                className="flex-1 rounded-lg border bg-gray-50 px-3 py-2 text-xs text-gray-700 sm:text-sm"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleCopy}
                  className="whitespace-nowrap rounded-lg bg-shopee px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
                >
                  {copied ? 'Copiado!' : 'Copiar'}
                </button>
                <button
                  onClick={handleRegenerate}
                  disabled={regenerating}
                  className="whitespace-nowrap rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                >
                  {regenerating ? 'Gerando...' : 'Gerar nova URL'}
                </button>
              </div>
            </div>
          )}
        </section>

        <section className="mb-8 rounded-xl bg-white p-5 shadow-sm sm:p-6">
          <h2 className="mb-1 text-lg font-semibold">Sua vitrine pública</h2>
          <p className="mb-4 text-sm text-gray-500">
            Uma página pública (estilo link na bio) com as campanhas que já têm link de
            afiliado e estão agendadas ou publicadas — pronta para compartilhar com seus
            seguidores.
          </p>
          {storefrontLoading && <p className="text-sm text-gray-500">Carregando...</p>}
          {storefrontError && <p className="text-sm text-red-500">{storefrontError}</p>}
          {storefrontSettings && (
            <>
              <form onSubmit={handleSaveStorefront} className="mb-3 grid gap-3 sm:grid-cols-2">
                <input
                  type="text"
                  placeholder="Nome da vitrine"
                  required
                  value={storefrontName}
                  onChange={(e) => setStorefrontName(e.target.value)}
                  className="rounded-lg border px-3 py-2 text-sm"
                />
                <input
                  type="text"
                  placeholder="Bio (opcional)"
                  value={storefrontBio}
                  onChange={(e) => setStorefrontBio(e.target.value)}
                  className="rounded-lg border px-3 py-2 text-sm"
                />
                <button
                  type="submit"
                  disabled={savingStorefront}
                  className="rounded-lg bg-shopee px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50 sm:col-span-2"
                >
                  {savingStorefront ? 'Salvando...' : 'Salvar'}
                </button>
              </form>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <input
                  type="text"
                  readOnly
                  value={storefrontSettings.storefront_url}
                  onFocus={(e) => e.target.select()}
                  className="flex-1 rounded-lg border bg-gray-50 px-3 py-2 text-xs text-gray-700 sm:text-sm"
                />
                <button
                  onClick={handleCopyStorefront}
                  className="whitespace-nowrap rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
                >
                  {storefrontCopied ? 'Copiado!' : 'Copiar'}
                </button>
                <a
                  href={storefrontSettings.storefront_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="whitespace-nowrap rounded-lg bg-shopee px-4 py-2 text-center text-sm font-semibold text-white hover:opacity-90"
                >
                  Ver vitrine
                </a>
              </div>
            </>
          )}
        </section>

        <section className="mb-8 rounded-xl bg-white p-5 shadow-sm sm:p-6">
          <div className="mb-1 flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-lg font-semibold">James, seu agente autônomo</h2>
            <button
              onClick={handleToggleAgent}
              disabled={settingsLoading || togglingAgent}
              className={`whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold disabled:opacity-50 ${
                agentEnabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
              }`}
            >
              {togglingAgent ? '...' : agentEnabled ? 'Ativo · clique para desligar' : 'Desligado · clique para ativar'}
            </button>
          </div>
          <p className="mb-4 text-sm text-gray-500">
            James roda em background e age sozinho: promove rascunhos esquecidos, renova
            legendas de campanhas que não venderam e sugere replicar campanhas que já venderam
            — sem você precisar pedir.
          </p>
          {agentLoading && <p className="text-sm text-gray-500">Carregando...</p>}
          {agentError && <p className="text-sm text-red-500">{agentError}</p>}
          {!agentLoading && agentActions.length === 0 && (
            <p className="text-sm text-gray-500">
              James ainda não tomou nenhuma ação — ele revisa suas campanhas periodicamente.
            </p>
          )}
          <ul className="space-y-2">
            {agentActions.map((a) => (
              <li key={a.id} className="rounded-lg border p-3 text-sm">
                <span className="mr-2 inline-block rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                  {a.action_type}
                </span>
                <span className="text-gray-700">{a.description}</span>
                <p className="mt-1 text-xs text-gray-400">
                  {new Date(a.created_at).toLocaleString('pt-BR')}
                </p>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl bg-white p-5 shadow-sm sm:p-6">
          <h2 className="mb-4 text-lg font-semibold">Campanhas</h2>
          {loading && <p className="text-sm text-gray-500">Carregando...</p>}
          {error && <p className="text-sm text-red-500">{error}</p>}
          {!loading && campaigns.length === 0 && (
            <p className="text-sm text-gray-500">Nenhuma campanha criada ainda.</p>
          )}
          <ul className="space-y-3">
            {campaigns.map((c) => (
              <CampaignCard
                key={c.id}
                campaign={c}
                onDelete={deleteCampaign}
                onUpdateLink={updateAffiliateLink}
              />
            ))}
          </ul>
        </section>
      </main>
    </div>
  )
}
