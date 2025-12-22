"""
Google Docs Helper Functions

This module provides utility functions for common Google Docs operations
to simplify the implementation of document editing tools.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Tuple, Union, List

logger = logging.getLogger(__name__)

# ColorInput simplified to str for JSON schema compatibility with ChatGPT
# Accepts hex color strings like "#RRGGBB" or "RRGGBB"
# The _normalize_color function also handles RGB tuples/lists at runtime
ColorInput = str

# Valid alignment values
VALID_ALIGNMENTS = ["START", "END", "CENTER", "JUSTIFIED"]

# Valid named paragraph styles
VALID_NAMED_STYLES = [
    "NORMAL_TEXT",
    "TITLE",
    "SUBTITLE",
    "HEADING_1",
    "HEADING_2",
    "HEADING_3",
    "HEADING_4",
    "HEADING_5",
    "HEADING_6",
]


def _normalize_color(
    color: Optional[ColorInput], param_name: str
) -> Optional[Dict[str, float]]:
    """
    Normalize a user-supplied color into Docs API rgbColor format.

    Supports:
    - Hex strings: "#RRGGBB" or "RRGGBB"
    - Tuple/list of 3 ints (0-255) or floats (0-1)
    """
    if color is None:
        return None

    def _to_component(value: Any) -> float:
        if isinstance(value, bool):
            raise ValueError(f"{param_name} components cannot be boolean values")
        if isinstance(value, int):
            if value < 0 or value > 255:
                raise ValueError(
                    f"{param_name} components must be 0-255 when using integers"
                )
            return value / 255
        if isinstance(value, float):
            if value < 0 or value > 1:
                raise ValueError(
                    f"{param_name} components must be between 0 and 1 when using floats"
                )
            return value
        raise ValueError(f"{param_name} components must be int (0-255) or float (0-1)")

    if isinstance(color, str):
        hex_color = color.lstrip("#")
        if len(hex_color) != 6 or any(
            c not in "0123456789abcdefABCDEF" for c in hex_color
        ):
            raise ValueError(f"{param_name} must be a hex string like '#RRGGBB'")
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        return {"red": r, "green": g, "blue": b}

    if isinstance(color, (list, tuple)) and len(color) == 3:
        r = _to_component(color[0])
        g = _to_component(color[1])
        b = _to_component(color[2])
        return {"red": r, "green": g, "blue": b}

    raise ValueError(f"{param_name} must be a hex string or RGB tuple/list")


def build_text_style(
    bold: bool = None,
    italic: bool = None,
    underline: bool = None,
    strikethrough: bool = None,
    font_size: int = None,
    font_family: str = None,
    text_color: Optional[ColorInput] = None,
    background_color: Optional[ColorInput] = None,
    link_url: str = None,
) -> tuple[Dict[str, Any], list[str]]:
    """
    Build text style object for Google Docs API requests.

    Args:
        bold: Whether text should be bold
        italic: Whether text should be italic
        underline: Whether text should be underlined
        strikethrough: Whether text should have strikethrough
        font_size: Font size in points
        font_family: Font family name
        text_color: Text color as hex string or RGB tuple/list
        background_color: Background (highlight) color as hex string or RGB tuple/list
        link_url: URL to make the text a hyperlink

    Returns:
        Tuple of (text_style_dict, list_of_field_names)
    """
    text_style = {}
    fields = []

    if bold is not None:
        text_style["bold"] = bold
        fields.append("bold")

    if italic is not None:
        text_style["italic"] = italic
        fields.append("italic")

    if underline is not None:
        text_style["underline"] = underline
        fields.append("underline")

    if strikethrough is not None:
        text_style["strikethrough"] = strikethrough
        fields.append("strikethrough")

    if font_size is not None:
        text_style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
        fields.append("fontSize")

    if font_family is not None:
        text_style["weightedFontFamily"] = {"fontFamily": font_family}
        fields.append("weightedFontFamily")

    if text_color is not None:
        rgb = _normalize_color(text_color, "text_color")
        text_style["foregroundColor"] = {"color": {"rgbColor": rgb}}
        fields.append("foregroundColor")

    if background_color is not None:
        rgb = _normalize_color(background_color, "background_color")
        text_style["backgroundColor"] = {"color": {"rgbColor": rgb}}
        fields.append("backgroundColor")

    if link_url is not None:
        text_style["link"] = {"url": link_url}
        fields.append("link")

    return text_style, fields


def create_insert_text_request(index: int, text: str) -> Dict[str, Any]:
    """
    Create an insertText request for Google Docs API.

    Args:
        index: Position to insert text
        text: Text to insert

    Returns:
        Dictionary representing the insertText request
    """
    return {"insertText": {"location": {"index": index}, "text": text}}


def create_insert_text_segment_request(
    index: int, text: str, segment_id: str
) -> Dict[str, Any]:
    """
    Create an insertText request for Google Docs API with segmentId (for headers/footers).

    Args:
        index: Position to insert text
        text: Text to insert
        segment_id: Segment ID (for targeting headers/footers)

    Returns:
        Dictionary representing the insertText request with segmentId
    """
    return {
        "insertText": {
            "location": {"segmentId": segment_id, "index": index},
            "text": text,
        }
    }


def create_delete_range_request(start_index: int, end_index: int) -> Dict[str, Any]:
    """
    Create a deleteContentRange request for Google Docs API.

    Args:
        start_index: Start position of content to delete
        end_index: End position of content to delete

    Returns:
        Dictionary representing the deleteContentRange request
    """
    return {
        "deleteContentRange": {
            "range": {"startIndex": start_index, "endIndex": end_index}
        }
    }


def create_format_text_request(
    start_index: int,
    end_index: int,
    bold: bool = None,
    italic: bool = None,
    underline: bool = None,
    strikethrough: bool = None,
    font_size: int = None,
    font_family: str = None,
    text_color: Optional[ColorInput] = None,
    background_color: Optional[ColorInput] = None,
    link_url: str = None,
) -> Optional[Dict[str, Any]]:
    """
    Create an updateTextStyle request for Google Docs API.

    Args:
        start_index: Start position of text to format
        end_index: End position of text to format
        bold: Whether text should be bold
        italic: Whether text should be italic
        underline: Whether text should be underlined
        strikethrough: Whether text should have strikethrough
        font_size: Font size in points
        font_family: Font family name
        text_color: Text color as hex string or RGB tuple/list
        background_color: Background (highlight) color as hex string or RGB tuple/list
        link_url: URL to make the text a hyperlink

    Returns:
        Dictionary representing the updateTextStyle request, or None if no styles provided
    """
    text_style, fields = build_text_style(
        bold, italic, underline, strikethrough, font_size, font_family, 
        text_color, background_color, link_url
    )

    if not text_style:
        return None

    return {
        "updateTextStyle": {
            "range": {"startIndex": start_index, "endIndex": end_index},
            "textStyle": text_style,
            "fields": ",".join(fields),
        }
    }


def create_find_replace_request(
    find_text: str, replace_text: str, match_case: bool = False
) -> Dict[str, Any]:
    """
    Create a replaceAllText request for Google Docs API.

    Args:
        find_text: Text to find
        replace_text: Text to replace with
        match_case: Whether to match case exactly

    Returns:
        Dictionary representing the replaceAllText request
    """
    return {
        "replaceAllText": {
            "containsText": {"text": find_text, "matchCase": match_case},
            "replaceText": replace_text,
        }
    }


def create_insert_table_request(index: int, rows: int, columns: int) -> Dict[str, Any]:
    """
    Create an insertTable request for Google Docs API.

    Args:
        index: Position to insert table
        rows: Number of rows
        columns: Number of columns

    Returns:
        Dictionary representing the insertTable request
    """
    return {
        "insertTable": {"location": {"index": index}, "rows": rows, "columns": columns}
    }


def create_insert_page_break_request(index: int) -> Dict[str, Any]:
    """
    Create an insertPageBreak request for Google Docs API.

    Args:
        index: Position to insert page break

    Returns:
        Dictionary representing the insertPageBreak request
    """
    return {"insertPageBreak": {"location": {"index": index}}}


def create_insert_image_request(
    index: int, image_uri: str, width: int = None, height: int = None
) -> Dict[str, Any]:
    """
    Create an insertInlineImage request for Google Docs API.

    Args:
        index: Position to insert image
        image_uri: URI of the image (Drive URL or public URL)
        width: Image width in points
        height: Image height in points

    Returns:
        Dictionary representing the insertInlineImage request
    """
    request = {"insertInlineImage": {"location": {"index": index}, "uri": image_uri}}

    # Add size properties if specified
    object_size = {}
    if width is not None:
        object_size["width"] = {"magnitude": width, "unit": "PT"}
    if height is not None:
        object_size["height"] = {"magnitude": height, "unit": "PT"}

    if object_size:
        request["insertInlineImage"]["objectSize"] = object_size

    return request


def create_bullet_list_request(
    start_index: int, end_index: int, list_type: str = "UNORDERED"
) -> Dict[str, Any]:
    """
    Create a createParagraphBullets request for Google Docs API.

    Args:
        start_index: Start of text range to convert to list
        end_index: End of text range to convert to list
        list_type: Type of list ("UNORDERED" or "ORDERED")

    Returns:
        Dictionary representing the createParagraphBullets request
    """
    bullet_preset = (
        "BULLET_DISC_CIRCLE_SQUARE"
        if list_type == "UNORDERED"
        else "NUMBERED_DECIMAL_ALPHA_ROMAN"
    )

    return {
        "createParagraphBullets": {
            "range": {"startIndex": start_index, "endIndex": end_index},
            "bulletPreset": bullet_preset,
        }
    }


def validate_operation(operation: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a batch operation dictionary.

    Args:
        operation: Operation dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    op_type = operation.get("type")
    if not op_type:
        return False, "Missing 'type' field"

    # Validate required fields for each operation type
    required_fields = {
        "insert_text": ["index", "text"],
        "delete_text": ["start_index", "end_index"],
        "replace_text": ["start_index", "end_index", "text"],
        "format_text": ["start_index", "end_index"],
        "insert_table": ["index", "rows", "columns"],
        "insert_page_break": ["index"],
        "find_replace": ["find_text", "replace_text"],
    }

    if op_type not in required_fields:
        return False, f"Unsupported operation type: {op_type or 'None'}"

    for field in required_fields[op_type]:
        if field not in operation:
            return False, f"Missing required field: {field}"

    return True, ""


# ============================================================================
# PARAGRAPH STYLE HELPERS
# ============================================================================


def build_paragraph_style(
    alignment: str = None,
    indent_start: float = None,
    indent_end: float = None,
    space_above: float = None,
    space_below: float = None,
    named_style_type: str = None,
    keep_with_next: bool = None,
    line_spacing: float = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Build paragraph style object for Google Docs API requests.

    Args:
        alignment: Paragraph alignment (START, END, CENTER, JUSTIFIED)
        indent_start: Left indentation in points
        indent_end: Right indentation in points
        space_above: Space before paragraph in points
        space_below: Space after paragraph in points
        named_style_type: Named style (NORMAL_TEXT, TITLE, SUBTITLE, HEADING_1-6)
        keep_with_next: Keep paragraph with next on same page
        line_spacing: Line spacing multiplier (1.0 = single, 1.5 = 1.5x, 2.0 = double)

    Returns:
        Tuple of (paragraph_style_dict, list_of_field_names)
    """
    paragraph_style = {}
    fields = []

    if alignment is not None:
        if alignment.upper() not in VALID_ALIGNMENTS:
            raise ValueError(
                f"Invalid alignment: {alignment}. Valid values: {VALID_ALIGNMENTS}"
            )
        paragraph_style["alignment"] = alignment.upper()
        fields.append("alignment")

    if indent_start is not None:
        paragraph_style["indentStart"] = {"magnitude": indent_start, "unit": "PT"}
        fields.append("indentStart")

    if indent_end is not None:
        paragraph_style["indentEnd"] = {"magnitude": indent_end, "unit": "PT"}
        fields.append("indentEnd")

    if space_above is not None:
        paragraph_style["spaceAbove"] = {"magnitude": space_above, "unit": "PT"}
        fields.append("spaceAbove")

    if space_below is not None:
        paragraph_style["spaceBelow"] = {"magnitude": space_below, "unit": "PT"}
        fields.append("spaceBelow")

    if named_style_type is not None:
        if named_style_type.upper() not in VALID_NAMED_STYLES:
            raise ValueError(
                f"Invalid named style: {named_style_type}. Valid values: {VALID_NAMED_STYLES}"
            )
        paragraph_style["namedStyleType"] = named_style_type.upper()
        fields.append("namedStyleType")

    if keep_with_next is not None:
        paragraph_style["keepWithNext"] = keep_with_next
        fields.append("keepWithNext")

    if line_spacing is not None:
        # Line spacing is specified as percentage (100 = single, 150 = 1.5x, 200 = double)
        paragraph_style["lineSpacing"] = line_spacing * 100
        fields.append("lineSpacing")

    return paragraph_style, fields


