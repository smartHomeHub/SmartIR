import asyncio
import pathlib
import json
import sys

from custom_components.smartir import DeviceData

CHECK_DATA = {
    "climate": {
        "hvac_modes": ["auto", "heat", "cool", "heat_cool", "fan_only", "dry"],
    },
    "fan": {},
    "media_player": {},
}


async def test_json(file_path, docs):
    p = pathlib.Path(file_path)
    path = p.parts
    if path[0] != "codes":
        return True
    file_name = path[-1]
    device_class = path[-2]
    if device_data := DeviceData.read_file_as_json(file_path):
        if result := await DeviceData.check_file(
            file_name,
            device_data,
            device_class,
            CHECK_DATA[device_class],
        ):
            docs[device_class].append(
                {
                    "file": file_name,
                    "manufacturer": device_data["manufacturer"],
                    "models": ", ".join(device_data["supportedModels"]),
                    "controller": device_data["supportedController"],
                }
            )
            return True
    return False


async def main():
    exit = 0
    generate_docs = False
    docs = {"climate": [], "fan": [], "media_player": []}

    files = sys.argv
    files.pop(0)
    if not len(files):
        sys.exit(0)
    if files[0] == "--docs":
        files.pop(0)
        generate_docs = True

    if len(files):
        for file_path in files:
            if not await test_json(file_path, docs):
                exit = 1

        if generate_docs:
            for device_class in docs.keys():
                with open("docs/" + device_class + "_codes.json", "w") as outfile:
                    json.dump(docs[device_class], outfile)

    sys.exit(exit)


asyncio.run(main())
