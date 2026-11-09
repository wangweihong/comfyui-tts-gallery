# 验证记录

日期：2026-11-09（Asia/Shanghai）。

- ComfyUI 0.43.0，前端1.57.4，Python3.13.12，RTX5090D；插件已安装到本机持久化custom_nodes。
- 目录37项：36条模型示例（Breeze28、Drama3 8）及1条火辣大厨参考。全部原始音频SHA-256与登记值一致，可解码，波形与时长来自实际音频。
- 10项Python测试通过：真实节点AUDIO输出、全目录解码与校验、工作流参数和连线、用户导入编辑删除、修订冲突、并发独立实例写入、损坏音频、越界与符号链接、HTTP接口、Range、跨来源写入拒绝。
- WAV、FLAC与真实MP3均完成解码检查；MP3检查使用临时转码的火辣大厨片段，临时文件已移除。
- 3项JavaScript单元测试通过：组合筛选、消息来源校验、共享播放器切换。
- 独立图库浏览器检查通过：筛选、试听、详情、中英切换、上传编辑删除、390px移动端无横向溢出。
- 实际ComfyUI前端检查通过：节点选择写回、工作流保存恢复、新建标签页后旧工作流仍在openWorkflows中、Breeze UI与API参数一致、Drama3动态音色输入在前端扁平序列化后与API嵌套输入等价、旧画布和Nodes2.0操作、独立页面深链接加载。浏览和加载流程没有提交POST /prompt。
- `TTSVoiceGallery → BreezeTTS2VoiceClone` 与 `TTSVoiceGallery → Drama3EncodeVoice → Drama3Generate → Drama3Decode` 均在安装后生成了新的中文文案；最终FLAC保存在各自的audio/<模型>/tts-gallery目录。
- 新生成15条控制示例，执行均成功；ASR核对13条文字一致，2条“你好/您好”差异，分别为breeze-chef-clone与drama3-chef-happy。差异已保留在目录中，未改写原始文案。
- 听感、音色相似度、耳语/音量等控制效果未进行人工验收。ASR检查不能替代听感评价，目录未声明人工听感通过。

截图：gallery-zh.png、detail-mobile.png、comfy-workflow.png、nodes-classic.png、nodes-2.png。浏览器中的其他已安装插件存在与本插件无关的旧接口/资源警告；验收未修改这些插件。
