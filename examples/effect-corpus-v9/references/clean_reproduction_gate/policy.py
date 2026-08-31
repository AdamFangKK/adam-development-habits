def evaluate(fixture_has_secret, clean_environment, tools_discovered):
    return (not fixture_has_secret) and clean_environment and tools_discovered
