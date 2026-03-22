"""naming-variant: 고유명사 표기 변이 탐지 도구.

canonical registry(name-table, characters, worldbuilding)에서 정규명을 수집하고,
chapters 본문에서 변이/오타를 탐지한다.

MCP 도구로 등록되며, scripts/naming-variant 래퍼를 통해 Codex에서도 사용 가능.
"""

import os
import re
from pathlib import Path


def _safe_read(path):
    p = Path(path)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def _extract_canonical_names(novel_dir: str) -> dict[str, list[str]]:
    """설정 파일에서 정규명 + 허용 별칭을 추출한다.

    Returns:
        {canonical_name: [alias1, alias2, ...]}
        alias에는 canonical 자체도 포함.
    """
    registry: dict[str, list[str]] = {}

    # 1. reference/name-table.md — 표 형식: | 정규명 | 한자 | 별칭 | ...
    name_table = _safe_read(os.path.join(novel_dir, "reference", "name-table.md"))
    for line in name_table.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) >= 3:
            canonical = cols[1].strip()
            if canonical and canonical != "이름" and canonical != "정규명":
                aliases = [canonical]
                # 한자가 있으면 추가
                if len(cols) >= 3 and cols[2].strip():
                    aliases.append(cols[2].strip())
                # 별칭 컬럼이 있으면 추가
                if len(cols) >= 4 and cols[3].strip():
                    for a in cols[3].split(","):
                        a = a.strip()
                        if a:
                            aliases.append(a)
                registry[canonical] = aliases

    # 2. settings/03-characters.md — 캐릭터명 + 별호
    chars = _safe_read(os.path.join(novel_dir, "settings", "03-characters.md"))
    for line in chars.splitlines():
        # "## 주인공: 엽무진(葉無塵)" 또는 "### 하소연(河小燕)"
        m = re.match(r"#{2,3}\s+(?:\S+:\s+)?(\S+?)(?:\((.+?)\))?(?:\s+—|$)", line)
        if m:
            name = m.group(1)
            hanja = m.group(2)
            if name not in registry:
                registry[name] = [name]
            if hanja:
                registry[name].append(hanja)
        # "- **별호**: 잔혈검마(殘血劍魔)"
        m2 = re.search(r"\*\*별호\*\*:\s*(\S+?)(?:\((.+?)\))?(?:\s|,|$)", line)
        if m2:
            alias_name = m2.group(1)
            alias_hanja = m2.group(2)
            # 가장 최근 등록된 캐릭터에 별호 추가
            if registry:
                last_key = list(registry.keys())[-1]
                registry[last_key].append(alias_name)
                if alias_hanja:
                    registry[last_key].append(alias_hanja)

    # 3. settings/04-worldbuilding.md — 문파명, 지명, 무공명 등
    world = _safe_read(os.path.join(novel_dir, "settings", "04-worldbuilding.md"))
    for line in world.splitlines():
        # 표 형식에서 이름 추출
        if line.startswith("|") and "---" not in line:
            cols = [c.strip() for c in line.split("|")]
            for col in cols[1:]:
                # 한자 병기된 이름 추출: "화산파(華山派)"
                m = re.findall(r"(\S{2,}?)(?:\((.+?)\))", col)
                for name, hanja in m:
                    if name not in registry and len(name) >= 2:
                        registry[name] = [name, hanja]

    # 4. summaries/hanja-glossary.md
    glossary = _safe_read(os.path.join(novel_dir, "summaries", "hanja-glossary.md"))
    for line in glossary.splitlines():
        if line.startswith("|") and "---" not in line:
            cols = [c.strip() for c in line.split("|")]
            if len(cols) >= 3:
                reading = cols[1].strip()
                hanja = cols[2].strip()
                if reading and reading != "한글" and len(reading) >= 2:
                    if reading not in registry:
                        registry[reading] = [reading]
                    if hanja and hanja not in registry[reading]:
                        registry[reading].append(hanja)

    return registry


