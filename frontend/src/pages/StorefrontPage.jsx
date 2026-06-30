import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../lib/api'

const STYLE = `
  .storefront-page {
    margin: 0;
    font-family: 'Inter', sans-serif;
    color: #2b2330;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: calc(48px + env(safe-area-inset-top)) calc(16px + env(safe-area-inset-right))
      calc(100px + env(safe-area-inset-bottom)) calc(16px + env(safe-area-inset-left));
    position: relative;
    overflow-x: hidden;
    background: linear-gradient(-45deg, #ffdee9, #ffe9d6, #f7d6ff, #ffd1e3);
    background-size: 400% 400%;
    animation: sfGradientShift 14s ease infinite;
  }
  @keyframes sfGradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }
  .sf-sparkle {
    position: fixed;
    font-size: 22px;
    opacity: 0.55;
    animation: sfFloat 6s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
  }
  @keyframes sfFloat {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-18px) rotate(12deg); }
  }
  .sf-badge-top {
    position: relative;
    z-index: 1;
    background: linear-gradient(90deg, #ff5e8e, #a25cff);
    color: #fff;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.04em;
    padding: 6px 16px;
    border-radius: 999px;
    margin-bottom: 18px;
    box-shadow: 0 6px 18px rgba(162, 92, 255, 0.35);
  }
  .sf-avatar-ring {
    width: 104px;
    height: 104px;
    border-radius: 50%;
    background: linear-gradient(135deg, #ff5e8e, #a25cff, #ffcf5c);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 18px;
    animation: sfSpin 8s linear infinite;
  }
  @keyframes sfSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  .sf-avatar {
    width: 92px;
    height: 92px;
    border-radius: 50%;
    background: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 42px;
  }
  .sf-page h1 {
    position: relative;
    z-index: 1;
    font-family: 'Poppins', sans-serif;
    font-size: 28px;
    font-weight: 800;
    margin: 0 0 6px;
    text-align: center;
    background: linear-gradient(90deg, #ff5e8e, #a25cff);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
  .sf-bio {
    position: relative;
    z-index: 1;
    color: #7a6f7d;
    font-size: 14px;
    text-align: center;
    max-width: 340px;
    margin: 0 0 32px;
    line-height: 1.5;
  }
  .sf-links {
    position: relative;
    z-index: 1;
    width: 100%;
    max-width: 440px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .sf-link-card {
    position: relative;
    display: flex;
    align-items: center;
    gap: 14px;
    background: rgba(255, 255, 255, 0.55);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.8);
    border-radius: 18px;
    padding: 16px 20px;
    color: #2b2330;
    text-decoration: none;
    font-size: 15px;
    font-weight: 600;
    box-shadow: 0 4px 14px rgba(162, 92, 255, 0.1);
    transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    opacity: 0;
    animation: sfFadeInUp 0.5s ease forwards;
  }
  .sf-link-card:hover {
    transform: translateY(-3px) scale(1.015);
    box-shadow: 0 10px 26px rgba(255, 94, 142, 0.28);
    background: rgba(255, 255, 255, 0.8);
  }
  .sf-link-card .sf-icon { font-size: 22px; flex-shrink: 0; }
  .sf-link-card .sf-label { flex: 1; }
  .sf-link-card .sf-tag {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.04em;
    padding: 4px 9px;
    border-radius: 999px;
    color: #fff;
    flex-shrink: 0;
    white-space: nowrap;
    background: linear-gradient(90deg, #ff5e8e, #ff8a5e);
  }
  @keyframes sfFadeInUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .sf-footer {
    position: relative;
    z-index: 1;
    margin-top: 44px;
    color: #7a6f7d;
    font-size: 12px;
    text-align: center;
  }
  .sf-empty {
    position: relative;
    z-index: 1;
    color: #7a6f7d;
    font-size: 14px;
    text-align: center;
    margin-top: 24px;
  }
`

export default function StorefrontPage() {
  const { userId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api
      .get(`/public/storefront/${userId}`)
      .then((res) => setData(res.data))
      .catch(() => setError('Vitrine não encontrada.'))
  }, [userId])

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center text-gray-500">{error}</div>
    )
  }

  if (!data) {
    return <div className="flex min-h-screen items-center justify-center text-gray-500">Carregando...</div>
  }

  return (
    <>
      <style>{STYLE}</style>
      <div className="storefront-page sf-page">
        <span className="sf-sparkle" style={{ top: '8%', left: '8%' }}>✨</span>
        <span className="sf-sparkle" style={{ top: '18%', right: '10%', fontSize: 16 }}>💖</span>
        <span className="sf-sparkle" style={{ top: '60%', left: '5%', fontSize: 28 }}>🌸</span>
        <span className="sf-sparkle" style={{ top: '75%', right: '8%' }}>✨</span>
        <span className="sf-sparkle" style={{ top: '40%', right: '4%', fontSize: 14 }}>💎</span>

        <div className="sf-badge-top">✨ CURADORIA ATUALIZADA</div>

        <div className="sf-avatar-ring">
          <div className="sf-avatar">🛍️</div>
        </div>

        <h1>{data.storefront_name}</h1>
        {data.storefront_bio && <p className="sf-bio">{data.storefront_bio}</p>}

        <div className="sf-links">
          {data.campaigns.map((c, i) => (
            <a
              key={i}
              className="sf-link-card"
              href={c.affiliate_link}
              target="_blank"
              rel="noopener noreferrer"
              style={{ animationDelay: `${0.05 + i * 0.05}s` }}
            >
              <span className="sf-icon">🛍️</span>
              <span className="sf-label">{c.product_name}</span>
              {c.featured && <span className="sf-tag">MAIS VENDIDO</span>}
            </a>
          ))}
        </div>

        {data.campaigns.length === 0 && (
          <p className="sf-empty">Nenhum produto disponível por aqui ainda — volte em breve!</p>
        )}

        <footer className="sf-footer">
          Feito com 💕 via ShopeeViral.AI
        </footer>
      </div>
    </>
  )
}
