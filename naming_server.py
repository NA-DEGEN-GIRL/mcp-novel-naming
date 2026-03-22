"""mcp-novel-naming: 고유명사 표기 변이 탐지 MCP 서버.

canonical registry에서 정규명을 수집하고 chapters 본문에서 변이/오타를 탐지.
"""

from mcp.server.fastmcp import FastMCP
from naming_variant import check_naming_variants

mcp = FastMCP("novel-naming")


@mcp.tool()
def naming_check(novel_dir: str, episode_range: str = "") -> str:
    """고유명사 표기 변이를 검사한다.

    Args:
        novel_dir: 소설 폴더 절대 경로
        episode_range: "1-10" 형식 (비어있으면 전체)
    """
    return check_naming_variants(novel_dir, episode_range)


if __name__ == "__main__":
    mcp.run(transport="stdio")
