import io
import logging
import os
import re
import zipfile
import xml.etree.ElementTree as ET
import ssl
import asyncio
import functools

from typing import List, Optional

from googleapiclient.errors import HttpError
from .api_enablement import get_api_enablement_message
from auth.google_auth import GoogleAuthenticationError

logger = logging.getLogger(__name__)


def translate_docs_api_error(error_details: str) -> Optional[str]:
    """
    Translate Google Docs API errors into actionable LLM-friendly messages.

    Args:
        error_details: The error string from HttpError

    Returns:
        Translated error message with suggestions, or None if not a recognized pattern
    """
    error_lower = error_details.lower()

    # Pattern: Invalid deleteContentRange with segment boundary issues
    if "invalid deletecontentrange" in error_lower:
        # Try to extract the index from the error
        index_match = re.search(r"index\s+(\d+)", error_details, re.IGNORECASE)
        segment_match = re.search(r"segment[,\s]+(\d+)", error_details, re.IGNORECASE)

        suggestion = (
            "DELETION BOUNDARY ERROR: The delete range crosses a structural element boundary.\n\n"
            "WHAT WENT WRONG:\n"
            "- Google Docs has internal paragraph/element boundaries that can't be split\n"
            "- Your end_index likely clips into the next element's structure\n\n"
            "HOW TO FIX:\n"
            "1. Use get_doc_section_range to get deletion-safe boundaries\n"
            "2. Or try reducing end_index by 1-2 to avoid the boundary\n"
            "3. Or use inspect_doc_structure to see element boundaries"
        )

        if index_match:
            idx = index_match.group(1)
            suggestion += f"\n\nPROBLEM INDEX: {idx} - try ending at {int(idx) - 1} instead"

        return suggestion

    # Pattern: Index out of bounds
    if "index" in error_lower and ("must be less than" in error_lower or "out of bounds" in error_lower):
        # Extract indices if possible
        numbers = re.findall(r"\d+", error_details)
        
        suggestion = (
            "INDEX OUT OF BOUNDS: The specified index exceeds the document length.\n\n"
            "HOW TO FIX:\n"
            "1. Call inspect_doc_structure first to get the document's total_length\n"
            "2. Ensure your index is less than total_length\n"
            "3. For insertions at the end, use total_length - 1"
        )
        
        if len(numbers) >= 2:
            suggestion += f"\n\nDETAILS: You used index {numbers[0]}, but max allowed is {numbers[1]}"
        
        return suggestion

    # Pattern: startIndex must be less than endIndex
    if "startindex" in error_lower and "endindex" in error_lower:
        return (
            "INVALID RANGE: start_index must be less than end_index.\n\n"
            "HOW TO FIX:\n"
            "1. Ensure start_index < end_index\n"
            "2. Use inspect_doc_structure to verify the correct indices\n"
            "3. For single-character operations, end_index should be start_index + 1"
        )

    # Pattern: Cannot modify/delete at index 0
    if "index 0" in error_lower or "first section break" in error_lower:
        return (
            "PROTECTED INDEX: Cannot modify index 0 (the document's first section break).\n\n"
            "HOW TO FIX:\n"
            "1. Start operations at index 1, not 0\n"
            "2. The first character of actual content is always at index 1"
        )

    # Pattern: Invalid segment or segment not found
    if "segment" in error_lower and ("invalid" in error_lower or "not found" in error_lower):
        return (
            "SEGMENT ERROR: The operation targeted an invalid document segment.\n\n"
            "HOW TO FIX:\n"
            "1. Use inspect_doc_structure to see the document's current structure\n"
            "2. Ensure you're targeting the main body, not headers/footers\n"
            "3. The document structure may have changed - refetch and retry"
        )

    # Pattern: Table-related errors
    if "table" in error_lower:
        if "not found" in error_lower or "does not exist" in error_lower:
            return (
                "TABLE NOT FOUND: The specified table index doesn't exist.\n\n"
                "HOW TO FIX:\n"
                "1. Use inspect_doc_structure to see how many tables exist\n"
                "2. Table indices are 0-based (first table is index 0)\n"
                "3. Use debug_table_structure to examine table details"
            )
        elif "cell" in error_lower:
            return (
                "TABLE CELL ERROR: Invalid cell reference in table operation.\n\n"
                "HOW TO FIX:\n"
                "1. Use debug_table_structure to see actual table dimensions\n"
                "2. Row/column indices are 0-based\n"
                "3. Ensure your data array matches the table dimensions"
            )

    # Pattern: Empty or invalid request
    if "invalid request" in error_lower or "empty request" in error_lower:
        return (
            "INVALID REQUEST: The API request was malformed or empty.\n\n"
            "HOW TO FIX:\n"
            "1. Ensure all required parameters are provided\n"
            "2. Check that text content is not empty\n"
            "3. Verify index values are positive integers"
        )

    return None


class TransientNetworkError(Exception):
    """Custom exception for transient network errors after retries."""

    pass


class UserInputError(Exception):
    """Raised for user-facing input/validation errors that shouldn't be retried."""

    pass


