# 来源与署名

- 图库布局、颜色与交互参考用户本地 `comfyui-pose-gallery` 和 `comfyui-cinematic-gallery`。视觉标记沿用紫色强调、白色卡片和浅色背景；原图库界面由 Anhao 提供，来源 `wangweihong/ai-pose-gallery-zh`，其许可保留于 `licenses/pose-gallery-LICENSE.txt`。未复制姿态图片或人体数据。
- 本插件的 Python、JavaScript 与 CSS 为此次实现；插件代码采用 MIT 许可。
- 21条 Breeze 既有示例来自用户本地2026-10-22测试记录；每条保留原始文本、指令、生成参数、运行ID和音频SHA-256。完整盘点位于 `library/SOURCE.json`。
- 火辣大厨为用户2026-10-29用本地 Breeze TTS 2设计并冻结的合成成年男声。复用用户已有的干净参考、逐字稿和来源记录，未重新设计，未复制其他私人声线。
- 15条火辣大厨模型示例由本地 ComfyUI 为本项目生成。运行ID、实际参数、参考编号及ASR辅助复核结果位于 `library/catalog.json`。目录中的“未验收”是实际状态，不代表人工听感通过。
- Breeze 模型用法：[BreezeBlue/Breeze-TTS-2](https://huggingface.co/BreezeBlue/Breeze-TTS-2)。该模型权重与输出的许可由上游规定，不适用本插件代码的MIT许可。
- Drama3 节点用法与标签语法：[PedroMarinhoDev/ComfyUI-Drama3](https://github.com/PedroMarinhoDev/ComfyUI-Drama3)；模型：[fishaudio/drama-3](https://huggingface.co/fishaudio/drama-3)。插件未复制其模型或节点实现。
- 上游模型和节点的说明链接已写入导出的工作流 Note。试听音频是合成结果，不是官方固定音色编号列表。
