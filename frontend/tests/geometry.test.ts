import assert from "node:assert/strict";
import test from "node:test";
import { createDefaultPlanar, makeId, nodesFromPoints, reconcilePlanar } from "../app/core/geometry";
import type { KnotComponent, PlanarDocument, Point } from "../app/core/types";

function openComponent(name: string, points: Point[], orientation: "forward" | "reverse" = "forward"): KnotComponent {
  return {
    id: makeId("test-component"),
    name,
    color: "#2f635d",
    objectId: "V",
    orientation,
    closed: false,
    nodes: nodesFromPoints(points, false, 0),
  };
}

function diagram(components: KnotComponent[]): PlanarDocument {
  return reconcilePlanar({ kind: "planar", framing: "blackboard", components, crossings: [] });
}

test("the default trefoil projection has three ordinary crossings", () => {
  const value = createDefaultPlanar();
  assert.equal(value.components.length, 1);
  assert.equal(value.crossings.length, 3);
  assert.deepEqual(value.crossings.map((crossing) => crossing.kind), ["transverse", "transverse", "transverse"]);
});

test("detects an inter-component crossing and preserves the over-under decision", () => {
  const first = openComponent("A", [{ x: 0, y: 0 }, { x: 100, y: 100 }]);
  const second = openComponent("B", [{ x: 0, y: 100 }, { x: 100, y: 0 }]);
  const value = diagram([first, second]);
  assert.equal(value.crossings.length, 1);
  const toggled: PlanarDocument = {
    ...value,
    crossings: value.crossings.map((crossing) => ({ ...crossing, over: "first" })),
  };
  assert.equal(reconcilePlanar(toggled).crossings[0].over, "first");
});

test("reversing one component reverses the oriented crossing sign", () => {
  const first = openComponent("A", [{ x: 0, y: 0 }, { x: 100, y: 100 }]);
  const forward = openComponent("B", [{ x: 0, y: 100 }, { x: 100, y: 0 }]);
  const reverse = { ...forward, orientation: "reverse" as const };
  const forwardSign = diagram([first, forward]).crossings[0].sign;
  const reverseSign = diagram([first, reverse]).crossings[0].sign;
  assert.equal(reverseSign, forwardSign === 1 ? -1 : 1);
});

test("detects a loop inside one cubic segment as two distinct branches", () => {
  const component: KnotComponent = {
    id: "loop",
    name: "loop",
    color: "#2f635d",
    objectId: "V",
    orientation: "forward",
    closed: false,
    nodes: [
      { id: "a", point: { x: 0, y: 0 }, in: { x: 0, y: 0 }, out: { x: 150, y: 200 } },
      { id: "b", point: { x: 50, y: 0 }, in: { x: -150, y: 200 }, out: { x: 0, y: 0 } },
    ],
  };
  const crossing = diagram([component]).crossings[0];
  assert.equal(crossing.kind, "transverse");
  assert.equal(crossing.first.segmentId, crossing.second.segmentId);
  assert.notEqual(crossing.first.t, crossing.second.t);
  assert.ok(crossing.over === "first" || crossing.over === "second");
});
