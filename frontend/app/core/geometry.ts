import type {
  BezierNode,
  Crossing,
  KnotComponent,
  PlanarDocument,
  Point,
  Segment,
} from "./types";

let nextId = 0;

export function makeId(prefix: string): string {
  nextId += 1;
  return `${prefix}-${nextId.toString(36)}`;
}

export function add(a: Point, b: Point): Point {
  return { x: a.x + b.x, y: a.y + b.y };
}

export function subtract(a: Point, b: Point): Point {
  return { x: a.x - b.x, y: a.y - b.y };
}

export function scale(a: Point, factor: number): Point {
  return { x: a.x * factor, y: a.y * factor };
}

export function distance(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

export function cubicPoint(segment: Segment, t: number): Point {
  const u = 1 - t;
  return {
    x:
      u * u * u * segment.p0.x +
      3 * u * u * t * segment.p1.x +
      3 * u * t * t * segment.p2.x +
      t * t * t * segment.p3.x,
    y:
      u * u * u * segment.p0.y +
      3 * u * u * t * segment.p1.y +
      3 * u * t * t * segment.p2.y +
      t * t * t * segment.p3.y,
  };
}

export function cubicDerivative(segment: Segment, t: number): Point {
  const u = 1 - t;
  return {
    x:
      3 * u * u * (segment.p1.x - segment.p0.x) +
      6 * u * t * (segment.p2.x - segment.p1.x) +
      3 * t * t * (segment.p3.x - segment.p2.x),
    y:
      3 * u * u * (segment.p1.y - segment.p0.y) +
      6 * u * t * (segment.p2.y - segment.p1.y) +
      3 * t * t * (segment.p3.y - segment.p2.y),
  };
}

export function componentSegments(component: KnotComponent, componentIndex = 0): Segment[] {
  const count = component.nodes.length;
  if (count < 2) return [];
  const segmentCount = component.closed ? count : count - 1;
  return Array.from({ length: segmentCount }, (_, index) => {
    const start = component.nodes[index];
    const end = component.nodes[(index + 1) % count];
    return {
      id: `${component.id}:${start.id}`,
      componentId: component.id,
      componentIndex,
      index,
      startNodeId: start.id,
      endNodeId: end.id,
      p0: start.point,
      p1: add(start.point, start.out),
      p2: add(end.point, end.in),
      p3: end.point,
    };
  });
}

export function allSegments(components: KnotComponent[]): Segment[] {
  return components.flatMap((component, index) => componentSegments(component, index));
}

export function pathData(component: KnotComponent): string {
  const segments = componentSegments(component);
  if (!segments.length) return "";
  return [
    `M ${segments[0].p0.x.toFixed(2)} ${segments[0].p0.y.toFixed(2)}`,
    ...segments.map(
      (segment) =>
        `C ${segment.p1.x.toFixed(2)} ${segment.p1.y.toFixed(2)} ${segment.p2.x.toFixed(2)} ${segment.p2.y.toFixed(2)} ${segment.p3.x.toFixed(2)} ${segment.p3.y.toFixed(2)}`,
    ),
  ].join(" ");
}

type LineHit = { a: number; b: number; point: Point };

function lineIntersection(a0: Point, a1: Point, b0: Point, b1: Point): LineHit | null {
  const ax = a1.x - a0.x;
  const ay = a1.y - a0.y;
  const bx = b1.x - b0.x;
  const by = b1.y - b0.y;
  const denominator = ax * by - ay * bx;
  if (Math.abs(denominator) < 1e-8) return null;
  const dx = b0.x - a0.x;
  const dy = b0.y - a0.y;
  const a = (dx * by - dy * bx) / denominator;
  const b = (dx * ay - dy * ax) / denominator;
  const epsilon = 1e-6;
  if (a < -epsilon || a > 1 + epsilon || b < -epsilon || b > 1 + epsilon) return null;
  return { a, b, point: { x: a0.x + a * ax, y: a0.y + a * ay } };
}

function areAdjacent(first: Segment, second: Segment, components: KnotComponent[]): boolean {
  if (first.componentId !== second.componentId) return false;
  const component = components[first.componentIndex];
  const size = component.closed ? component.nodes.length : component.nodes.length - 1;
  const delta = Math.abs(first.index - second.index);
  return delta <= 1 || (component.closed && delta === size - 1);
}

function pairKey(first: Segment, second: Segment): string {
  return [first.id, second.id].sort().join("|");
}

export function findSegment(components: KnotComponent[], id: string): Segment | undefined {
  return allSegments(components).find((segment) => segment.id === id);
}

export function detectCrossings(
  components: KnotComponent[],
  previous: Crossing[] = [],
): Crossing[] {
  const segments = allSegments(components);
  const previousByKey = new Map(previous.map((crossing) => [crossing.key, crossing]));
  const results: Crossing[] = [];
  const subdivisions = 18;

  const appendCrossing = (
    first: Segment,
    second: Segment,
    key: string,
    found: { firstT: number; secondT: number; point: Point },
  ) => {
    const firstDerivative = cubicDerivative(first, found.firstT);
    const secondDerivative = cubicDerivative(second, found.secondT);
    const rawCross = firstDerivative.x * secondDerivative.y - firstDerivative.y * secondDerivative.x;
    const normalized =
      Math.abs(rawCross) /
      Math.max(1, Math.hypot(firstDerivative.x, firstDerivative.y) * Math.hypot(secondDerivative.x, secondDerivative.y));
    const firstOrientation = components[first.componentIndex].orientation === "reverse" ? -1 : 1;
    const secondOrientation = components[second.componentIndex].orientation === "reverse" ? -1 : 1;
    const signedCross = rawCross * firstOrientation * secondOrientation;
    const old = previousByKey.get(key);
    results.push({
      id: old?.id ?? makeId("crossing"),
      key,
      first: { segmentId: first.id, t: found.firstT },
      second: { segmentId: second.id, t: found.secondT },
      point: found.point,
      over: old?.over ?? (second.index >= first.index ? "second" : "first"),
      kind: normalized < 0.08 ? "tangent" : "transverse",
      sign: normalized < 0.08 ? null : signedCross >= 0 ? 1 : -1,
    });
  };

  for (let i = 0; i < segments.length; i += 1) {
    const self = segments[i];
    let selfHit: { firstT: number; secondT: number; point: Point } | null = null;
    for (let a = 0; a < subdivisions && !selfHit; a += 1) {
      const a0 = cubicPoint(self, a / subdivisions);
      const a1 = cubicPoint(self, (a + 1) / subdivisions);
      for (let b = a + 2; b < subdivisions; b += 1) {
        const b0 = cubicPoint(self, b / subdivisions);
        const b1 = cubicPoint(self, (b + 1) / subdivisions);
        const hit = lineIntersection(a0, a1, b0, b1);
        if (!hit) continue;
        selfHit = {
          firstT: (a + hit.a) / subdivisions,
          secondT: (b + hit.b) / subdivisions,
          point: hit.point,
        };
        break;
      }
    }
    if (selfHit) appendCrossing(self, self, `${self.id}|${self.id}`, selfHit);

    for (let j = i + 1; j < segments.length; j += 1) {
      const first = segments[i];
      const second = segments[j];
      if (areAdjacent(first, second, components)) continue;
      const key = pairKey(first, second);
      let found: { firstT: number; secondT: number; point: Point } | null = null;
      for (let a = 0; a < subdivisions && !found; a += 1) {
        const a0 = cubicPoint(first, a / subdivisions);
        const a1 = cubicPoint(first, (a + 1) / subdivisions);
        for (let b = 0; b < subdivisions; b += 1) {
          const b0 = cubicPoint(second, b / subdivisions);
          const b1 = cubicPoint(second, (b + 1) / subdivisions);
          const hit = lineIntersection(a0, a1, b0, b1);
          if (!hit) continue;
          found = {
            firstT: (a + hit.a) / subdivisions,
            secondT: (b + hit.b) / subdivisions,
            point: hit.point,
          };
          break;
        }
      }
      if (!found) continue;
      appendCrossing(first, second, key, found);
    }
  }

  for (let i = 0; i < results.length; i += 1) {
    const crowded = results.filter((candidate, index) => index !== i && distance(candidate.point, results[i].point) < 7);
    if (crowded.length) results[i] = { ...results[i], kind: "multiple", over: null, sign: null };
  }
  return results;
}

export function reconcilePlanar(document: PlanarDocument): PlanarDocument {
  return { ...document, crossings: detectCrossings(document.components, document.crossings) };
}

export function nodesFromPoints(points: Point[], closed = true, tension = 0.9): BezierNode[] {
  const clean = points.length > 1 && distance(points[0], points[points.length - 1]) < 1
    ? points.slice(0, -1)
    : points;
  return clean.map((point, index) => {
    const previous = clean[(index - 1 + clean.length) % clean.length] ?? point;
    const next = clean[(index + 1) % clean.length] ?? point;
    const tangent = scale(subtract(next, previous), tension / 6);
    return {
      id: makeId("node"),
      point,
      in: closed || index > 0 ? scale(tangent, -1) : { x: 0, y: 0 },
      out: closed || index < clean.length - 1 ? tangent : { x: 0, y: 0 },
    };
  });
}

function perpendicularDistance(point: Point, start: Point, end: Point): number {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  if (dx === 0 && dy === 0) return distance(point, start);
  const t = Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / (dx * dx + dy * dy)));
  return distance(point, { x: start.x + t * dx, y: start.y + t * dy });
}

