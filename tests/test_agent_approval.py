from app.tools.research_tools import build_tools


def get_tool_names(tools) -> list[str]:
    return [
        tool.metadata.name
        for tool in tools
    ]


def test_save_tool_is_unavailable_without_approval() -> None:
    tools = build_tools(
        approved_to_save=False,
    )

    tool_names = get_tool_names(tools)

    assert "save_report" not in tool_names


def test_save_tool_is_available_after_approval() -> None:
    tools = build_tools(
        approved_to_save=True,
    )

    tool_names = get_tool_names(tools)

    assert "save_report" in tool_names