# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *

def DetectFileType(path):
    with open(path, "rb") as file: header = file.read(64)

    riff_format = header[8:12]
    if header.startswith(b"\xFF\xD8\xFF"):                                                   return "image/jpeg"
    elif header.startswith(b"\x89PNG\r\n\x1a\n"):                                            return "image/png"
    elif header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):                       return "image/gif"
    elif header.startswith(b"BM"):                                                           return "image/bmp"
    elif header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):                     return "image/tiff"
    elif header.startswith(b"RIFF") and riff_format == b"WEBP":                              return "image/webp"
    elif header.startswith(b"\x00\x00\x01\x00"):                                             return "image/ico"
    elif header.startswith(b"\x00\x00\x02\x00"):                                             return "image/cur"
    elif header.startswith(b"\x38\x42\x50\x53"):                                             return "image/psd"
    elif header.startswith(b"\x76\x2F\x31\x01"):                                             return "image/exr"
    elif header.startswith(b"\x49\x49\x2A\x00\x10\x00\x00\x00\x43\x52"):                     return "image/cr2"
    elif header.startswith(b"\x4D\x4D\x00\x2A"):                                             return "image/nef"
    elif header.startswith(b"RIFF") and riff_format == b"AVI ":                              return "video/avi"
    elif header.startswith(b"ID3") or header[:2] in (b"\xFF\xFB", b"\xFF\xF3", b"\xFF\xF2"): return "audio/mpeg"
    elif header.startswith(b"fLaC"):                                                         return "audio/flac"
    elif header.startswith(b"RIFF") and riff_format == b"WAVE":                              return "audio/wav"
    elif header.startswith(b"MThd"):                                                         return "audio/midi"
    elif header.startswith(b"\x2E\x73\x6E\x64"):                                             return "audio/au"
    elif header.startswith(b"FORM") and riff_format == b"AIFF":                              return "audio/aiff"
    elif header.startswith(b"DSD "):                                                         return "audio/dsf"
    elif header.startswith(b"FRM8"):                                                         return "audio/dsd"
    elif header.startswith(b"\x00\x00\x00") and b"ftyp" in header:
        if b"M4A" in header or b"isom" in header:                                            return "audio/mp4"
        else:                                                                                return "video/mp4"
    elif header.startswith(b"OggS"):
        if b"OpusHead" in header:                                                            return "audio/opus"
        else:                                                                                return "audio/ogg"

    return "unknown"

def CleanValue(value):
    if value is None:
        return None
    if isinstance(value, bytes):
        try: return value.decode("utf-8", "replace")
        except: return base64.b64encode(value).decode()
    if isinstance(value, (list, tuple, set)): return [CleanValue(item) for item  in value]
    if isinstance(value, dict): return {str(key): CleanValue(item ) for key, item  in value.items()}
    return str(value)

def Hashes(path):
    hashers = {"MD5": hashlib.md5(), "SHA1": hashlib.sha1(), "SHA256": hashlib.sha256()}
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            for x in hashers.values(): x.update(chunk)
    return {name: hasher.hexdigest() for name, hasher in hashers.items()}

def GetEmbeddedExtractor(path, json_data):
    signatures = [
        (b"\xff\xd8\xff",      "jpg"),
        (b"\x89PNG\r\n\x1a\n", "png"),
        (b"GIF87a",            "gif"),
        (b"GIF89a",            "gif"),
        (b"BM",                "bmp"),
        (b"II*\x00",           "tiff"),
        (b"MM\x00*",           "tiff"),
        (b"%PDF",              "pdf"),
        (b"PK\x03\x04",        "zip"),
    ]

    def IsText(data):
        try:
            text = data.decode("utf-8")
            printable = sum(c.isprintable() for c in text)
            return printable / len(text) > 0.9
        except: return False

    def DetectFormat(data):
        for signature, ext in signatures:
            if data.startswith(signature): return ext
        return None

    def SaveFile(data, index, suffix):
        os.makedirs(path_folder_ouput_file_metadata_scanner, exist_ok=True)
        path = os.path.join(path_folder_ouput_file_metadata_scanner, f"{index}.{suffix}")
        with open(path, "wb") as file: file.write(data)
        Add(f"Embedded extractor: {white}{path}")
        return path
    
    with open(path, "rb") as file: content = file.read()
    streams = re.findall(rb"stream(.*?)endstream", content, re.S)
    file_count = 1
    text_count = 1
    paths      = []

    for i, stream_data in enumerate(streams):
        stream_data = stream_data.strip(b"\r\n")

        try: stream_data = zlib.decompress(stream_data)
        except: pass

        fmt = DetectFormat(stream_data)
        if fmt:
            path = SaveFile(stream_data, f"file_{file_count}", fmt)
            paths.append(path)
            file_count += 1
            continue

        blocks = re.findall(rb"[A-Za-z0-9+/=\r\n]{200,}", stream_data)
        for base64_chunk in blocks:
            try:    decoded = base64.b64decode(re.sub(rb"\s+", b"", base64_chunk))
            except: decoded = None
            if not decoded: continue

            fmt = DetectFormat(decoded)
            if fmt:
                path = SaveFile(decoded, f"File_{file_count}", fmt)
                paths.append(path)
                file_count += 1

            elif IsText(decoded):
                path = SaveFile(decoded, f"Text_{text_count}", "txt")
                paths.append(path)
                text_count += 1

        if IsText(stream_data) and len(stream_data) > 50:
            path = SaveFile(stream_data, f"Text_{text_count}", "txt")
            paths.append(path)
            text_count += 1

    if paths:
        if "Embedded extractor" not in json_data: json_data["Embedded extractor"] = paths
    
    return json_data


