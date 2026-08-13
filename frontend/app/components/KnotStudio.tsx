"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";
import {
  add,
  allSegments,
  createDefaultPlanar,
  cubicDerivative,
  distance,
  findSegment,
  makeId,
  nodesFromPoints,
  normalizedTangent,
  pathData,
  reconcilePlanar,
  scale,
  simplifyPoints,
  subtract,
} from "../core/geometry";
import { applyProject, createWorkspace, makeProject, parseProject } from "../core/project";
import type {
  BezierNode,
  BraidDocument,
  KnotComponent,
  PlanarDocument,
  Point,
  WorkspaceState,
} from "../core/types";

type Mode = "planar" | "braid";
type PlanarTool = "select" | "pen" | "freehand" | "crossing" | "pan";
type BraidTool = "select" | "positive" | "negative";
type ViewBox = { x: number; y: number; width: number; height: number };
type Selection = { componentId: string; nodeId?: string } | null;
type History = { past: WorkspaceState[]; present: WorkspaceState; future: WorkspaceState[] };

const PALETTE = ["#2f635d", "#a75d43", "#6f6598", "#ab7b28", "#446f9a"];
const INITIAL_VIEW: ViewBox = { x: 0, y: 0, width: 960, height: 680 };
const AUTOSAVE_KEY = "knot-drawer-autosave-v1";

function sameWorkspace(first: WorkspaceState, second: WorkspaceState): boolean {
  return JSON.stringify(first) === JSON.stringify(second);
}

