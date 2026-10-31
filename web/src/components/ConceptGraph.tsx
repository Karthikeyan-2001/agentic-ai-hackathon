import dagre from '@dagrejs/dagre'
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useMemo, useState } from 'react'
import { percent } from '../api'
import type { ConceptView } from '../types'

const NODE_WIDTH = 190
const NODE_HEIGHT = 62

function colours(concept: ConceptView): { background: string; border: string; label: string } {
  if (!concept.assessed) return { background: 'var(--color-none)', border: 'var(--color-line)', label: 'Not assessed' }
  if (concept.displayed_mastery < 0.4) {
    return { background: 'var(--color-bad-soft)', border: 'var(--color-bad)', label: percent(concept.displayed_mastery) }
  }
  if (concept.displayed_mastery < 0.7) {
    return { background: 'var(--color-warn-soft)', border: 'var(--color-warn)', label: percent(concept.displayed_mastery) }
  }
  return { background: 'var(--color-good-soft)', border: 'var(--color-good)', label: percent(concept.displayed_mastery) }
}

function layout(concepts: ConceptView[]): { nodes: Node[]; edges: Edge[] } {
  const ids = new Set(concepts.map((concept) => concept.id))
  const graph = new dagre.graphlib.Graph()
  graph.setGraph({ rankdir: 'LR', nodesep: 18, ranksep: 46 })
  graph.setDefaultEdgeLabel(() => ({}))
  concepts.forEach((concept) => graph.setNode(concept.id, { width: NODE_WIDTH, height: NODE_HEIGHT }))
  const edges: Edge[] = []
  concepts.forEach((concept) => {
    concept.prerequisites
      .filter((prerequisite) => ids.has(prerequisite))
      .forEach((prerequisite) => {
        graph.setEdge(prerequisite, concept.id)
        edges.push({ id: `${prerequisite}-${concept.id}`, source: prerequisite, target: concept.id })
      })
  })
  dagre.layout(graph)

  const nodes = concepts.map((concept): Node => {
    const position = graph.node(concept.id)
    const colour = colours(concept)
    return {
      id: concept.id,
      position: { x: position.x - NODE_WIDTH / 2, y: position.y - NODE_HEIGHT / 2 },
      data: {
        label: (
          <div className="text-left">
            <div className="text-xs leading-tight font-semibold">{concept.name}</div>
            <div className="mt-1 text-xs">{colour.label}</div>
          </div>
        ),
      },
      draggable: false,
      connectable: false,
      sourcePosition: 'right' as Node['sourcePosition'],
      targetPosition: 'left' as Node['targetPosition'],
      style: {
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        padding: 8,
        background: colour.background,
        border: `1.5px solid ${colour.border}`,
        borderRadius: 8,
        color: 'var(--color-ink)',
      },
    }
  })
  return { nodes, edges }
}

export function ConceptGraph({ concepts }: { concepts: ConceptView[] }) {
  const chapters = useMemo(() => [...new Set(concepts.map((concept) => concept.chapter))], [concepts])
  const [chapter, setChapter] = useState('Electricity')
  const visible = useMemo(() => concepts.filter((concept) => concept.chapter === chapter), [concepts, chapter])
  const { nodes, edges } = useMemo(() => layout(visible), [visible])

  return (
    <section className="rounded-lg border border-line bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-semibold">Concept map</h2>
        <label className="text-sm">
          <span className="sr-only">Chapter</span>
          <select
            value={chapter}
            onChange={(event) => setChapter(event.target.value)}
            className="rounded-md border border-line bg-card px-2 py-1"
          >
            {chapters.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="mt-3 h-[26rem] rounded-md border border-line" key={chapter}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          nodesDraggable={false}
          nodesConnectable={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={20} color="var(--color-line)" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <p className="mt-2 text-xs text-mute">
        Arrows run from a prerequisite to the concept that needs it. Mastery fades over time until it's reviewed.
      </p>
    </section>
  )
}