def create_update_paragraph_style_request(
    start_index: int,
    end_index: int,
    alignment: str = None,
    indent_start: float = None,
    indent_end: float = None,
    space_above: float = None,
    space_below: float = None,
    named_style_type: str = None,
    keep_with_next: bool = None,
    line_spacing: float = None,
) -> Optional[Dict[str, Any]]:
    """
    Create an updateParagraphStyle request for Google Docs API.

    Args:
        start_index: Start position of paragraph range
        end_index: End position of paragraph range
        alignment: Paragraph alignment (START, END, CENTER, JUSTIFIED)
        indent_start: Left indentation in points
        indent_end: Right indentation in points
        space_above: Space before paragraph in points
        space_below: Space after paragraph in points
        named_style_type: Named style (NORMAL_TEXT, TITLE, SUBTITLE, HEADING_1-6)
        keep_with_next: Keep paragraph with next on same page
        line_spacing: Line spacing multiplier

    Returns:
        Dictionary representing the updateParagraphStyle request, or None if no styles provided
    """
    paragraph_style, fields = build_paragraph_style(
        alignment,
        indent_start,
        indent_end,
        space_above,
        space_below,
        named_style_type,
        keep_with_next,
        line_spacing,
    )

    if not paragraph_style:
        return None

    return {
        "updateParagraphStyle": {
            "range": {"startIndex": start_index, "endIndex": end_index},
            "paragraphStyle": paragraph_style,
            "fields": ",".join(fields),
        }
    }


