import type { BraidDocument, KnotDrawerProject, PlanarDocument, WorkspaceState } from "./types";
import { createDefaultPlanar, reconcilePlanar } from "./geometry";

export function createWorkspace(): WorkspaceState {
  return {
    title: "未命名扭结",
    planar: createDefaultPlanar(),
    braid: {
      kind: "braid",
      framing: "blackboard",
      strandCount: 3,
      topObjects: ["V", "V", "V"],
      word: [1, -2, 1],
      closure: "blackboard",
    },
  };
}
export function makeProject(
  workspace: WorkspaceState,
  mode: "planar" | "braid",
  createdAt: string,
): KnotDrawerProject {
  return {
    schema: "knot-drawer",
    version: 1,
    document: mode === "planar" ? workspace.planar : workspace.braid,
    metadata: {
      title: workspace.title,
      createdAt,
      updatedAt: new Date().toISOString(),
    },
  };
}

export function parseProject(value: unknown): KnotDrawerProject {
  if (!value || typeof value !== "object") throw new Error("项目文件不是 JSON 对象。");
  const project = value as Partial<KnotDrawerProject>;
  if (project.schema !== "knot-drawer" || project.version !== 1) {
    throw new Error("不支持的项目 schema 或版本。");
  }
  if (!project.document || (project.document.kind !== "planar" && project.document.kind !== "braid")) {
    throw new Error("项目缺少有效的 diagram 文档。");
  }
  return project as KnotDrawerProject;
}

export function applyProject(workspace: WorkspaceState, project: KnotDrawerProject): WorkspaceState {
  if (project.document.kind === "planar") {
    return {
      ...workspace,
      title: project.metadata?.title || workspace.title,
      planar: reconcilePlanar(project.document as PlanarDocument),
    };
  }
  return {
    ...workspace,
    title: project.metadata?.title || workspace.title,
    braid: project.document as BraidDocument,
  };
}
