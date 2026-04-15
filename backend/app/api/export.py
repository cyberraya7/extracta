import csv
import io
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.store.memory_store import store

router = APIRouter()


@router.get("/export/{format}")
async def export_data(format: str):
    if format not in ("json", "csv"):
        raise HTTPException(
            status_code=400, detail="Format must be 'json' or 'csv'"
        )

    if not store.processed:
        raise HTTPException(status_code=400, detail="No processed data to export")

    entities = store.get_entities()
    graph = store.get_graph()

    if format == "json":
        payload = {
            "entities": entities,
            "graph": graph,
        }
        content = json.dumps(payload, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=yose_export.json"},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "text", "label", "score", "occurrences", "variants"])
    for ent in entities:
        writer.writerow(
            [
                ent["id"],
                ent["text"],
                ent["label"],
                ent["score"],
                ent["occurrences"],
                "; ".join(ent.get("variants", [])),
            ]
        )
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=yose_export.csv"},
    )
