"""
Export vector layers and metadata using ForgeClient.

For each project in the user account, creates as many folders as the images inside; each
raster folder than contains - for each detection on it - the metadata about the detection
and the geometries.

Usage:
    python scripts/forge_export_layers.py output_dir

Requires `PICTERRA_API_KEY` environment variable.

Usage
-----

Set your API key in the environment and run the script:

```bash
export PICTERRA_API_KEY="your_api_key_here"
python scripts/forge_export_layers.py /path/to/output
```

You can use the '--limit' option to test downloading only N layers.

You can use the '--skip' option to skip some layers: the script will always output
a CSV file ('--csv-output') which contains the exported ids. 


Output layout
-------------

For each vector layer a folder `<vector_id>_<safe_name>/` will be created containing:

- `vector.geojson` : downloaded GeoJSON of the vector layer
- `metadata.json` : JSON with folder, raster, vector layer and detector metadata

"""
import argparse
import csv
import json
import os
import re
from typing import Any

from picterra.forge_client import ForgeClient


def safe_name(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z._-]", "_", name)[:200]


def drain_results_page(page):
    items = []
    while page is not None:
        items.extend(list(page))
        page = page.next()
    return items


def csv_to_set(csv_file: str) -> set[str]:
    result_set = set()
    assert os.path.isfile(csv_file)
    # Open the CSV file and read its content
    with open(csv_file, newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            # Add each cell's value as a string to the set
            for cell in row:
                result_set.add(cell.strip())  # Strip whitespace for clean values
    return result_set


def append_id_to_single_row_csv(csv_file: str, new_id: str):
    # Read the existing content
    file_exists = os.path.isfile(csv_file)

    # Read the existing content if the file exists
    if file_exists:
        with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            # Read the single row
            row = next(reader)
    else:
        # If the file does not exist, create a new row
        row = []

    # Append the new ID to the row
    row.append(new_id)

    # Write the updated row back to the CSV
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(row)


def main():
    # Parse command line arguments
    p = argparse.ArgumentParser()
    p.add_argument("outdir", help="Directory to write outputs")
    p.add_argument("--limit", help="Export only a max number of layers")
    p.add_argument("--skip", help="CSV path with vector layer IDs to skip")
    p.add_argument("--csv-output", help="CSV path for exported vector layer IDs", default="out.csv")
    args = p.parse_args()
    outdir = str(args.outdir)
    limit: int | None = args.limit
    skip_set = csv_to_set(args.skip) if args.skip else set()
    csv_output: str = args.csv_output
    os.makedirs(outdir, exist_ok=True)

    # Create ForgeClient (needs PICTERRA_API_KEY env var)
    client = ForgeClient()

    # Build detectors map
    detectors_map: dict[str, Any] = {}
    print("Listing detectors...")
    dp = client.list_detectors()
    for det in drain_results_page(dp):
        detectors_map[det["id"]] = det
    print(f"Found {len(detectors_map)} detectors\n")

    # Get folders via internal paginated endpoint
    print("Listing folders...")
    folders_page = client._return_results_page("folders", None)
    folders = drain_results_page(folders_page)
    print(f"Found {len(folders)} folders\n")

    count = 0
    for folder in folders:
        folder_id = folder.get("id")
        folder_name = folder.get("name")
        print(f"\nFolder: {folder_name} ({folder_id})")
        # List rasters in folder
        rp = client.list_rasters(folder_id=folder_id)
        rasters = drain_results_page(rp)
        for raster in rasters:
            raster_id = raster.get("id")
            raster_name = raster.get("name")
            print(f"  Raster: {raster_name} ({raster_id})")
            # List vector layers for raster
            vpage = client.list_raster_vector_layers(raster_id=raster_id)
            vlayers = drain_results_page(vpage)
            for vl in vlayers:
                vl_id = vl.get("id")
                if vl_id in skip_set:
                    print(f"Skip {vl_id}")
                    continue
                vl_name = vl.get("name")
                detector_id = vl.get("detector_id")
                detector_data = detectors_map.get(detector_id)
                if detector_data is None:
                    print(f"Skip {vl_name}")
                    continue
                detector_name = detector_data["name"]
                folder_for_vl = os.path.join(
                    outdir,
                    safe_name(folder_name),
                    safe_name(raster_name),
                    f"{safe_name(detector_name)}_{safe_name(vl_name)}"
                )
                os.makedirs(folder_for_vl, exist_ok=True)

                geojson_path = os.path.join(folder_for_vl, "vector.geojson")
                metadata_path = os.path.join(folder_for_vl, "metadata.json")

                print(f"    Downloading vector layer {vl_name} ({vl_id}) -> {geojson_path}")
                try:
                    client.download_vector_layer_to_file(vl_id, geojson_path)
                except Exception as e:
                    print(f"      Error downloading layer {vl_id}: {e}")
                    continue
                metadata = {
                    "id": vl_id,
                    "name": vl_name,
                    "count": vl.get("count"),
                    "created_at": vl.get("created_at"),
                    "folder": {"id": folder_id, "name": folder_name},
                    "raster": {"id": raster_id, "name": raster_name},
                    "detector": {"id": detector_id, "name": detector_name},
                }
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
                append_id_to_single_row_csv(csv_output, vl_id)
                count += 1
                if limit and count >= int(limit):
                    break
            if limit and count >= int(limit):
                break
        if limit and count >= int(limit):
            break
    print(f"Exported {count} vector layers, their ids are in {csv_output}")


if __name__ == "__main__":
    main()
