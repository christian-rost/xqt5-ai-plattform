function formatTokens(count) {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`
  return String(count)
}

function formatCost(cost) {
  return `$${cost.toFixed(4)}`
}

export default function UsageWidget({ usage }) {
  if (!usage) return null

  return (
    <div className="usage-widget">
      <div className="usage-title">Verbrauch</div>
      <div className="usage-row">
        <span>Tokens</span>
        <span>{formatTokens(usage.total_tokens)}</span>
      </div>
      <div className="usage-row">
        <span>Kosten</span>
        <span>{formatCost(usage.estimated_cost)}</span>
      </div>
      <div className="usage-row">
        <span>Anfragen</span>
        <span>{usage.request_count}</span>
      </div>
    </div>
  )
}