def check_credentials_directory_permissions(credentials_dir: str = None) -> None:
    """
    Check if the service has appropriate permissions to create and write to the .credentials directory.

    Args:
        credentials_dir: Path to the credentials directory (default: uses get_default_credentials_dir())

    Raises:
        PermissionError: If the service lacks necessary permissions
        OSError: If there are other file system issues
    """
    if credentials_dir is None:
        from auth.google_auth import get_default_credentials_dir

        credentials_dir = get_default_credentials_dir()

    try:
        # Check if directory exists
        if os.path.exists(credentials_dir):
            # Directory exists, check if we can write to it
            test_file = os.path.join(credentials_dir, ".permission_test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                logger.info(
                    f"Credentials directory permissions check passed: {os.path.abspath(credentials_dir)}"
                )
            except (PermissionError, OSError) as e:
                raise PermissionError(
                    f"Cannot write to existing credentials directory '{os.path.abspath(credentials_dir)}': {e}"
                )
        else:
            # Directory doesn't exist, try to create it and its parent directories
            try:
                os.makedirs(credentials_dir, exist_ok=True)
                # Test writing to the new directory
                test_file = os.path.join(credentials_dir, ".permission_test")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                logger.info(
                    f"Created credentials directory with proper permissions: {os.path.abspath(credentials_dir)}"
                )
            except (PermissionError, OSError) as e:
                # Clean up if we created the directory but can't write to it
                try:
                    if os.path.exists(credentials_dir):
                        os.rmdir(credentials_dir)
                except (PermissionError, OSError):
                    pass
                raise PermissionError(
                    f"Cannot create or write to credentials directory '{os.path.abspath(credentials_dir)}': {e}"
                )

    except PermissionError:
        raise
    except Exception as e:
        raise OSError(
            f"Unexpected error checking credentials directory permissions: {e}"
        )


def extract_office_xml_text(file_bytes: bytes, mime_type: str) -> Optional[str]:
    """
    Very light-weight XML scraper for Word, Excel, PowerPoint files.
    Returns plain-text if something readable is found, else None.
    No external deps – just std-lib zipfile + ElementTree.
    """
    shared_strings: List[str] = []
    ns_excel_main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            targets: List[str] = []
            # Map MIME → iterable of XML files to inspect
            if (
                mime_type
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ):
                targets = ["word/document.xml"]
            elif (
                mime_type
                == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ):
                targets = [n for n in zf.namelist() if n.startswith("ppt/slides/slide")]
            elif (
                mime_type
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ):
                targets = [
                    n
                    for n in zf.namelist()
                    if n.startswith("xl/worksheets/sheet") and "drawing" not in n
                ]
                # Attempt to parse sharedStrings.xml for Excel files
                try:
                    shared_strings_xml = zf.read("xl/sharedStrings.xml")
                    shared_strings_root = ET.fromstring(shared_strings_xml)
                    for si_element in shared_strings_root.findall(
                        f"{{{ns_excel_main}}}si"
                    ):
                        text_parts = []
                        # Find all <t> elements, simple or within <r> runs, and concatenate their text
                        for t_element in si_element.findall(f".//{{{ns_excel_main}}}t"):
                            if t_element.text:
                                text_parts.append(t_element.text)
                        shared_strings.append("".join(text_parts))
                except KeyError:
                    logger.info(
                        "No sharedStrings.xml found in Excel file (this is optional)."
                    )
                except ET.ParseError as e:
                    logger.error(f"Error parsing sharedStrings.xml: {e}")
                except (
                    Exception
                ) as e:  # Catch any other unexpected error during sharedStrings parsing
                    logger.error(
                        f"Unexpected error processing sharedStrings.xml: {e}",
                        exc_info=True,
                    )
            else:
                return None

            pieces: List[str] = []
            for member in targets:
                try:
                    xml_content = zf.read(member)
                    xml_root = ET.fromstring(xml_content)
                    member_texts: List[str] = []

                    if (
                        mime_type
                        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ):
                        for cell_element in xml_root.findall(
                            f".//{{{ns_excel_main}}}c"
                        ):  # Find all <c> elements
                            value_element = cell_element.find(
                                f"{{{ns_excel_main}}}v"
                            )  # Find <v> under <c>

                            # Skip if cell has no value element or value element has no text
                            if value_element is None or value_element.text is None:
                                continue

                            cell_type = cell_element.get("t")
                            if cell_type == "s":  # Shared string
                                try:
                                    ss_idx = int(value_element.text)
                                    if 0 <= ss_idx < len(shared_strings):
                                        member_texts.append(shared_strings[ss_idx])
                                    else:
                                        logger.warning(
                                            f"Invalid shared string index {ss_idx} in {member}. Max index: {len(shared_strings) - 1}"
                                        )
                                except ValueError:
                                    logger.warning(
                                        f"Non-integer shared string index: '{value_element.text}' in {member}."
                                    )
                            else:  # Direct value (number, boolean, inline string if not 's')
                                member_texts.append(value_element.text)
                    else:  # Word or PowerPoint
                        for elem in xml_root.iter():
                            # For Word: <w:t> where w is "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                            # For PowerPoint: <a:t> where a is "http://schemas.openxmlformats.org/drawingml/2006/main"
                            if (
                                elem.tag.endswith("}t") and elem.text
                            ):  # Check for any namespaced tag ending with 't'
                                cleaned_text = elem.text.strip()
                                if (
                                    cleaned_text
                                ):  # Add only if there's non-whitespace text
                                    member_texts.append(cleaned_text)

                    if member_texts:
                        pieces.append(
                            " ".join(member_texts)
                        )  # Join texts from one member with spaces

                except ET.ParseError as e:
                    logger.warning(
                        f"Could not parse XML in member '{member}' for {mime_type} file: {e}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error processing member '{member}' for {mime_type}: {e}",
                        exc_info=True,
                    )
                    # continue processing other members

            if not pieces:  # If no text was extracted at all
                return None

            # Join content from different members (sheets/slides) with double newlines for separation
            text = "\n\n".join(pieces).strip()
            return text or None  # Ensure None is returned if text is empty after strip

    except zipfile.BadZipFile:
        logger.warning(f"File is not a valid ZIP archive (mime_type: {mime_type}).")
        return None
    except (
        ET.ParseError
    ) as e:  # Catch parsing errors at the top level if zipfile itself is XML-like
        logger.error(f"XML parsing error at a high level for {mime_type}: {e}")
        return None
    except Exception as e:
        logger.error(
            f"Failed to extract office XML text for {mime_type}: {e}", exc_info=True
        )
        return None


