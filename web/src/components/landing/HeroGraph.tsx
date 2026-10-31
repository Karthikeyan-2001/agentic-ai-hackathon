type NodeState = 'weak' | 'partial' | 'strong' | 'unknown'

interface GraphNode {
  id: string
  label: string
  x: number
  y: number
  state: NodeState
  prerequisites: string[]
}

// The real Python prerequisites from content/concepts.json, shown for one example student.
const NODES: GraphNode[] = [
  { id: 'variables', label: 'Variables', x: 45, y: 235, state: 'strong', prerequisites: [] },
  { id: 'types', label: 'Data types', x: 160, y: 235, state: 'partial', prerequisites: ['variables'] },
  { id: 'arithmetic', label: 'Arithmetic', x: 280, y: 115, state: 'strong', prerequisites: ['types'] },
  { id: 'comparison', label: 'Comparison', x: 280, y: 320, state: 'unknown', prerequisites: ['types'] },
  { id: 'indexing', label: 'List indexing', x: 410, y: 40, state: 'strong', prerequisites: ['arithmetic'] },
  { id: 'ifElse', label: 'if and else', x: 410, y: 320, state: 'unknown', prerequisites: ['comparison'] },
  { id: 'forRange', label: 'for with range', x: 540, y: 320, state: 'weak', prerequisites: ['ifElse'] },
  { id: 'functions', label: 'Functions', x: 540, y: 190, state: 'unknown', prerequisites: ['ifElse', 'arithmetic'] },
  { id: 'traversal', label: 'List traversal', x: 665, y: 60, state: 'partial', prerequisites: ['indexing', 'forRange'] },
  { id: 'totals', label: 'Running totals', x: 665, y: 165, state: 'partial', prerequisites: ['forRange', 'arithmetic'] },
  { id: 'nested', label: 'Nested loops', x: 665, y: 270, state: 'weak', prerequisites: ['forRange', 'arithmetic'] },
  { id: 'whileLoops', label: 'while loops', x: 665, y: 385, state: 'partial', prerequisites: ['forRange', 'comparison'] },
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
        aria-label="Concept graph of 12 Python concepts linked by prerequisites. For this example student, for loops with range and nested loops are weak."
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
            {node.id === 'forRange' &&<circle cx={node.x} cy={node.y} r={13} fill={FILL.weak} className="graph-ripple" />}
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