function download(name: string, content: string, type: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

function safeFileName(title: string): string {
  return title.trim().replace(/[\\/:*?"<>|]+/g, "-") || "knot-diagram";
}

function updateComponent(
  document: PlanarDocument,
  componentId: string,
  transform: (component: KnotComponent) => KnotComponent,
): PlanarDocument {
  return reconcilePlanar({
    ...document,
    components: document.components.map((component) =>
      component.id === componentId ? transform(component) : component,
    ),
  });
}

function projectPoint(svg: SVGSVGElement, clientX: number, clientY: number): Point {
  const point = svg.createSVGPoint();
  point.x = clientX;
  point.y = clientY;
  const matrix = svg.getScreenCTM();
  if (!matrix) return { x: clientX, y: clientY };
  const result = point.matrixTransform(matrix.inverse());
  return { x: result.x, y: result.y };
}

function ToolButton({
  active,
  icon,
  label,
  shortcut,
  onClick,
}: {
  active?: boolean;
  icon: string;
  label: string;
  shortcut?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`tool-button${active ? " active" : ""}`}
      onClick={onClick}
      aria-pressed={active}
      title={shortcut ? `${label} (${shortcut})` : label}
    >
      <span className="tool-icon" aria-hidden="true">{icon}</span>
      <span>{label}</span>
      {shortcut && <kbd>{shortcut}</kbd>}
    </button>
  );
}

function IconButton({
  label,
  icon,
  disabled,
  onClick,
}: {
  label: string;
  icon: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button type="button" className="icon-button" onClick={onClick} disabled={disabled} title={label}>
      <span aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </button>
  );
}

function EmptyGuide({ mode }: { mode: Mode }) {
  return (
    <div className="empty-guide">
      <div className="empty-knot" aria-hidden="true">∞</div>
      <strong>{mode === "planar" ? "从一条闭合曲线开始" : "添加第一个辫生成元"}</strong>
      <span>{mode === "planar" ? "使用钢笔精确绘制，或用手绘快速起稿" : "从右侧选择 σᵢ 或 σᵢ⁻¹"}</span>
    </div>
  );
}

function BraidCanvas({
  document,
  selectedIndex,
  onSelect,
  artworkRef,
}: {
  document: BraidDocument;
  selectedIndex: number | null;
  onSelect: (index: number | null) => void;
  artworkRef: React.RefObject<SVGGElement | null>;
}) {
  const geometry = useMemo(() => buildBraidGeometry(document), [document]);
  return (
    <svg
      className="editor-svg"
      viewBox="0 0 960 680"
      role="img"
      aria-label="辫图编辑画布"
      onPointerDown={() => onSelect(null)}
    >
      <defs>
        <pattern id="braid-grid" width="24" height="24" patternUnits="userSpaceOnUse">
          <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#e7e4dc" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="960" height="680" fill="#fbfaf6" />
      <rect width="960" height="680" fill="url(#braid-grid)" opacity="0.72" />
      <g ref={artworkRef}>
        {geometry.paths.map((path, index) => (
          <path
            key={index}
            d={path}
            fill="none"
            stroke="#223c39"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}
        {geometry.closures.map((path, index) => (
          <path
            key={`closure-${index}`}
            d={path}
            fill="none"
            stroke="#223c39"
            strokeWidth="4"
            strokeLinecap="round"
          />
        ))}
        {geometry.overpasses.map((crossing) => (
          <g key={crossing.index}>
            <path d={crossing.path} fill="none" stroke="#fbfaf6" strokeWidth="14" strokeLinecap="round" />
            <path d={crossing.path} fill="none" stroke="#223c39" strokeWidth="4" strokeLinecap="round" />
          </g>
        ))}
      </g>
      {geometry.crossingTargets.map((target) => (
        <g
          key={`target-${target.index}`}
          className={`braid-crossing-target${selectedIndex === target.index ? " selected" : ""}`}
          onPointerDown={(event) => {
            event.stopPropagation();
            onSelect(target.index);
          }}
        >
          <circle cx={target.point.x} cy={target.point.y} r="20" />
          {selectedIndex === target.index && <circle className="selection-ring" cx={target.point.x} cy={target.point.y} r="18" />}
        </g>
      ))}
      {geometry.topXs.map((x, index) => (
        <g key={`label-${index}`} className="strand-label">
          <rect x={x - 20} y="20" width="40" height="25" rx="12" />
          <text x={x} y="37" textAnchor="middle">{document.topObjects[index] || "V"}</text>
        </g>
      ))}
      {document.word.length === 0 && <text x="480" y="340" textAnchor="middle" className="canvas-hint">尚未添加交叉</text>}
    </svg>
  );
}

type BraidGeometry = {
  paths: string[];
  closures: string[];
  overpasses: { index: number; path: string }[];
  crossingTargets: { index: number; point: Point }[];
  topXs: number[];
  strandPoints: Point[][];
  bottomPositionByStrand: number[];
};

function braidSection(x0: number, y0: number, x1: number, y1: number): string {
  const middle = (y0 + y1) / 2;
  return `M ${x0} ${y0} C ${x0} ${middle} ${x1} ${middle} ${x1} ${y1}`;
}

function buildBraidGeometry(document: BraidDocument): BraidGeometry {
  const count = document.strandCount;
  const left = 210;
  const right = 710;
  const top = 66;
  const available = Math.max(1, count - 1);
  const xs = Array.from({ length: count }, (_, index) => left + (index / available) * (right - left));
  const rowHeight = Math.min(74, 500 / Math.max(1, document.word.length));
  const bottom = top + Math.max(1, document.word.length) * rowHeight;
  const positions = Array.from({ length: count }, (_, index) => index);
  const points = Array.from({ length: count }, (_, index) => [{ x: xs[index], y: top }]);
  const overpasses: { index: number; path: string }[] = [];
  const crossingTargets: { index: number; point: Point }[] = [];

  document.word.forEach((generator, row) => {
    const index = Math.abs(generator) - 1;
    const y0 = top + row * rowHeight;
    const y1 = y0 + rowHeight;
    const before = [...positions];
    const after = [...positions];
    if (index >= 0 && index < count - 1) {
      [after[index], after[index + 1]] = [after[index + 1], after[index]];
    }
    before.forEach((strand) => {
      const destination = after.indexOf(strand);
      points[strand].push({ x: xs[destination], y: y1 });
    });
    const overFrom = generator > 0 ? index : index + 1;
    const overTo = generator > 0 ? index + 1 : index;
    overpasses.push({ index: row, path: braidSection(xs[overFrom], y0, xs[overTo], y1) });
    crossingTargets.push({ index: row, point: { x: (xs[index] + xs[index + 1]) / 2, y: (y0 + y1) / 2 } });
    positions.splice(0, positions.length, ...after);
  });

  if (document.word.length === 0) {
    points.forEach((path, index) => path.push({ x: xs[index], y: bottom }));
  }
  const paths = points.map((strandPoints) =>
    strandPoints.slice(0, -1).map((point, index) => braidSection(point.x, point.y, strandPoints[index + 1].x, strandPoints[index + 1].y)).join(" "),
  );
  const closures = document.closure === "blackboard"
    ? xs.map((x, index) => {
        const outside = 790 + index * 14;
        return `M ${x} ${bottom} C ${outside} ${bottom} ${outside} ${top} ${x} ${top}`;
      })
    : [];
  const bottomPositionByStrand = Array.from({ length: count }, (_, strand) => positions.indexOf(strand));
  return { paths, closures, overpasses, crossingTargets, topXs: xs, strandPoints: points, bottomPositionByStrand };
}

function closureCompatible(document: BraidDocument): boolean {
  const bottom = [...document.topObjects];
  for (const generator of document.word) {
    const index = Math.abs(generator) - 1;
    if (index >= 0 && index < bottom.length - 1) [bottom[index], bottom[index + 1]] = [bottom[index + 1], bottom[index]];
  }
  return bottom.every((objectId, index) => objectId === document.topObjects[index]);
}

function braidToPlanar(document: BraidDocument): PlanarDocument {
  const geometry = buildBraidGeometry({ ...document, closure: "blackboard" });
  const visited = new Set<number>();
  const components: KnotComponent[] = [];
  for (let start = 0; start < document.strandCount; start += 1) {
    if (visited.has(start)) continue;
    const points: Point[] = [];
    let strand = start;
    while (!visited.has(strand)) {
      visited.add(strand);
      const strandPoints = geometry.strandPoints[strand];
      points.push(...(points.length ? strandPoints.slice(1) : strandPoints));
      const position = geometry.bottomPositionByStrand[strand];
      const bottomPoint = strandPoints[strandPoints.length - 1];
      const topPoint = geometry.strandPoints[position][0];
      const outside = 790 + position * 14;
      points.push(
        { x: outside, y: bottomPoint.y },
        { x: outside, y: topPoint.y },
        topPoint,
      );
      strand = position;
    }
    components.push({
      id: makeId("component"),
      name: components.length === 0 ? "辫闭合" : `分量 ${components.length + 1}`,
      color: PALETTE[components.length % PALETTE.length],
      objectId: document.topObjects[start] || "V",
      orientation: "forward",
      closed: true,
      nodes: nodesFromPoints(points, true, 0.72),
    });
  }
  let planar = reconcilePlanar({ kind: "planar", framing: "blackboard", components, crossings: [] });
  const rowHeight = Math.min(74, 500 / Math.max(1, document.word.length));
  planar = {
    ...planar,
    crossings: planar.crossings.map((crossing) => {
      const row = Math.round((crossing.point.y - 66) / rowHeight - 0.5);
      const generator = document.word[row];
      if (!generator || crossing.kind !== "transverse") return crossing;
      const first = findSegment(planar.components, crossing.first.segmentId);
      const second = findSegment(planar.components, crossing.second.segmentId);
      if (!first || !second) return crossing;
      const firstDx = cubicDerivative(first, crossing.first.t).x;
      const secondDx = cubicDerivative(second, crossing.second.t).x;
      const desired = generator > 0 ? 1 : -1;
      const over = Math.sign(firstDx) === desired ? "first" : Math.sign(secondDx) === desired ? "second" : crossing.over;
      return { ...crossing, over };
    }),
  };
  return planar;
}

export default function KnotStudio() {
  const [history, setHistory] = useState<History>(() => ({ past: [], present: createWorkspace(), future: [] }));
  const [mode, setMode] = useState<Mode>("planar");
  const [planarTool, setPlanarTool] = useState<PlanarTool>("select");
  const [braidTool, setBraidTool] = useState<BraidTool>("select");
  const [selection, setSelection] = useState<Selection>(null);
  const [selectedGenerator, setSelectedGenerator] = useState<number | null>(null);
  const [viewBox, setViewBox] = useState<ViewBox>(INITIAL_VIEW);
  const [freehandPreview, setFreehandPreview] = useState<Point[]>([]);
  const [toast, setToast] = useState<string>("");
  const [createdAt] = useState(() => new Date().toISOString());
  const fileInputRef = useRef<HTMLInputElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const artworkRef = useRef<SVGGElement>(null);
  const gestureStart = useRef<WorkspaceState | null>(null);
  const dragRef = useRef<
    | { kind: "node"; componentId: string; nodeId: string; origin: Point; pointer: Point }
    | { kind: "handle"; componentId: string; nodeId: string; side: "in" | "out"; pointer: Point; origin: Point }
    | { kind: "pan"; pointer: Point; view: ViewBox }
    | { kind: "freehand" }
    | null
  >(null);

  const workspace = history.present;
  const planar = workspace.planar;
  const braid = workspace.braid;
  const activeComponent = selection ? planar.components.find((item) => item.id === selection.componentId) ?? null : null;
  const activeNode = selection?.nodeId ? activeComponent?.nodes.find((node) => node.id === selection.nodeId) ?? null : null;
  const selectedCrossing = selection?.componentId === "crossing"
    ? planar.crossings.find((crossing) => crossing.id === selection.nodeId) ?? null
    : null;
  const ambiguousCount = planar.crossings.filter((crossing) => crossing.kind !== "transverse").length;
  const segments = useMemo(() => allSegments(planar.components), [planar.components]);
  const segmentById = useMemo(() => new Map(segments.map((segment) => [segment.id, segment])), [segments]);

  const flash = useCallback((message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  }, []);

  const commit = useCallback((transform: (current: WorkspaceState) => WorkspaceState) => {
    setHistory((current) => {
      const next = transform(current.present);
      if (sameWorkspace(next, current.present)) return current;
      return { past: [...current.past.slice(-199), current.present], present: next, future: [] };
    });
  }, []);

  const replacePresentFromGesture = useCallback((transform: (start: WorkspaceState) => WorkspaceState) => {
    const start = gestureStart.current;
    if (!start) return;
    setHistory((current) => ({ ...current, present: transform(start), future: [] }));
  }, []);

  const finishGesture = useCallback(() => {
    const start = gestureStart.current;
    if (!start) return;
    setHistory((current) =>
      sameWorkspace(start, current.present)
        ? current
        : { past: [...current.past.slice(-199), start], present: current.present, future: [] },
    );
    gestureStart.current = null;
  }, []);

  const undo = useCallback(() => {
    setHistory((current) => {
      const previous = current.past.at(-1);
      if (!previous) return current;
      return { past: current.past.slice(0, -1), present: previous, future: [current.present, ...current.future] };
    });
  }, []);

  const redo = useCallback(() => {
    setHistory((current) => {
      const next = current.future[0];
      if (!next) return current;
      return { past: [...current.past, current.present], present: next, future: current.future.slice(1) };
    });
  }, []);

  useEffect(() => {
    let restored: { workspace: WorkspaceState; mode: Mode } | null = null;
    try {
      const saved = localStorage.getItem(AUTOSAVE_KEY);
      if (!saved) return;
      const value = JSON.parse(saved) as { workspace?: WorkspaceState; mode?: Mode };
      if (value.workspace?.planar && value.workspace?.braid) {
        restored = {
          workspace: { ...value.workspace, planar: reconcilePlanar(value.workspace.planar) },
          mode: value.mode === "braid" ? "braid" : "planar",
        };
      }
    } catch {
      localStorage.removeItem(AUTOSAVE_KEY);
    }
    if (!restored) return;
    const savedState = restored;
    const timer = window.setTimeout(() => {
      setHistory({ past: [], present: savedState.workspace, future: [] });
      setMode(savedState.mode);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    localStorage.setItem(AUTOSAVE_KEY, JSON.stringify({ workspace, mode }));
  }, [workspace, mode]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.tagName === "INPUT" || target?.tagName === "TEXTAREA") return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        if (event.shiftKey) redo();
        else undo();
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") {
        event.preventDefault();
        redo();
        return;
      }
      if (mode === "planar") {
        const shortcuts: Record<string, PlanarTool> = { v: "select", p: "pen", f: "freehand", x: "crossing", h: "pan" };
        if (shortcuts[event.key.toLowerCase()]) setPlanarTool(shortcuts[event.key.toLowerCase()]);
        if ((event.key === "Delete" || event.key === "Backspace") && selection && selection.componentId !== "crossing") {
          event.preventDefault();
          commit((current) => {
            const component = current.planar.components.find((item) => item.id === selection.componentId);
            if (!component) return current;
            const components = selection.nodeId
              ? current.planar.components.map((item) =>
                  item.id === component.id ? { ...item, nodes: item.nodes.filter((node) => node.id !== selection.nodeId) } : item,
                ).filter((item) => item.nodes.length >= 2)
              : current.planar.components.filter((item) => item.id !== component.id);
            return { ...current, planar: reconcilePlanar({ ...current.planar, components }) };
          });
          setSelection(null);
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [commit, mode, redo, selection, undo]);

  const activeTool = mode === "planar" ? planarTool : braidTool;

  const pointerInCanvas = (event: ReactPointerEvent<SVGSVGElement>): Point =>
    projectPoint(event.currentTarget, event.clientX, event.clientY);

  const handleCanvasPointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (mode !== "planar") return;
    const point = pointerInCanvas(event);
    if (planarTool === "pan" || event.button === 1 || event.buttons === 4) {
      dragRef.current = { kind: "pan", pointer: { x: event.clientX, y: event.clientY }, view: viewBox };
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }
    if (planarTool === "freehand") {
      dragRef.current = { kind: "freehand" };
      setFreehandPreview([point]);
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }
    if (planarTool === "pen") {
      const open = planar.components.find((component) => !component.closed);
      const componentId = open?.id ?? makeId("component");
      const node: BezierNode = { id: makeId("node"), point, in: { x: 0, y: 0 }, out: { x: 0, y: 0 } };
      commit((current) => {
        const existing = current.planar.components.find((component) => component.id === componentId);
        const components = existing
          ? current.planar.components.map((component) =>
              component.id === componentId ? { ...component, nodes: [...component.nodes, node] } : component,
            )
          : [
              ...current.planar.components,
              {
                id: componentId,
                name: `分量 ${current.planar.components.length + 1}`,
                color: PALETTE[current.planar.components.length % PALETTE.length],
                objectId: "V",
                orientation: "forward" as const,
                closed: false,
                nodes: [node],
              },
            ];
        return { ...current, planar: reconcilePlanar({ ...current.planar, components }) };
      });
      setSelection({ componentId, nodeId: node.id });
      return;
    }
    setSelection(null);
  };

  const handleCanvasPointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    if (!drag) return;
    if (drag.kind === "pan") {
      const factorX = viewBox.width / event.currentTarget.clientWidth;
      const factorY = viewBox.height / event.currentTarget.clientHeight;
      setViewBox({
        ...drag.view,
        x: drag.view.x - (event.clientX - drag.pointer.x) * factorX,
        y: drag.view.y - (event.clientY - drag.pointer.y) * factorY,
      });
      return;
    }
    const point = pointerInCanvas(event);
    if (drag.kind === "freehand") {
      setFreehandPreview((current) => (distance(current.at(-1) ?? point, point) >= 3 ? [...current, point] : current));
      return;
    }
    if (drag.kind === "node") {
      const delta = subtract(point, drag.pointer);
      replacePresentFromGesture((start) => ({
        ...start,
        planar: updateComponent(start.planar, drag.componentId, (component) => ({
          ...component,
          nodes: component.nodes.map((node) =>
            node.id === drag.nodeId ? { ...node, point: add(drag.origin, delta) } : node,
          ),
        })),
      }));
      return;
    }
    const delta = subtract(point, drag.pointer);
    replacePresentFromGesture((start) => ({
      ...start,
      planar: updateComponent(start.planar, drag.componentId, (component) => ({
        ...component,
        nodes: component.nodes.map((node) => {
          if (node.id !== drag.nodeId) return node;
          const value = add(drag.origin, delta);
          return drag.side === "out"
            ? { ...node, out: value, in: scale(value, -1) }
            : { ...node, in: value, out: scale(value, -1) };
        }),
      })),
    }));
  };

  const handleCanvasPointerUp = (event: ReactPointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    dragRef.current = null;
    if (!drag) return;
    if (drag.kind === "freehand") {
      if (freehandPreview.length >= 8) {
        const points = simplifyPoints(freehandPreview, 5.5);
        const component: KnotComponent = {
          id: makeId("component"),
          name: `分量 ${planar.components.length + 1}`,
          color: PALETTE[planar.components.length % PALETTE.length],
          objectId: "V",
          orientation: "forward",
          closed: true,
          nodes: nodesFromPoints(points, true, 0.92),
        };
        commit((current) => ({
          ...current,
          planar: reconcilePlanar({ ...current.planar, components: [...current.planar.components, component] }),
        }));
        setSelection({ componentId: component.id });
      } else {
        flash("笔画太短，未创建分量");
      }
      setFreehandPreview([]);
    } else if (drag.kind === "node" || drag.kind === "handle") {
      finishGesture();
    }
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  };

  const handleNodePointerDown = (
    event: ReactPointerEvent<SVGCircleElement>,
    component: KnotComponent,
    node: BezierNode,
  ) => {
    event.stopPropagation();
    if (planarTool === "pen" && !component.closed && component.nodes[0].id === node.id && component.nodes.length >= 3) {
      commit((current) => ({
        ...current,
        planar: updateComponent(current.planar, component.id, (value) => {
          const fitted = nodesFromPoints(value.nodes.map((item) => item.point), true, 0.9);
          return {
            ...value,
            closed: true,
            nodes: fitted.map((item, index) => ({ ...item, id: value.nodes[index].id })),
          };
        }),
      }));
      setPlanarTool("select");
      flash("分量已闭合");
      return;
    }
    if (planarTool !== "select") return;
    const svg = svgRef.current;
    if (!svg) return;
    const point = projectPoint(svg, event.clientX, event.clientY);
    gestureStart.current = history.present;
    dragRef.current = { kind: "node", componentId: component.id, nodeId: node.id, origin: node.point, pointer: point };
    setSelection({ componentId: component.id, nodeId: node.id });
    svg.setPointerCapture(event.pointerId);
  };

  const handleHandlePointerDown = (
    event: ReactPointerEvent<SVGCircleElement>,
    componentId: string,
    nodeId: string,
    side: "in" | "out",
  ) => {
    event.stopPropagation();
    const svg = svgRef.current;
    if (!svg) return;
    gestureStart.current = history.present;
    dragRef.current = {
      kind: "handle",
      componentId,
      nodeId,
      side,
      pointer: projectPoint(svg, event.clientX, event.clientY),
      origin: activeNode?.id === nodeId ? activeNode[side] : { x: 0, y: 0 },
    };
    svg.setPointerCapture(event.pointerId);
  };

  const handleWheel = (event: ReactWheelEvent<SVGSVGElement>) => {
    event.preventDefault();
    const factor = event.deltaY > 0 ? 1.12 : 0.89;
    const nextWidth = Math.max(360, Math.min(2200, viewBox.width * factor));
    const ratio = nextWidth / viewBox.width;
    const nextHeight = viewBox.height * ratio;
    const point = pointerInCanvas(event as unknown as ReactPointerEvent<SVGSVGElement>);
    setViewBox({
      x: point.x - (point.x - viewBox.x) * ratio,
      y: point.y - (point.y - viewBox.y) * ratio,
      width: nextWidth,
      height: nextHeight,
    });
  };

  const toggleCrossing = (id: string) => {
    commit((current) => ({
      ...current,
      planar: {
        ...current.planar,
        crossings: current.planar.crossings.map((crossing) =>
          crossing.id === id && crossing.kind === "transverse"
            ? {
                ...crossing,
                over: crossing.over === "first" ? "second" : "first",
              }
            : crossing,
        ),
      },
    }));
  };

  const resetPlanar = () => {
    commit((current) => ({ ...current, planar: createDefaultPlanar() }));
    setSelection(null);
    setViewBox(INITIAL_VIEW);
  };

  const addBraidGenerator = (index: number, sign: 1 | -1) => {
    const value = (index + 1) * sign;
    commit((current) => ({ ...current, braid: { ...current.braid, word: [...current.braid.word, value] } }));
    setSelectedGenerator(braid.word.length);
  };

  const updateBraid = (transform: (document: BraidDocument) => BraidDocument) =>
    commit((current) => ({ ...current, braid: transform(current.braid) }));

  const setStrandCount = (count: number) => {
    const safe = Math.max(2, Math.min(9, count));
    updateBraid((document) => ({
      ...document,
      strandCount: safe,
      topObjects: Array.from({ length: safe }, (_, index) => document.topObjects[index] ?? "V"),
      word: document.word.filter((value) => Math.abs(value) < safe),
    }));
  };

  const convertBraid = () => {
    const converted = braidToPlanar(braid);
    commit((current) => ({ ...current, planar: converted }));
    setMode("planar");
    setSelection(null);
    setViewBox(INITIAL_VIEW);
    flash("已生成可独立编辑的平面副本");
  };

  const saveJson = () => {
    const project = makeProject(workspace, mode, createdAt);
    download(`${safeFileName(workspace.title)}.knot.json`, `${JSON.stringify(project, null, 2)}\n`, "application/json");
    flash("项目 JSON 已导出");
  };

  const exportSvg = () => {
    const content = artworkRef.current?.innerHTML ?? "";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 680" width="960" height="680"><rect width="960" height="680" fill="#fbfaf6"/>${content}</svg>`;
    download(`${safeFileName(workspace.title)}.svg`, svg, "image/svg+xml");
    flash("干净 SVG 已导出");
  };

  const importJson = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      const project = parseProject(JSON.parse(await file.text()));
      const next = applyProject(workspace, project);
      setHistory({ past: [...history.past, workspace], present: next, future: [] });
      setMode(project.document.kind);
      setSelection(null);
      flash("项目已载入");
    } catch (error) {
      flash(error instanceof Error ? error.message : "无法载入项目");
    }
  };

  const zoomPercent = Math.round((INITIAL_VIEW.width / viewBox.width) * 100);
  const braidValid = closureCompatible(braid);

  return (
    <main className="studio-shell">
      <header className="topbar">
        <div className="brand" aria-label="Knot Atelier">
          <div className="brand-mark" aria-hidden="true">∞</div>
          <div><strong>Knot Atelier</strong><span>扭结图工作台</span></div>
        </div>
        <div className="mode-switch" aria-label="编辑模式">
          <button type="button" className={mode === "planar" ? "active" : ""} onClick={() => setMode("planar")}>平面图</button>
          <button type="button" className={mode === "braid" ? "active" : ""} onClick={() => setMode("braid")}>辫图</button>
        </div>
        <input
          className="project-title"
          value={workspace.title}
          aria-label="项目名称"
          onChange={(event) => commit((current) => ({ ...current, title: event.target.value }))}
        />
        <div className="top-actions">
          <IconButton label="撤销" icon="↶" disabled={!history.past.length} onClick={undo} />
          <IconButton label="重做" icon="↷" disabled={!history.future.length} onClick={redo} />
          <span className="toolbar-divider" />
          <IconButton label="导入" icon="↥" onClick={() => fileInputRef.current?.click()} />
          <IconButton label="保存 JSON" icon="⌑" onClick={saveJson} />
          <IconButton label="导出 SVG" icon="⇩" onClick={exportSvg} />
          <input ref={fileInputRef} type="file" accept=".json,.knot.json,application/json" hidden onChange={importJson} />
        </div>
      </header>

      <section className="workspace-grid">
        <aside className="tool-rail" aria-label="工具栏">
          {mode === "planar" ? (
            <>
              <ToolButton icon="⌁" label="选择" shortcut="V" active={planarTool === "select"} onClick={() => setPlanarTool("select")} />
              <ToolButton icon="✒" label="钢笔" shortcut="P" active={planarTool === "pen"} onClick={() => setPlanarTool("pen")} />
              <ToolButton icon="∿" label="手绘" shortcut="F" active={planarTool === "freehand"} onClick={() => setPlanarTool("freehand")} />
              <ToolButton icon="⋈" label="交叉" shortcut="X" active={planarTool === "crossing"} onClick={() => setPlanarTool("crossing")} />
              <ToolButton icon="✥" label="平移" shortcut="H" active={planarTool === "pan"} onClick={() => setPlanarTool("pan")} />
              <div className="rail-spacer" />
              <ToolButton icon="◎" label="示例" onClick={resetPlanar} />
            </>
          ) : (
            <>
              <ToolButton icon="⌁" label="选择" active={braidTool === "select"} onClick={() => setBraidTool("select")} />
              <ToolButton icon="↘" label="正交叉" active={braidTool === "positive"} onClick={() => setBraidTool("positive")} />
              <ToolButton icon="↙" label="负交叉" active={braidTool === "negative"} onClick={() => setBraidTool("negative")} />
            </>
          )}
        </aside>

        <section className={`canvas-panel tool-${activeTool}`}>
          <div className="canvas-header">
            <div>
              <span className="eyebrow">{mode === "planar" ? "PLANAR DIAGRAM" : "BRAID WORD"}</span>
              <strong>{mode === "planar" ? "黑板标架画布" : braid.word.length ? `(${braid.word.join(", ")})` : "恒等辫"}</strong>
            </div>
            <div className="canvas-badges">
              <span>blackboard</span>
              {mode === "planar" && ambiguousCount > 0 && <span className="warning">{ambiguousCount} 个歧义</span>}
              {mode === "braid" && braid.closure === "blackboard" && !braidValid && <span className="warning">颜色不兼容</span>}
            </div>
          </div>

          <div className="canvas-stage">
            {mode === "planar" ? (
              <svg
                ref={svgRef}
                className="editor-svg"
                viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
                role="img"
                aria-label="平面扭结编辑画布"
                onPointerDown={handleCanvasPointerDown}
                onPointerMove={handleCanvasPointerMove}
                onPointerUp={handleCanvasPointerUp}
                onPointerCancel={handleCanvasPointerUp}
                onWheel={handleWheel}
              >
                <defs>
                  <pattern id="planar-grid" width="24" height="24" patternUnits="userSpaceOnUse">
                    <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#e7e4dc" strokeWidth="1" />
                  </pattern>
                </defs>
                <rect x={viewBox.x} y={viewBox.y} width={viewBox.width} height={viewBox.height} fill="#fbfaf6" />
                <rect x={viewBox.x} y={viewBox.y} width={viewBox.width} height={viewBox.height} fill="url(#planar-grid)" opacity="0.72" />
                <g ref={artworkRef}>
                  {planar.components.map((component) => (
                    <path
                      key={component.id}
                      d={pathData(component)}
                      fill="none"
                      stroke="#223c39"
                      strokeWidth="5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      data-component-id={component.id}
                    />
                  ))}
                  {planar.crossings.map((crossing) => {
                    if (crossing.kind !== "transverse" || !crossing.over) return null;
                    const isFirst = crossing.over === "first";
                    const segment = segmentById.get(isFirst ? crossing.first.segmentId : crossing.second.segmentId);
                    if (!segment) return null;
                    const tangent = normalizedTangent(segment, isFirst ? crossing.first.t : crossing.second.t, 16);
                    return (
                      <g key={crossing.id} data-crossing-id={crossing.id}>
                        <line x1={tangent.start.x} y1={tangent.start.y} x2={tangent.end.x} y2={tangent.end.y} stroke="#fbfaf6" strokeWidth="16" strokeLinecap="round" />
                        <line x1={tangent.start.x} y1={tangent.start.y} x2={tangent.end.x} y2={tangent.end.y} stroke="#223c39" strokeWidth="5" strokeLinecap="round" />
                      </g>
                    );
                  })}
                </g>
                {freehandPreview.length > 1 && (
                  <polyline points={freehandPreview.map((point) => `${point.x},${point.y}`).join(" ")} fill="none" stroke="#a75d43" strokeWidth="3" strokeLinecap="round" strokeDasharray="6 4" />
                )}
                {planar.crossings.map((crossing) => (
                  <g
                    key={`hit-${crossing.id}`}
                    className={`crossing-hit ${crossing.kind}${selectedCrossing?.id === crossing.id ? " selected" : ""}`}
                    onPointerDown={(event) => {
                      event.stopPropagation();
                      setSelection({ componentId: "crossing", nodeId: crossing.id });
                      if (planarTool === "crossing" && crossing.kind === "transverse") toggleCrossing(crossing.id);
                    }}
                    onDoubleClick={(event) => {
                      event.stopPropagation();
                      toggleCrossing(crossing.id);
                    }}
                  >
                    <circle cx={crossing.point.x} cy={crossing.point.y} r="14" />
                    {crossing.kind !== "transverse" && <text x={crossing.point.x} y={crossing.point.y + 4} textAnchor="middle">!</text>}
                  </g>
                ))}
                {planarTool === "select" && activeComponent && selection?.componentId !== "crossing" && (
                  <g className="node-editor">
                    {activeComponent.nodes.map((node) => (
                      <g key={node.id}>
                        {selection?.nodeId === node.id && (
                          <>
                            <line x1={node.point.x + node.in.x} y1={node.point.y + node.in.y} x2={node.point.x + node.out.x} y2={node.point.y + node.out.y} />
                            <circle className="handle" cx={node.point.x + node.in.x} cy={node.point.y + node.in.y} r="5" onPointerDown={(event) => handleHandlePointerDown(event, activeComponent.id, node.id, "in")} />
                            <circle className="handle" cx={node.point.x + node.out.x} cy={node.point.y + node.out.y} r="5" onPointerDown={(event) => handleHandlePointerDown(event, activeComponent.id, node.id, "out")} />
                          </>
                        )}
                        <circle className={`anchor${selection?.nodeId === node.id ? " selected" : ""}`} cx={node.point.x} cy={node.point.y} r="6" onPointerDown={(event) => handleNodePointerDown(event, activeComponent, node)} />
                      </g>
                    ))}
                  </g>
                )}
                {planarTool === "pen" && planar.components.filter((component) => !component.closed).map((component) => component.nodes.map((node) => (
                  <circle key={node.id} className="pen-anchor" cx={node.point.x} cy={node.point.y} r={component.nodes[0].id === node.id ? 8 : 5} onPointerDown={(event) => handleNodePointerDown(event, component, node)} />
                )))}
              </svg>
            ) : (
              <BraidCanvas document={braid} selectedIndex={selectedGenerator} onSelect={setSelectedGenerator} artworkRef={artworkRef} />
            )}
            {mode === "planar" && planar.components.length === 0 && <EmptyGuide mode="planar" />}
          </div>
        </section>

        <aside className="inspector">
          {mode === "planar" ? (
            <PlanarInspector
              document={planar}
              selection={selection}
              activeComponent={activeComponent}
              activeNode={activeNode}
              selectedCrossing={selectedCrossing}
              onSelectComponent={(componentId) => setSelection({ componentId })}
              onAddComponent={() => {
                setPlanarTool("pen");
                setSelection(null);
                flash("在画布上放置第一个节点");
              }}
              onUpdateComponent={(componentId, transform) =>
                commit((current) => ({ ...current, planar: updateComponent(current.planar, componentId, transform) }))
              }
              onToggleCrossing={toggleCrossing}
            />
          ) : (
            <BraidInspector
              document={braid}
              selectedIndex={selectedGenerator}
              compatible={braidValid}
              onSetStrandCount={setStrandCount}
              onUpdate={updateBraid}
              onAdd={addBraidGenerator}
              onSelect={setSelectedGenerator}
              onConvert={convertBraid}
            />
          )}
        </aside>
      </section>

      <footer className="statusbar">
        <div className="status-main"><span className="status-dot" />本地自动保存</div>
        {mode === "planar" ? (
          <>
            <span>分量 <strong>{planar.components.length}</strong></span>
            <span>交叉 <strong>{planar.crossings.length}</strong></span>
            <span className={ambiguousCount ? "status-warning" : ""}>歧义 <strong>{ambiguousCount}</strong></span>
            <span>缩放 <strong>{zoomPercent}%</strong></span>
            <button type="button" onClick={() => setViewBox(INITIAL_VIEW)}>适合画布</button>
          </>
        ) : (
          <>
            <span>股数 <strong>{braid.strandCount}</strong></span>
            <span>生成元 <strong>{braid.word.length}</strong></span>
            <span className={!braidValid && braid.closure === "blackboard" ? "status-warning" : ""}>{braid.closure === "open" ? "开放辫" : braidValid ? "闭合颜色兼容" : "闭合颜色不兼容"}</span>
          </>
        )}
        <span className="status-spacer" />
        <span>schema knot-drawer/v1</span>
      </footer>
      {toast && <div className="toast" role="status">{toast}</div>}
    </main>
  );
}

function PlanarInspector({
  document,
  selection,
  activeComponent,
  activeNode,
  selectedCrossing,
  onSelectComponent,
  onAddComponent,
  onUpdateComponent,
  onToggleCrossing,
}: {
  document: PlanarDocument;
  selection: Selection;
  activeComponent: KnotComponent | null;
  activeNode: BezierNode | null;
  selectedCrossing: PlanarDocument["crossings"][number] | null;
  onSelectComponent: (id: string) => void;
  onAddComponent: () => void;
  onUpdateComponent: (id: string, transform: (component: KnotComponent) => KnotComponent) => void;
  onToggleCrossing: (id: string) => void;
}) {
  return (
    <>
      <div className="inspector-heading"><div><span className="eyebrow">DOCUMENT</span><h2>平面图</h2></div><button type="button" className="small-primary" onClick={onAddComponent}>＋ 分量</button></div>
      <section className="inspector-section">
        <div className="section-title"><span>分量</span><small>{document.components.length}</small></div>
        <div className="component-list">
          {document.components.map((component, index) => (
            <button key={component.id} type="button" className={`component-row${selection?.componentId === component.id ? " active" : ""}`} onClick={() => onSelectComponent(component.id)}>
              <span className="color-dot" style={{ background: component.color }} />
              <span><strong>{component.name}</strong><small>{component.objectId} · {component.nodes.length} 节点</small></span>
              <span>{index + 1}</span>
            </button>
          ))}
        </div>
      </section>
      {activeComponent && (
        <section className="inspector-section form-section">
          <div className="section-title"><span>分量属性</span></div>
          <label>名称<input value={activeComponent.name} onChange={(event) => onUpdateComponent(activeComponent.id, (component) => ({ ...component, name: event.target.value }))} /></label>
          <label>对象标签<input value={activeComponent.objectId} onChange={(event) => onUpdateComponent(activeComponent.id, (component) => ({ ...component, objectId: event.target.value }))} /></label>
          <div className="segmented-row">
            <button type="button" className={activeComponent.orientation === "forward" ? "active" : ""} onClick={() => onUpdateComponent(activeComponent.id, (component) => ({ ...component, orientation: "forward" }))}>沿绘制方向</button>
            <button type="button" className={activeComponent.orientation === "reverse" ? "active" : ""} onClick={() => onUpdateComponent(activeComponent.id, (component) => ({ ...component, orientation: "reverse" }))}>反向</button>
          </div>
          {activeNode && <div className="data-card"><span>节点</span><strong>{activeNode.id}</strong><small>x {activeNode.point.x.toFixed(1)} · y {activeNode.point.y.toFixed(1)}</small></div>}
        </section>
      )}
      {selectedCrossing && (
        <section className="inspector-section form-section">
          <div className="section-title"><span>交叉点</span><small className={selectedCrossing.kind === "transverse" ? "ok" : "warn"}>{selectedCrossing.kind}</small></div>
          <div className="data-card"><span>局部符号</span><strong>{selectedCrossing.sign == null ? "未定义" : selectedCrossing.sign > 0 ? "+1" : "−1"}</strong><small>{selectedCrossing.id}</small></div>
          <button type="button" className="wide-button" disabled={selectedCrossing.kind !== "transverse"} onClick={() => onToggleCrossing(selectedCrossing.id)}>切换上穿 / 下穿</button>
          {selectedCrossing.kind !== "transverse" && <p className="help warning-copy">该位置不是普通横截交点。请移动曲线，将切点或多重点拆开。</p>}
        </section>
      )}
      {!activeComponent && !selectedCrossing && (
        <section className="inspector-section quiet-panel"><strong>选择一个对象</strong><p>选择分量、节点或交叉点后，可以在这里检查并修改它的属性。</p></section>
      )}
      <section className="inspector-section legend">
        <div className="section-title"><span>图表状态</span></div>
        <div><span className="legend-line normal" />普通交叉 <strong>{document.crossings.filter((item) => item.kind === "transverse").length}</strong></div>
        <div><span className="legend-line ambiguous" />歧义位置 <strong>{document.crossings.filter((item) => item.kind !== "transverse").length}</strong></div>
      </section>
    </>
  );
}

function BraidInspector({
  document,
  selectedIndex,
  compatible,
  onSetStrandCount,
  onUpdate,
  onAdd,
  onSelect,
  onConvert,
}: {
  document: BraidDocument;
  selectedIndex: number | null;
  compatible: boolean;
  onSetStrandCount: (count: number) => void;
  onUpdate: (transform: (document: BraidDocument) => BraidDocument) => void;
  onAdd: (index: number, sign: 1 | -1) => void;
  onSelect: (index: number | null) => void;
  onConvert: () => void;
}) {
  const selected = selectedIndex == null ? null : document.word[selectedIndex];
  const move = (direction: -1 | 1) => {
    if (selectedIndex == null) return;
    const target = selectedIndex + direction;
    if (target < 0 || target >= document.word.length) return;
    onUpdate((current) => {
      const word = [...current.word];
      [word[selectedIndex], word[target]] = [word[target], word[selectedIndex]];
      return { ...current, word };
    });
    onSelect(target);
  };
  return (
    <>
      <div className="inspector-heading"><div><span className="eyebrow">DOCUMENT</span><h2>辫图</h2></div><span className={`validation-pill ${compatible ? "ok" : "warn"}`}>{compatible ? "可闭合" : "需检查"}</span></div>
      <section className="inspector-section form-section">
        <div className="section-title"><span>边界</span></div>
        <label>股数<input type="number" min="2" max="9" value={document.strandCount} onChange={(event) => onSetStrandCount(Number(event.target.value))} /></label>
        <div className="object-grid">
          {document.topObjects.map((objectId, index) => (
            <label key={index}>第 {index + 1} 股<input value={objectId} onChange={(event) => onUpdate((current) => ({ ...current, topObjects: current.topObjects.map((value, item) => item === index ? event.target.value : value) }))} /></label>
          ))}
        </div>
        <div className="segmented-row">
          <button type="button" className={document.closure === "open" ? "active" : ""} onClick={() => onUpdate((current) => ({ ...current, closure: "open" }))}>开放</button>
          <button type="button" className={document.closure === "blackboard" ? "active" : ""} onClick={() => onUpdate((current) => ({ ...current, closure: "blackboard" }))}>黑板闭合</button>
        </div>
      </section>
      <section className="inspector-section">
        <div className="section-title"><span>添加交叉</span><small>从上到下</small></div>
        <div className="generator-grid">
          {Array.from({ length: document.strandCount - 1 }, (_, index) => (
            <div key={index}>
              <button type="button" onClick={() => onAdd(index, 1)}>σ<sub>{index + 1}</sub></button>
              <button type="button" onClick={() => onAdd(index, -1)}>σ<sub>{index + 1}</sub><sup>−1</sup></button>
            </div>
          ))}
        </div>
      </section>
      <section className="inspector-section">
        <div className="section-title"><span>生成元顺序</span><small>{document.word.length}</small></div>
        <div className="word-list">
          {document.word.map((value, index) => (
            <button key={`${index}-${value}`} type="button" className={selectedIndex === index ? "active" : ""} onClick={() => onSelect(index)}>
              <small>{index + 1}</small><strong>σ<sub>{Math.abs(value)}</sub>{value < 0 && <sup>−1</sup>}</strong>
            </button>
          ))}
          {!document.word.length && <p className="help">当前是恒等辫。</p>}
        </div>
        {selected != null && (
          <div className="word-actions">
            <button type="button" disabled={selectedIndex === 0} onClick={() => move(-1)}>上移</button>
            <button type="button" disabled={selectedIndex === document.word.length - 1} onClick={() => move(1)}>下移</button>
            <button type="button" onClick={() => {
              onUpdate((current) => ({ ...current, word: current.word.filter((_, index) => index !== selectedIndex) }));
              onSelect(null);
            }}>删除</button>
          </div>
        )}
      </section>
      <section className={`inspector-section validation-card ${compatible ? "valid" : "invalid"}`}>
        <strong>{compatible ? "顶部与底部颜色兼容" : "闭合颜色不兼容"}</strong>
        <p>{compatible ? "该 colored braid 可以形成当前 blackboard closure。" : "生成元作用后的对象词与顶部不同；调整标签或 braid word。"}</p>
      </section>
      <button type="button" className="convert-button" onClick={onConvert}>生成平面图副本 <span>→</span></button>
      <p className="help adapter-note">生成的是独立副本；平面编辑不会反向修改 braid word。</p>
    </>
  );
}
