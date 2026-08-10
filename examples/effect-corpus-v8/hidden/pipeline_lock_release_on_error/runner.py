def run(lock, step):
    lock.acquire()
    try:
        return step()
    finally:
        lock.release()