def _scan_chapters(novel_dir: str, registry: dict, episode_range: str = None) -> list[dict]:
    """chapters 본문에서 정규명 변이를 탐지한다."""
    chapters_dir = os.path.join(novel_dir, "chapters")
    if not os.path.isdir(chapters_dir):
        return []

    # 에피소드 파일 수집
    files = []
    for root, dirs, fnames in os.walk(chapters_dir):
        for f in sorted(fnames):
            if f.endswith(".md"):
                files.append(os.path.join(root, f))

    # 범위 필터
    if episode_range:
        parts = episode_range.split("-")
        if len(parts) == 2:
            start, end = int(parts[0]), int(parts[1])
            filtered = []
            for f in files:
                m = re.search(r"chapter-(\d+)", f)
                if m and start <= int(m.group(1)) <= end:
                    filtered.append(f)
            files = filtered

    findings = []

    for fpath in files:
        text = _safe_read(fpath)
        fname = os.path.basename(fpath)
        ep_match = re.search(r"chapter-(\d+)", fname)
        ep_num = int(ep_match.group(1)) if ep_match else 0

        for canonical, aliases in registry.items():
            if len(canonical) < 2:
                continue

            # 정규명의 각 글자를 포함하되 다른 형태로 쓰인 변이 찾기
            # 예: "남궁세가" → "남궁 세가", "남궁가", "남궁 가문"
            # 간단한 접근: 정규명의 첫 2글자로 시작하는 단어를 찾아 비교
            prefix = canonical[:2]
            if len(prefix) < 2:
                continue

            # 본문에서 prefix로 시작하는 연속 한글 찾기
            pattern = re.compile(prefix + r"[\w가-힣]*")
            for m in pattern.finditer(text):
                found = m.group()
                if found == canonical or found in aliases:
                    continue
                # 너무 짧은 매칭 무시
                if len(found) < 2:
                    continue
                # 변이 후보
                line_num = text[:m.start()].count("\n") + 1
                findings.append({
                    "episode": ep_num,
                    "file": fname,
                    "line": line_num,
                    "found": found,
                    "canonical": canonical,
                    "aliases": aliases,
                    "context": text[max(0, m.start() - 20):m.end() + 20].replace("\n", " "),
                })

    return findings


def check_naming_variants(novel_dir: str, episode_range: str = "") -> str:
    """고유명사 표기 변이를 검사한다.

    Args:
        novel_dir: 소설 폴더 경로
        episode_range: "1-10" 형식. 비어있으면 전체.

    Returns:
        마크다운 보고서
    """
    registry = _extract_canonical_names(novel_dir)

    if not registry:
        return "## Naming Variant Report\n\n정규명 레지스트리가 비어있습니다. reference/name-table.md 또는 settings/ 파일을 확인하세요."

    findings = _scan_chapters(novel_dir, registry, episode_range or None)

    lines = ["# Naming Variant Report\n"]
    lines.append(f"정규명 등록: {len(registry)}개\n")

    if not findings:
        lines.append("변이 후보: 0건. 표기가 일관됩니다.")
        return "\n".join(lines)

    lines.append(f"변이 후보: {len(findings)}건\n")
    lines.append("| # | 화 | 줄 | 발견 | 정규명 | 허용 별칭 | 문맥 |")
    lines.append("|---|-----|-----|------|--------|----------|------|")

    for i, f in enumerate(findings[:50], 1):  # 최대 50건
        aliases_str = ", ".join(f["aliases"][:3])
        context = f["context"].replace("|", "\\|")
        lines.append(
            f"| {i} | {f['episode']}화 | {f['line']} | {f['found']} | {f['canonical']} | {aliases_str} | ...{context}... |"
        )

    if len(findings) > 50:
        lines.append(f"\n... +{len(findings) - 50}건 생략")

    lines.append("\n> 위 후보는 자동 탐지 결과입니다. 의도적 변형(호칭, 축약)인지 오류인지는 사람이 판단하세요.")

    return "\n".join(lines)


def register_naming_variant(mcp_instance):
    """MCP 서버에 naming-variant 도구를 등록한다."""

    @mcp_instance.tool()
    async def naming_variant_check(
        novel_dir: str,
        episode_range: str = "",
    ) -> str:
        """고유명사 표기 변이를 검사한다.

        Args:
            novel_dir: 소설 폴더 절대 경로
            episode_range: "1-10" 형식 (비어있으면 전체)
        """
        return check_naming_variants(novel_dir, episode_range)
