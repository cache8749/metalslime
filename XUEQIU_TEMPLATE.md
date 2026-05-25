# 雪球监控微信模板 (Xueqiu Monitor WeChat Template)

请在微信测试号后台新建模板，并填入以下内容：

### 模板标题 (Template Title)
雪球博主动态提醒

### 模板内容 (Template Content)
```text
博主：{{name.DATA}}
时间：{{time.DATA}}
内容：{{content.DATA}}
```

---
**说明：**
- `name`: 博主标识 (雪球-2292705444)
- `time`: 发帖时间 (YYYY-MM-DD HH:MM:SS)
- `content`: 帖子正文（单字段，无字数分块）