export function simplifyPoints(points: Point[], tolerance = 4): Point[] {
  if (points.length <= 2) return points;
  let maxDistance = 0;
  let split = 0;
  for (let index = 1; index < points.length - 1; index += 1) {
    const value = perpendicularDistance(points[index], points[0], points[points.length - 1]);
    if (value > maxDistance) {
      maxDistance = value;
      split = index;
    }
  }
  if (maxDistance <= tolerance) return [points[0], points[points.length - 1]];
  return [
    ...simplifyPoints(points.slice(0, split + 1), tolerance).slice(0, -1),
    ...simplifyPoints(points.slice(split), tolerance),
  ];
}

export function createDefaultPlanar(): PlanarDocument {
  const count = 18;
  const points = Array.from({ length: count }, (_, index) => {
    const t = (index / count) * Math.PI * 2;
    return {
      x: 470 + 105 * (Math.sin(t) + 2 * Math.sin(2 * t)),
      y: 330 + 105 * (Math.cos(t) - 2 * Math.cos(2 * t)),
    };
  });
  const component: KnotComponent = {
    id: makeId("component"),
    name: "演示扭结",
    color: "#2f635d",
    objectId: "V",
    orientation: "forward",
    closed: true,
    nodes: nodesFromPoints(points, true, 1),
  };
  return reconcilePlanar({ kind: "planar", framing: "blackboard", components: [component], crossings: [] });
}

export function normalizedTangent(segment: Segment, t: number, length = 18): { start: Point; end: Point } {
  const point = cubicPoint(segment, t);
  const derivative = cubicDerivative(segment, t);
  const magnitude = Math.max(1, Math.hypot(derivative.x, derivative.y));
  const vector = { x: (derivative.x / magnitude) * length, y: (derivative.y / magnitude) * length };
  return { start: subtract(point, vector), end: add(point, vector) };
}
