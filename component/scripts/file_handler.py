from pathlib import Path
from typing import Optional, Any
import json
import ast
import io
import pandas as pd
from sepal_ui.solara import get_current_sepal_client
from pathlib import Path
from typing import Optional, Any
import io
import pandas as pd


def read_file(file_path: str, **pd_args) -> Any:

    if not file_path or str(file_path).strip() in ["", "."]:
        raise ValueError("File path cannot be empty")

    file_path = str(Path(file_path))
    suffix = Path(file_path).suffix.lower()

    from_local = not str(file_path).startswith("/home/sepal-user") and str(
        file_path
    ).startswith("/home")

    sepal_session = get_current_sepal_client()

    # 1) FETCH RAW DATA (bytes or str)
    if sepal_session and not from_local:
        try:
            raw = sepal_session.get_file(file_path)
        except Exception as e:
            raise Exception("File not found or inaccessible: " + str(e))
    else:
        p = Path(file_path)
        if not p.exists():
            raise Exception(f"File not found: {file_path}")
        raw = p.read_bytes()

    # 2) UNWRAP nested repr-of-bytes if present
    if isinstance(raw, (bytes, bytearray)):
        try:
            text = raw.decode("utf-8")
            if text.startswith(("b'", 'b"')) and text.endswith(("'", '"')):
                # literal_eval safely converts "b'…'" → actual bytes
                raw = ast.literal_eval(text)
        except (UnicodeDecodeError, ValueError):
            pass
    elif isinstance(raw, str):
        if raw.startswith(("b'", 'b"')) and raw.endswith(("'", '"')):
            raw = ast.literal_eval(raw)

    # 3) JSON case
    if suffix == ".json":
        text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
        return json.loads(text)

    # 4) CSV case
    if suffix == ".csv":
        b = raw if isinstance(raw, (bytes, bytearray)) else raw.encode("utf-8")
        return pd.read_csv(io.BytesIO(b), **pd_args)

    # 5) fallback: return raw as-is
    return raw


def df_to_csv(
    df: pd.DataFrame,
    file_path: str,
    sepal_session: Optional[Any] = None,
    **to_csv_kwargs,
) -> Optional[Path]:

    buf = io.StringIO()
    df.to_csv(buf, **{"index": False, **to_csv_kwargs})
    csv_text = buf.getvalue()

    sepal_session = get_current_sepal_client()
    if sepal_session:
        # send the CSV _text_ as your `file` field
        return sepal_session.set_file(file_path, csv_text)
    else:
        # write a real .csv on disk
        p = Path(file_path)
        p.write_text(csv_text, encoding="utf-8")
        return p
