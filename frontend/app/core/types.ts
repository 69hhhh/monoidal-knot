export type Point = { x: number; y: number };

export type BezierNode = {
  id: string;
  point: Point;
  in: Point;
  out: Point;
};

export type KnotComponent = {
  id: string;
  name: string;
  color: string;
  objectId: string;
  orientation: "forward" | "reverse";
  closed: boolean;
  nodes: BezierNode[];
};

export type CrossingKind = "transverse" | "tangent" | "overlap" | "multiple";

export type Crossing = {
  id: string;
  key: string;
  first: { segmentId: string; t: number };
  second: { segmentId: string; t: number };
  point: Point;
  over: "first" | "second" | null;
  kind: CrossingKind;
  sign: -1 | 1 | null;
};

export type PlanarDocument = {
  kind: "planar";
  framing: "blackboard";
  components: KnotComponent[];
  crossings: Crossing[];
};

export type BraidDocument = {
  kind: "braid";
  framing: "blackboard";
  strandCount: number;
  topObjects: string[];
  word: number[];
  closure: "open" | "blackboard";
};

export type WorkspaceState = {
  title: string;
  planar: PlanarDocument;
  braid: BraidDocument;
};

export type KnotDrawerProject = {
  schema: "knot-drawer";
  version: 1;
  document: PlanarDocument | BraidDocument;
  metadata: {
    title: string;
    createdAt: string;
    updatedAt: string;
  };
};

export type Segment = {
  id: string;
  componentId: string;
  componentIndex: number;
  index: number;
  startNodeId: string;
  endNodeId: string;
  p0: Point;
  p1: Point;
  p2: Point;
  p3: Point;
};