# ============================================================================
# TEXT FINDING HELPERS
# ============================================================================


def extract_text_from_document(doc_data: Dict[str, Any]) -> Tuple[str, List[Dict]]:
    """
    Extract all text from a document and build segment mapping for index lookup.

    Args:
        doc_data: Google Docs document data from API

    Returns:
        Tuple of (full_text, list of segment dicts with text, start, end)
    """
    full_text = ""
    segments = []

    def collect_text_from_content(content: List[Dict]) -> None:
        nonlocal full_text
        for element in content:
            # Handle paragraph elements
            if "paragraph" in element:
                paragraph = element.get("paragraph", {})
                for pe in paragraph.get("elements", []):
                    text_run = pe.get("textRun", {})
                    if text_run and "content" in text_run:
                        start_idx = pe.get("startIndex", 0)
                        end_idx = pe.get("endIndex", 0)
                        content_text = text_run["content"]
                        full_text += content_text
                        segments.append(
                            {"text": content_text, "start": start_idx, "end": end_idx}
                        )

            # Handle table elements
            if "table" in element:
                table = element.get("table", {})
                for row in table.get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        cell_content = cell.get("content", [])
                        collect_text_from_content(cell_content)

    body_content = doc_data.get("body", {}).get("content", [])
    collect_text_from_content(body_content)

    # Sort segments by starting position
    segments.sort(key=lambda x: x["start"])

    return full_text, segments


