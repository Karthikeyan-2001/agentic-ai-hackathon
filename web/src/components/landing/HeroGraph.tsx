type NodeState = 'weak' | 'partial' | 'strong' | 'unknown'

interface GraphNode {
  id: string
  label: string
  x: number
  y: number
  state: NodeState
  prerequisites: string[]
}

// The real Electricity prerequisites from content/concepts.json, shown for one example student.
const NODES: GraphNode[] = [
  { id: 'charge', label: 'Charge', x: 45, y: 235, state: 'unknown', prerequisites: [] },
  { id: 'current', label: 'Current', x: 160, y: 235, state: 'partial', prerequisites: ['charge'] },
  { id: 'voltage', label: 'Voltage', x: 280, y: 115, state: 'strong', prerequisites: ['current'] },
  { id: 'series', label: 'Series current', x: 280, y: 320, state: 'weak', prerequisites: ['current'] },
  { id: 'ohm', label: "Ohm's law", x: 410, y: 115, state: 'strong', prerequisites: ['current', 'voltage'] },
  { id: 'parallelCurrent', label: 'Parallel current', x: 410, y: 390, state: 'partial', prerequisites: ['series', 'voltage'] },
  { id: 'factors', label: 'Resistance factors', x: 540, y: 40, state: 'strong', prerequisites: ['ohm'] },
  { id: 'power', label: 'Power', x: 540, y: 135, state: 'partial', prerequisites: ['ohm'] },
  { id: 'seriesResistance', label: 'Series resistance', x: 540, y: 245, state: 'weak', prerequisites: ['series', 'ohm'] },
  { id: 'parallelResistance', label: 'Parallel resistance', x: 540, y: 390, state: 'partial', prerequisites: ['parallelCurrent', 'ohm'] },
  { id: 'energy', label: 'Energy', x: 665, y: 90, state: 'partial', prerequisites: ['power'] },
  { id: 'heating', label: 'Heating', x: 665, y: 190, state: 'unknown', prerequisites: ['power'] },
]

const BY_ID = new Map(NODES.map((node) => [node.id, node]))

const FILL: Record<NodeState, string> = {
  weak: 'var(--color-bad)',
  partial: 'var(--color-warn)',
  strong: 'var(--color-good)',
  unknown: 'var(--color-none)',
}

export function HeroGraph() {
  const edges = NODES.flatMap((node) =>
    node.prerequisites.map((prerequisite) => {
      const from = BY_ID.get(prerequisite)!
      const middle = (from.x + node.x) / 2
      return {
        key: `${prerequisite}-${node.id}`,
        path: `M ${from.x} ${from.y} C ${middle} ${from.y}, ${middle} ${node.y}, ${node.x} ${node.y}`,
        delay: from.x / 900,
      }
    }),
  )

  return (
    <figure className="w-full">
      <svg
        viewBox="0 0 720 440"
        role="img"
        aria-label="Concept graph of 12 Electricity concepts linked by prerequisites. For this example student, Series current and Series resistance are weak."
        className="h-auto w-full"
      >
        {edges.map((edge) => (
          <path
            key={edge.key}
            d={edge.path}
            pathLength={1}
            fill="none"
            stroke="var(--color-mute)"
            strokeOpacity={0.45}
            strokeWidth={1.5}
            className="graph-edge"
            style={{ animationDelay: `${edge.delay}s` }}
          />
        ))}
        {NODES.map((node) => (
          <g key={node.id} className="graph-node" style={{ animationDelay: `${0.25 + node.x / 900}s` }}>
            {node.id === 'series' && <circle cx={node.x} cy={node.y} r={13} fill={FILL.weak} className="graph-ripple" />}
            <circle
              cx={node.x}
              cy={node.y}
              r={13}
              fill={FILL[node.state]}
              stroke={node.state === 'unknown' ? 'var(--color-mute)' : 'var(--color-paper)'}
              strokeWidth={node.state === 'unknown' ? 1.5 : 3}
            />
            <text
              x={node.x}
              y={node.y + 32}
              textAnchor="middle"
              fontSize={15}
              fontWeight={500}
              fill="var(--color-ink)"
              className="max-md:hidden"
            >
              {node.label}
            </text>
          </g>
        ))}
      </svg>
      <figcaption className="mt-3 text-sm text-mute">
        Mastery across prerequisites for one example student. Red is weak, amber is partial, green is strong and grey is
        not assessed.
      </figcaption>
    </figure>
  )
}