def handle_http_errors(
    tool_name: str, is_read_only: bool = False, service_type: Optional[str] = None
):
    """
    A decorator to handle Google API HttpErrors and transient SSL errors in a standardized way.

    It wraps a tool function, catches HttpError, logs a detailed error message,
    and raises a generic Exception with a user-friendly message.

    If is_read_only is True, it will also catch ssl.SSLError and retry with
    exponential backoff. After exhausting retries, it raises a TransientNetworkError.

    Args:
        tool_name (str): The name of the tool being decorated (e.g., 'list_calendars').
        is_read_only (bool): If True, the operation is considered safe to retry on
                             transient network errors. Defaults to False.
        service_type (str): Optional. The Google service type (e.g., 'calendar', 'gmail').
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            max_retries = 3
            base_delay = 1

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except ssl.SSLError as e:
                    if is_read_only and attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            f"SSL error in {tool_name} on attempt {attempt + 1}: {e}. Retrying in {delay} seconds..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"SSL error in {tool_name} on final attempt: {e}. Raising exception."
                        )
                        raise TransientNetworkError(
                            f"A transient SSL error occurred in '{tool_name}' after {max_retries} attempts. "
                            "This is likely a temporary network or certificate issue. Please try again shortly."
                        ) from e
                except UserInputError as e:
                    message = f"Input error in {tool_name}: {e}"
                    logger.warning(message)
                    raise e
                except HttpError as error:
                    user_google_email = kwargs.get("user_google_email", "N/A")
                    error_details = str(error)

                    # Check if this is an API not enabled error
                    if (
                        error.resp.status == 403
                        and "accessNotConfigured" in error_details
                    ):
                        enablement_msg = get_api_enablement_message(
                            error_details, service_type
                        )

                        if enablement_msg:
                            message = (
                                f"API error in {tool_name}: {enablement_msg}\n\n"
                                f"User: {user_google_email}"
                            )
                        else:
                            message = (
                                f"API error in {tool_name}: {error}. "
                                f"The required API is not enabled for your project. "
                                f"Please check the Google Cloud Console to enable it."
                            )
                    elif error.resp.status in [401, 403]:
                        # Authentication/authorization errors
                        message = (
                            f"API error in {tool_name}: {error}. "
                            f"You might need to re-authenticate for user '{user_google_email}'. "
                            f"LLM: Try 'start_google_auth' with the user's email and the appropriate service_name."
                        )
                    elif error.resp.status == 400 and service_type == "docs":
                        # Google Docs API errors - try to translate into actionable guidance
                        translated = translate_docs_api_error(error_details)
                        if translated:
                            message = f"API error in {tool_name}:\n\n{translated}\n\nOriginal error: {error}"
                        else:
                            message = f"API error in {tool_name}: {error}"
                    else:
                        # Other HTTP errors - return as-is
                        message = f"API error in {tool_name}: {error}"

                    logger.error(f"API error in {tool_name}: {error}", exc_info=True)
                    raise Exception(message) from error
                except TransientNetworkError:
                    # Re-raise without wrapping to preserve the specific error type
                    raise
                except GoogleAuthenticationError:
                    # Re-raise authentication errors without wrapping
                    raise
                except Exception as e:
                    message = f"An unexpected error occurred in {tool_name}: {e}"
                    logger.exception(message)
                    raise Exception(message) from e

        return wrapper

    return decorator
