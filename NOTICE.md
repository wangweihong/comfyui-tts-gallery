# 来源与署名

- 图库布局、颜色与交互参考用户本地 `comfyui-pose-gallery` 和 `comfyui-cinematic-gallery`。视觉标记沿用紫色强调、白色卡片和浅色背景；原图库界面由 Anhao 提供，来源 `wangweihong/ai-pose-gallery-zh`，其许可保留于 `licenses/pose-gallery-LICENSE.txt`。未复制姿态图片或人体数据。
- 本插件的 Python、JavaScript 与 CSS 为此次实现；插件代码采用 MIT 许可。
- 21条 Breeze 既有示例来自用户本地2026-10-22测试记录；每条保留原始文本、指令、生成参数、运行ID和音频SHA-256。完整盘点位于 `library/SOURCE.json`。
- 火辣大厨为用户2026-10-29用本地 Breeze TTS 2设计并冻结的合成成年男声。复用用户已有的干净参考、逐字稿和来源记录，未重新设计，未复制其他私人声线。
- 15条火辣大厨模型示例由本地 ComfyUI 为本项目生成。运行ID、实际参数、参考编号及ASR辅助复核结果位于 `library/catalog.json`。目录中的“未验收”是实际状态，不代表人工听感通过。
- Breeze 模型用法：[BreezeBlue/Breeze-TTS-2](https://huggingface.co/BreezeBlue/Breeze-TTS-2)。该模型权重与输出的许可由上游规定，不适用本插件代码的MIT许可。
- Drama3 节点用法与标签语法：[PedroMarinhoDev/ComfyUI-Drama3](https://github.com/PedroMarinhoDev/ComfyUI-Drama3)；模型：[fishaudio/drama-3](https://huggingface.co/fishaudio/drama-3)。插件未复制其模型或节点实现。
- 上游模型和节点的说明链接已写入导出的工作流 Note。试听音频是合成结果，不是官方固定音色编号列表。

## Drama3扩展

- 新增35条配方根据上述Drama3节点文档的点标签、局部标签、导演指令和speaker标签整理，包含29条单人控制及6组双声线对话。已按用户指定顺序完成生成并收录试听；其中27条ASR文字一致、8条存在差异，全部保留真实结果。
- 第二个参考“温暖女声”直接复用用户已有的design_zh_female合成音频和文案；其原始音频SHA-256与火辣大厨不同，未复制既有同音色的voiceA/voiceB测试文件。
- 新配方的自然语言控制词是提供给模型的指令，并非确定性的音频效果。执行、文字完整性和听感分别记录，不用脚本执行成功代表人工听感通过。
