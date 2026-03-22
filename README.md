# mcp-novel-naming

AI 소설 집필 파이프라인용 **고유명사 표기 변이 탐지** MCP 서버.

설정 파일(name-table, characters, worldbuilding, hanja-glossary)에서 정규명 레지스트리를 자동 구축하고, chapters 본문에서 변이/오타를 탐지한다.

## 왜 필요한가

장편 소설(50화+)에서 같은 대상을 다른 이름으로 부르는 문제가 누적된다:
- "남궁세가" vs "남궁 세가" vs "남궁가" vs "남궁 가문"
- "천외귀환" vs "천외 귀환"
- "빙혼검" vs "빙혼의 검"

특히 무협/사극/판타지에서 한자 병기, 별호, 축약형이 섞이면 AI 집필자도 일관성을 잃기 쉽다.

## 도구

### `naming_check`

고유명사 표기 변이를 검사한다.

**입력:**
- `novel_dir`: 소설 폴더 절대 경로
- `episode_range`: `"1-10"` 형식 (선택, 비어있으면 전체)

**정규명 수집 소스:**
- `reference/name-table.md` — 정규명 + 한자 + 별칭
- `settings/03-characters.md` — 캐릭터명 + 별호
- `settings/04-worldbuilding.md` — 문파/지명/무공명
- `summaries/hanja-glossary.md` — 한자 표기 용어

**출력:** 마크다운 변이 후보 보고서

```markdown
# Naming Variant Report

정규명 등록: 44개
변이 후보: 3건

| # | 화 | 줄 | 발견 | 정규명 | 허용 별칭 | 문맥 |
|---|-----|-----|------|--------|----------|------|
| 1 | 12화 | 45 | 남궁가 | 남궁세가 | 남궁세가, 南宮世家 | ...남궁가의 검법은... |
```

> 후보는 자동 탐지 결과. 의도적 변형(호칭, 축약)인지 오류인지는 사람이 판단.

## 설치

### MCP 서버로 사용 (Claude Code)

`.claude/settings.local.json`에 추가:

```json
{
  "mcpServers": {
    "novel-naming": {
      "command": "python3",
      "args": ["/root/novel/mcp-novel-naming/naming_server.py"]
    }
  }
}
```

### CLI로 사용 (Codex)

`scripts/novel-naming` wrapper:

```bash
scripts/novel-naming /root/novel/no-title-001
scripts/novel-naming /root/novel/no-title-001 1-10
```

## 정규명 레지스트리 형식

### reference/name-table.md

```markdown
| 정규명 | 한자 | 별칭 |
|--------|------|------|
| 엽무진 | 葉無塵 | 잔혈검마, 운검소년 |
| 화산파 | 華山派 | |
```

### settings/03-characters.md

자동 추출 패턴:
```markdown
## 주인공: 엽무진(葉無塵)
- **별호**: 잔혈검마(殘血劍魔)
```

## 제한사항

- 정규명 첫 2글자 기반 매칭이므로, 1글자 이름은 감지하지 않음
- 일반적인 조사/서술어 결합(`엽무진이`, `남궁세가에서는`, `천외귀환이었다`)은 정규화 후 비교해 정상으로 처리
- 완전히 띄어 쓴 변형(`남궁 세가`)이나 의미적 치환(`사부`, `장문인`)은 별칭 등록 또는 별도 규칙이 없으면 놓칠 수 있음
- 의도적 호칭 변형은 별칭 등록으로 예외 처리하는 편이 안전함

## 관련 레포

- [claude-codex-novel-templates-hybrid](https://github.com/NA-DEGEN-GIRL/claude-codex-novel-templates-hybrid)
- [mcp-novel-calc](https://github.com/NA-DEGEN-GIRL/mcp-novel-calc)
- [mcp-novel-hanja](https://github.com/NA-DEGEN-GIRL/mcp-novel-hanja)
- [mcp-novel-editor](https://github.com/NA-DEGEN-GIRL/mcp-novel-editor)
