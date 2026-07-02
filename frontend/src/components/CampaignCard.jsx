import { useState } from 'react'

const STATUS_LABELS = {
  draft: { text: 'rascunho', cls: 'bg-gray-100 text-gray-600' },
  scheduled: { text: 'agendada', cls: 'bg-blue-100 text-blue-700' },
  posted: { text: 'publicada', cls: 'bg-green-100 text-green-700' },
  failed: { text: 'falhou', cls: 'bg-red-100 text-red-700' },
  needs_review: { text: 'precisa revisão', cls: 'bg-amber-100 text-amber-700' },
}

const SHOPEE_CUSTOM_LINK_URL = 'https://affiliate.shopee.com.br/offer/custom_link'

export default function CampaignCard({ campaign, onDelete, onUpdateLink, onUpdateProductUrl }) {
  const [linkValue, setLinkValue] = useState(campaign.affiliate_link || '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [editing, setEditing] = useState(!campaign.affiliate_link)
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [urlValue, setUrlValue] = useState('')
  const [savingUrl, setSavingUrl] = useState(false)

  const handleFixUrl = async () => {
    if (!urlValue.trim()) return
    setSavingUrl(true)
    try {
      await onUpdateProductUrl(campaign.id, urlValue.trim())
      setUrlValue('')
    } finally {
      setSavingUrl(false)
    }
  }

  const handleCopyProductUrl = async () => {
    await navigator.clipboard.writeText(campaign.product_url)
    setCopiedUrl(true)
    setTimeout(() => setCopiedUrl(false), 2000)
  }

  const status = STATUS_LABELS[campaign.status] || { text: campaign.status, cls: 'bg-gray-100 text-gray-600' }

  const handleSaveLink = async () => {
    if (!linkValue.trim()) return
    setSaving(true)
    try {
      await onUpdateLink(campaign.id, linkValue.trim())
      setSaved(true)
      setEditing(false)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <li className="rounded-lg border p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-medium">{campaign.product_name}</p>
          <p className="text-sm text-gray-600">{campaign.caption}</p>
          <p className="text-xs text-gray-500">{campaign.hashtags}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className={`inline-block rounded px-2 py-0.5 text-xs ${status.cls}`}>{status.text}</span>
            {campaign.affiliate_link && !editing && (
              <span className="inline-block rounded bg-green-50 px-2 py-0.5 text-xs text-green-700">
                ✓ com link de afiliado
              </span>
            )}
          </div>
          {campaign.status_detail && (
            <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-2">
              <p className="text-xs text-amber-700">{campaign.status_detail}</p>
              {onUpdateProductUrl && (
                <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                  <input
                    type="url"
                    aria-label="Corrigir URL do produto"
                    placeholder="Cole a URL do produto: shopee.com.br/...-i.LOJA.ITEM"
                    value={urlValue}
                    onChange={(e) => setUrlValue(e.target.value)}
                    className="flex-1 rounded-lg border px-3 py-2 text-xs"
                  />
                  <button
                    onClick={handleFixUrl}
                    disabled={savingUrl || !urlValue.trim()}
                    className="whitespace-nowrap rounded-lg bg-shopee-dark px-3 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
                  >
                    {savingUrl ? 'Corrigindo...' : 'Corrigir URL'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
        <button onClick={() => onDelete(campaign.id)} className="shrink-0 text-xs text-red-600 hover:underline">
          Remover
        </button>
      </div>

      <div className="mt-3 border-t pt-3">
        {!editing && campaign.affiliate_link ? (
          <div className="flex items-center justify-between gap-2">
            <a
              href={campaign.affiliate_link}
              target="_blank"
              rel="noopener noreferrer"
              className="truncate text-xs text-shopee-dark hover:underline"
            >
              {campaign.affiliate_link}
            </a>
            <button
              onClick={() => setEditing(true)}
              className="shrink-0 text-xs text-gray-500 hover:text-shopee"
            >
              Editar link
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <ol className="space-y-0.5 text-xs text-gray-500">
              <li>1. Clique em "Gerar link" (abre a ferramenta da Shopee em outra aba).</li>
              <li>2. Cole a URL do produto lá (use "Copiar URL" abaixo) e clique em "Obter link".</li>
              <li>3. Copie o link gerado, volte aqui e cole no campo abaixo.</li>
            </ol>
            <div className="flex gap-2">
              <a
                href={SHOPEE_CUSTOM_LINK_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="whitespace-nowrap rounded-lg border px-3 py-2 text-xs text-gray-600 hover:bg-gray-50"
              >
                Gerar link ↗
              </a>
              <button
                onClick={handleCopyProductUrl}
                className="whitespace-nowrap rounded-lg border px-3 py-2 text-xs text-gray-600 hover:bg-gray-50"
              >
                {copiedUrl ? 'URL copiada!' : 'Copiar URL do produto'}
              </button>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                type="url"
                placeholder="Cole aqui: https://s.shopee.com.br/..."
                value={linkValue}
                onChange={(e) => setLinkValue(e.target.value)}
                className="flex-1 rounded-lg border px-3 py-2 text-xs"
              />
              <button
                onClick={handleSaveLink}
                disabled={saving || !linkValue.trim()}
                className="whitespace-nowrap rounded-lg bg-shopee-dark px-3 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
              >
                {saving ? 'Salvando...' : saved ? 'Salvo!' : 'Salvar link'}
              </button>
            </div>
          </div>
        )}
      </div>
    </li>
  )
}