def find_text_range(
    doc_data: Dict[str, Any], text_to_find: str, instance: int = 1
) -> Optional[Dict[str, int]]:
    """
    Find the document indices for a specific text string.

    Args:
        doc_data: Google Docs document data from API
        text_to_find: The text string to locate
        instance: Which instance to find (1 = first, 2 = second, etc.)

    Returns:
        Dict with 'start_index' and 'end_index', or None if not found
    """
    if not text_to_find:
        return None

    full_text, segments = extract_text_from_document(doc_data)

    if not full_text:
        logger.warning("Document appears to be empty")
        return None

    # Find the specified instance of the text
    found_count = 0
    search_start = 0

    while found_count < instance:
        current_index = full_text.find(text_to_find, search_start)
        if current_index == -1:
            logger.debug(
                f"Text '{text_to_find}' not found for instance {found_count + 1}"
            )
            break

        found_count += 1
        if found_count == instance:
            target_start_in_full_text = current_index
            target_end_in_full_text = current_index + len(text_to_find)

            # Map from full text position to actual document indices
            current_pos_in_full_text = 0
            start_index = -1
            end_index = -1

            for seg in segments:
                seg_start_in_full_text = current_pos_in_full_text
                seg_text_length = len(seg["text"])
                seg_end_in_full_text = seg_start_in_full_text + seg_text_length

                # Map start index
                if (
                    start_index == -1
                    and target_start_in_full_text >= seg_start_in_full_text
                    and target_start_in_full_text < seg_end_in_full_text
                ):
                    offset = target_start_in_full_text - seg_start_in_full_text
                    start_index = seg["start"] + offset

                # Map end index
                if (
                    target_end_in_full_text > seg_start_in_full_text
                    and target_end_in_full_text <= seg_end_in_full_text
                ):
                    offset = target_end_in_full_text - seg_start_in_full_text
                    end_index = seg["start"] + offset
                    break

                current_pos_in_full_text = seg_end_in_full_text

            if start_index != -1 and end_index != -1:
                logger.debug(
                    f"Found '{text_to_find}' at document range {start_index}-{end_index}"
                )
                return {"start_index": start_index, "end_index": end_index}

            # Reset and try next occurrence
            logger.warning(
                f"Failed to map text '{text_to_find}' instance {instance} to document indices"
            )

        search_start = current_index + 1

    logger.warning(
        f"Could not find instance {instance} of text '{text_to_find}' in document"
    )
    return None