def GetBinaryStringsMetadata(path, json_data):
    try:
        with open(path, "rb") as file:
            data = file.read()

        candidates = re.findall(rb"[ -~]{6,}", data)
        results = []

        for raw in candidates:
            text = raw.decode("utf-8", "ignore").strip()
            if not text: continue
            if len(text) < 12: continue
            if text.count(" ") < 2: continue
            if sum(c.isalpha() for c in text) / len(text) < 0.6: continue
            if sum(c.isupper() for c in text) / max(sum(c.isalpha() for c in text), 1) > 0.6: continue
            if re.search(r"[{}\[\]^|<>~@#$%*=]", text): continue
            if re.fullmatch(r"[A-Za-z0-9+/= ]{12,}", text): continue
            results.append(text)

        if results:
            if "Binary strings" not in json_data: json_data["Binary strings"] = {}
            json_data["Binary strings"] = results
            for result in results: Add(f"Binary string: {white}{result}")
    except: pass
    return json_data

def JpegMarkers(path, json_data):
    try:
        markers = []
        with open(path, "rb") as file: data = file.read()
        i = 0
        while i < len(data) - 1:
            if data[i] == 0xFF and data[i + 1] != 0x00:
                marker = hex(data[i + 1])
                if marker: markers.append(marker)
                if i + 3 < len(data):
                    try:
                        length = struct.unpack(">H", data[i + 2:i + 4])[0]
                        i += length
                    except: i += 2
                else: i += 2
            else: i += 1
        if markers:
            if "Image" not in json_data: json_data["Image"] = {}
            unique = sorted(set(markers))
            formatted = " / ".join(unique)
            json_data["Image"]["JPEG markers"] = formatted
            Add(f"JPEG markers: {white}{formatted}")
    except: pass
    return json_data

def ExtractXmp(blob):
    m = re.search(rb"<x:xmpmeta.*?</x:xmpmeta>", blob, re.DOTALL)
    if not m: return None
    try: return m.group(0).decode("utf-8", "replace")
    except: return base64.b64encode(m.group(0)).decode()

def GetXmpMetadata(path, json_data):
    try:
        with open(path, "rb") as file:
            blob = file.read()
        xmp = ExtractXmp(blob)
        if xmp:
            if "XMP" not in json_data: json_data["XMP"] = {}
            json_data["XMP"]["RAW"] = xmp
            Add(f"XMP: {white}{xmp}")
    except: pass
    return json_data

