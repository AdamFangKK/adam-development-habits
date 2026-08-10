def publish(version, content, blobs, manifest):
    key = f"v{version}"
    manifest.point_to(key)
    blobs.write(key, content)
    return key
