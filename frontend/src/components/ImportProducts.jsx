import { useState } from 'react'

// Parser de CSV simples que lida com campos entre aspas e virgulas/ponto-e-virgula.
// Suficiente pro caso de uso (planilha de produtos exportada do Excel como CSV).
function parseCSV(text) {
  const rows = []
  let field = ''
  let row = []
  let inQuotes = false
  const delimiter = text.includes(';') && !text.split('\n')[0].includes(',') ? ';' : ','

  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (inQuotes) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"'
        i++
      } else if (ch === '"') {
        inQuotes = false
      } else {
        field += ch
      }
    } else if (ch === '"') {
      inQuotes = true
    } else if (ch === delimiter) {
      row.push(field)
      field = ''
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++
      row.push(field)
      rows.push(row)
      field = ''
      row = []
    } else {
      field += ch
    }
  }
  if (field !== '' || row.length > 0) {
    row.push(field)
    rows.push(row)
  }
  return rows.filter((r) => r.some((c) => c.trim() !== ''))
}

// Mapeia colunas por nome (flexivel: aceita variacoes comuns dos cabecalhos).
function extractItems(rows) {
  if (rows.length < 2) return []
  const header = rows[0].map((h) => h.trim().toLowerCase())

  const findCol = (...names) => {
    for (const name of names) {
      const idx = header.findIndex((h) => h.includes(name))
      if (idx >= 0) return idx
    }
    return -1
  }

  const nameCol = findCol('produto', 'nome', 'product')
  const urlCol = findCol('url_produto', 'url do produto', 'product_url', 'url', 'link do produto')
  const affCol = findCol('link_afiliado', 'link de afiliado', 'affiliate', 's.shopee')

  if (nameCol < 0 || urlCol < 0) return []

  const items = []
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i]
    const name = (r[nameCol] || '').trim()
    const url = (r[urlCol] || '').trim()
    if (!name || !url || !url.startsWith('http')) continue
    const aff = affCol >= 0 ? (r[affCol] || '').trim() : ''
    items.push({
      product_name: name,
      product_url: url,
      affiliate_link: aff && aff.startsWith('http') ? aff : null,
    })
  }
  return items
}

export default function ImportProducts({ onImported }) {
  const [rawText, setRawText] = useState('')
  const [preview, setPreview] = useState([])
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleText = (text) => {
    setRawText(text)
    setResult(null)
    setError(null)
    try {
      const items = extractItems(parseCSV(text))
      setPreview(items)
      if (text.trim() && items.length === 0) {
        setError('Não reconheci as colunas. A planilha precisa de uma coluna de nome (produto) e uma de URL (url_produto).')
      }
    } catch {
      setPreview([])
    }
  }

  const handleFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const text = await file.text()
    handleText(text)
  }

  const handleImport = async () => {
    if (preview.length === 0) return
    setImporting(true)
    setError(null)
    try {
      const res = await onImported(preview)
      setResult(res)
      setRawText('')
      setPreview([])
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao importar')
    } finally {
      setImporting(false)
    }
  }

  return (
    <section className="mb-8 rounded-xl bg-white p-5 shadow-sm sm:p-6">
      <h2 className="mb-1 text-lg font-semibold">Importar produtos em lote</h2>
      <p className="mb-4 text-sm text-gray-500">
        Cole as linhas da sua planilha ou envie um arquivo CSV. Precisa ter pelo menos uma
        coluna de <strong>produto</strong> e uma de <strong>url_produto</strong> (a coluna
        <strong> link_afiliado</strong> é opcional). No Excel: Arquivo → Salvar como → CSV.
      </p>

      <div className="mb-3 flex flex-col gap-3">
        <textarea
          rows={4}
          placeholder="produto,url_produto,link_afiliado&#10;Caneca térmica,https://shopee.com.br/...,https://s.shopee.com.br/..."
          value={rawText}
          onChange={(e) => handleText(e.target.value)}
          className="w-full rounded-lg border px-3 py-2 font-mono text-xs"
        />
        <div className="flex flex-wrap items-center gap-3">
          <label className="cursor-pointer rounded-lg border px-3 py-2 text-xs text-gray-600 hover:bg-gray-50">
            Enviar arquivo CSV
            <input type="file" accept=".csv,text/csv" onChange={handleFile} className="hidden" />
          </label>
          {preview.length > 0 && (
            <span className="text-xs text-gray-500">{preview.length} produto(s) reconhecido(s)</span>
          )}
        </div>
      </div>

      {error && <p className="mb-3 text-sm text-red-500">{error}</p>}

      {preview.length > 0 && (
        <div className="mb-3 max-h-40 overflow-y-auto rounded-lg border">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 text-gray-500">
              <tr>
                <th className="px-3 py-2">Produto</th>
                <th className="px-3 py-2">Link afiliado?</th>
              </tr>
            </thead>
            <tbody>
              {preview.slice(0, 50).map((p, i) => (
                <tr key={i} className="border-t">
                  <td className="px-3 py-1.5">{p.product_name}</td>
                  <td className="px-3 py-1.5">{p.affiliate_link ? '✓' : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {result && (
        <p className="mb-3 text-sm text-green-700">
          {result.criadas} campanha(s) criada(s)
          {result.ignoradas_duplicadas > 0 && `, ${result.ignoradas_duplicadas} ignorada(s) por já existir`}.
        </p>
      )}

      <button
        onClick={handleImport}
        disabled={importing || preview.length === 0}
        className="rounded-lg bg-shopee px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
      >
        {importing ? 'Criando campanhas com IA...' : `Importar ${preview.length || ''} produto(s)`}
      </button>
    </section>
  )
}