def GetImageMetadata(path, json_data):
    if "Image" not in json_data: json_data["Image"] = {}
    try:
        exif = piexif.load(path)
        for ifd, tags in exif.items():
            if isinstance(tags, dict):
                for tag_id, value in tags.items():
                    name = piexif.TAGS.get(ifd, {}).get(tag_id, {}).get("name", tag_id)
                    cleaned = CleanValue(value)
                    if cleaned:
                        key = f"{ifd}:{name}"
                        json_data["Image"][key] = cleaned
                        Add(f"{key}: {white}{cleaned}")
    except: pass

    try:
        with open(path, "rb") as file:
            tags = exifread.process_file(file, details=True, strict=False)
            for key, value in tags.items():
                cleaned = CleanValue(value)
                if cleaned:
                    json_data["Image"][key] = cleaned
                    Add(f"{key}: {white}{cleaned}")
    except: pass

    try:
        with PIL.Image.open(path) as img:
            if img.format:
                json_data["Image"]["Format"] = img.format
                Add(f"Image format: {white}{img.format}")

            if img.mode:
                json_data["Image"]["Mode"] = img.mode
                Add(f"Image mode: {white}{img.mode}")

            if img.width and img.height:
                json_data["Image"]["Width"] = img.width
                json_data["Image"]["Height"] = img.height
                json_data["Image"]["Dimension"] = f"{img.width}x{img.height}"
                Add(f"Image width: {white}{img.width}")
                Add(f"Image height: {white}{img.height}")
                Add(f"Image dimension: {white}{json_data['Image']['Dimension']}")

            bands = img.getbands()
            if bands:
                if isinstance(bands, (list, tuple)): formated_bands = " / ".join(map(str, bands))
                else: formated_bands = str(bands)
                json_data["Image"]["Bands"] = formated_bands
                json_data["Image"]["Channels"] = len(bands)
                Add(f"Image bands: {white}{formated_bands}")
                Add(f"Image channels: {white}{len(bands)}")

            info = img.info
            if isinstance(info, dict):
                if "Info" not in json_data["Image"]:
                    json_data["Image"]["Info"] = {}
                for key, value in info.items():
                    cleaned = CleanValue(value)
                    if cleaned:
                        if isinstance(cleaned, (list, tuple, set)): cleaned = " / ".join(map(str, cleaned))
                        else: cleaned
                        json_data["Image"]["Info"][key] = cleaned
                        Add(f"Image {key}: {white}{cleaned}")

            dpi = img.info.get("dpi")
            if dpi:
                json_data["Image"]["X Resolution"] = dpi[0]
                json_data["Image"]["Y Resolution"] = dpi[1]
                json_data["Image"]["Resolution Unit"] = "inch"
                Add(f"Image x resolution: {white}{dpi[0]}")
                Add(f"Image y resolution: {white}{dpi[1]}")

            if hasattr(img, "tag_v2"):
                for key, value in img.tag_v2.items():
                    cleaned = CleanValue(value)
                    if cleaned:
                        if "Tiff" not in json_data["Image"]:  json_data["Image"]["Tiff"] = {}
                        json_data["Image"]["Tiff"][str(key)] = cleaned
                        Add(f"Tiff {key}: {white}{cleaned}")

            if "icc_profile" in img.info and img.info["icc_profile"]:
                icc = base64.b64encode(img.info["icc_profile"]).decode()
                json_data["Image"]["ICC profile"] = icc
                Add(f"ICC profile: {white}{icc}")
    except: pass
    return json_data

def GetAudioMetadata(path, json_data):
    try:
        audio = mutagen.File(path, easy=False)
        if not audio: return json_data
        if "Audio" not in json_data: json_data["Audio"] = {}

        if hasattr(audio, "mime") and audio.mime:
            mime = audio.mime
            if isinstance(mime, (list, tuple)): mime = " / ".join(mime)
            if mime:
                json_data["Audio"]["Type"] = mime
                Add(f"Audio type: {white}{mime}")

        for key, value in audio.items():
            if key.startswith("APIC") and hasattr(value, "data"):
                cover = {}
                if hasattr(value, "mime") and value.mime:
                    cover["Mime"] = value.mime
                    Add(f"Audio cover mime: {white}{value.mime}")
                if hasattr(value, "type"):
                    cover["Type"] = str(value.type)
                    Add(f"Audio cover type: {white}{cover['Type']}")
                if hasattr(value, "desc") and value.desc:
                    cover["Description"] = value.desc
                    Add(f"Audio cover description: {white}{value.desc}")
                if value.data:
                    cover["Size"] = len(value.data)
                    Add(f"Audio cover size: {white}{cover['Size']}")
                    cover["MD5"] = hashlib.md5(value.data).hexdigest()
                    Add(f"Audio cover MD5: {white}{cover['MD5']}")
                    cover["SHA256"] = hashlib.sha256(value.data).hexdigest()
                    Add(f"Audio cover SHA256: {white}{cover['SHA256']}")
                if cover:
                    json_data["Audio"]["Cover"] = cover
            else:
                cleaned = CleanValue(value)
                if cleaned:
                    json_data["Audio"][key] = cleaned
                    Add(f"Audio {key}: {white}{cleaned}")

        if hasattr(audio, "info"):
            info = audio.info
            if hasattr(info, "length"):
                json_data["Audio"]["Duration"] = info.length
                Add(f"Audio duration: {white}{info.length}")
            if hasattr(info, "bitrate"):
                json_data["Audio"]["Bitrate"] = info.bitrate
                Add(f"Audio bitrate: {white}{info.bitrate}")
            if hasattr(info, "sample_rate"):
                json_data["Audio"]["SampleRate"] = info.sample_rate
                Add(f"Audio sample rate: {white}{info.sample_rate}")
            if hasattr(info, "channels"):
                json_data["Audio"]["Channels"] = info.channels
                Add(f"Audio channels: {white}{info.channels}")
    except: pass
    return json_data

