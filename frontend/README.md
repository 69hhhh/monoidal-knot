# Knot Atelier

`Knot Atelier` 是 `monoidal-knot` 仓库中的独立前端。它不导入 Python 包，也不需要后端；
当前使用自己的 `knot-drawer/v1` JSON schema，为以后通过 adapter 接入
`BraidMorphism` 或 planar-tangle API 保留边界。

## 已支持

- 平面 knot/link 的三次 Bézier 编辑；
- 自由手绘转可编辑 Bézier 节点；
- 自动检测普通横截交点，点击切换 over/under；
- 切点和多重点警告；
- colored braid word 编辑和 blackboard closure 兼容检查；
- braid closure 单向生成独立平面图副本；
- 撤销、重做、本地自动恢复、项目 JSON 和 SVG 导出。

## 本地运行

需要 Node.js `>=22.13.0`：

```powershell
npm install
npm run dev
```

默认地址是 `http://localhost:3000`。

## 验证

```powershell
npm exec -- tsc --noEmit
npm run lint
npm test
```

核心目录：

```text
app/core/                 schema、几何和序列化
app/components/           平面图与辫图编辑器
app/adapters/             后续 monoidal-knot 适配边界
```