def get_paragraph_range(
    doc_data: Dict[str, Any], index_within: int
) -> Optional[Dict[str, int]]:
    """
    Find the paragraph boundaries containing a specific index.

    Args:
        doc_data: Google Docs document data from API
        index_within: An index located within the target paragraph

    Returns:
        Dict with 'start_index' and 'end_index' of the paragraph, or None if not found
    """

    def find_paragraph_in_content(
        content: List[Dict],
    ) -> Optional[Dict[str, int]]:
        for element in content:
            start_idx = element.get("startIndex", 0)
            end_idx = element.get("endIndex", 0)

            # Check if index is within this element's range
            if index_within >= start_idx and index_within < end_idx:
                # If it's a paragraph, we found it
                if "paragraph" in element:
                    return {"start_index": start_idx, "end_index": end_idx}

                # If it's a table, search within cells
                if "table" in element:
                    table = element.get("table", {})
                    for row in table.get("tableRows", []):
                        for cell in row.get("tableCells", []):
                            cell_content = cell.get("content", [])
                            result = find_paragraph_in_content(cell_content)
                            if result:
                                return result

        return None

    body_content = doc_data.get("body", {}).get("content", [])
    result = find_paragraph_in_content(body_content)

    if result:
        logger.debug(
            f"Found paragraph containing index {index_within} at range {result['start_index']}-{result['end_index']}"
        )
    else:
        logger.warning(f"Could not find paragraph containing index {index_within}")

    return result


# ============================================================================
# TAB HELPERS
# ============================================================================


def get_all_tabs(doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Recursively collect all tabs from a document in a flat list with hierarchy info.

    Args:
        doc_data: Google Docs document data from API

    Returns:
        List of tab dicts with added 'level' field for nesting depth
    """
    all_tabs = []

    def add_tab_and_children(tab: Dict[str, Any], level: int = 0) -> None:
        tab_with_level = {**tab, "level": level}
        all_tabs.append(tab_with_level)

        # Process child tabs
        child_tabs = tab.get("childTabs", [])
        for child_tab in child_tabs:
            add_tab_and_children(child_tab, level + 1)

    tabs = doc_data.get("tabs", [])
    for tab in tabs:
        add_tab_and_children(tab)

    return all_tabs


def find_tab_by_id(doc_data: Dict[str, Any], tab_id: str) -> Optional[Dict[str, Any]]:
    """
    Find a specific tab by ID in a document (searches recursively).

    Args:
        doc_data: Google Docs document data from API
        tab_id: The tab ID to search for

    Returns:
        The tab dict if found, None otherwise
    """

    def search_tabs(tabs: List[Dict]) -> Optional[Dict[str, Any]]:
        for tab in tabs:
            tab_props = tab.get("tabProperties", {})
            if tab_props.get("tabId") == tab_id:
                return tab
            # Search child tabs
            child_tabs = tab.get("childTabs", [])
            if child_tabs:
                found = search_tabs(child_tabs)
                if found:
                    return found
        return None

    tabs = doc_data.get("tabs", [])
    return search_tabs(tabs)


def get_tab_text_length(document_tab: Dict[str, Any]) -> int:
    """
    Get the total text length from a DocumentTab.

    Args:
        document_tab: The documentTab object from a tab

    Returns:
        Total character count
    """
    total_length = 0

    body = document_tab.get("body", {})
    content = body.get("content", [])

    def count_text_in_content(elements: List[Dict]) -> int:
        length = 0
        for element in elements:
            if "paragraph" in element:
                for pe in element.get("paragraph", {}).get("elements", []):
                    text_run = pe.get("textRun", {})
                    if text_run and "content" in text_run:
                        length += len(text_run["content"])

            if "table" in element:
                for row in element.get("table", {}).get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        cell_content = cell.get("content", [])
                        length += count_text_in_content(cell_content)

        return length

    return count_text_in_content(content)