def GetFileMetadata(path, json_data):
    try:
        st = os.stat(path)
        if "File" not in json_data: json_data["File"] = {}
        name = os.path.basename(path)
        if name:
            json_data["File"]["Name"] = name
            Add(f"File name: {white}{name}")
        full_path = os.path.abspath(path)
        if full_path:
            json_data["File"]["Path"] = full_path
            Add(f"File path: {white}{full_path}")
        if hasattr(st, "st_size"):
            json_data["File"]["Size"] = st.st_size
            Add(f"File size: {white}{st.st_size}")
        if hasattr(st, "st_ctime"):
            json_data["File"]["Created"] = time.ctime(st.st_ctime)
            Add(f"File created: {white}{json_data['File']['Created']}")
        if hasattr(st, "st_mtime"):
            json_data["File"]["Modified"] = time.ctime(st.st_mtime)
            Add(f"File modified: {white}{json_data['File']['Modified']}")
        if hasattr(st, "st_atime"):
            json_data["File"]["Accessed"] = time.ctime(st.st_atime)
            Add(f"File accessed: {white}{json_data['File']['Accessed']}")
        if hasattr(st, "st_mode"):
            mode = st.st_mode
            perms = []
            flags = (
                (stat.S_IRUSR, "read owner"), (stat.S_IWUSR, "write owner"), (stat.S_IXUSR, "exec owner"), (stat.S_IRGRP, "read group"), (stat.S_IWGRP, "write group"), 
                (stat.S_IXGRP, "exec group"), (stat.S_IROTH, "read other"), (stat.S_IWOTH, "write other"), (stat.S_IXOTH, "exec other"), (stat.S_ISUID, "setuid"), 
                (stat.S_ISGID, "setgid"), (stat.S_ISVTX, "sticky bit"), (stat.S_IFREG, "regular file"), (stat.S_IFDIR, "directory"), (stat.S_IFLNK, "symlink"), 
                (stat.S_IFSOCK, "socket"), (stat.S_IFIFO, "fifo"), (stat.S_IFBLK, "block device"), (stat.S_IFCHR, "char device"),
            )
            for flag, name in flags:
                try:
                    if stat.S_IFMT(mode) == flag or mode & flag: perms.append(name)
                except: pass
            if perms:
                json_data["File"]["Permissions"] = f"{mode}: " + str(" / ".join(sorted(set(perms))))
                Add(f"File permissions: {white}{json_data['File']['Permissions']}")
    except: pass
    return json_data

def GetHashesMetadata(path, json_data):
    try:
        hashes = Hashes(path)
        if not hashes: return json_data
        if "Hashes" not in json_data: json_data["Hashes"] = {}
        for name, value in hashes.items():
            if value:
                json_data["Hashes"][name] = value
                Add(f"{name}: {white}{value}")
    except: pass
    return json_data

def FileMetadataScanner(path=None, output=None):
    Title("File Metadata Scanner")
    
    if not path: path = Input("File path [-p] -> ")
    if not os.path.exists(path): ErrorPath()

    Wait(f"Metadata scanning..")

    state = {"stop": False, "completed": 0, "completed_total": 9}
    StartThread(StatsPressed, state, time_start=time.time())

    json_data = {}
    ftype = DetectFileType(path)
    state["completed"] += 1
    json_data = GetFileMetadata(path, json_data)
    state["completed"] += 1
    if ftype.startswith("image/"): json_data = GetImageMetadata(path, json_data)
    state["completed"] += 1
    if ftype == ("image/jpeg")   : json_data = JpegMarkers(path, json_data)
    state["completed"] += 1
    if ftype.startswith("audio/"): json_data = GetAudioMetadata(path, json_data)
    state["completed"] += 1
    json_data = GetXmpMetadata(path, json_data)
    state["completed"] += 1
    json_data = GetEmbeddedExtractor(path, json_data)
    state["completed"] += 1
    json_data = GetBinaryStringsMetadata(path, json_data)
    state["completed"] += 1
    json_data = GetHashesMetadata(path, json_data)
    state["completed"] += 1
    state["stop"] = True

    if output in (True, None): SaveJsonToFile(json_data, f"Result_FileMetadata_{os.path.basename(path)}", json_output=output)
    Continue()
    Reset()