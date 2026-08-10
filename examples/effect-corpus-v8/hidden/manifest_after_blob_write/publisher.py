def publish(version, content, blobs, manifest):
    key = f"v{version}"
    blobs.write(key, content)
    manifest.point_to(key)
    return key
