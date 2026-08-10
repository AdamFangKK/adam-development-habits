def run(lock, step):
    lock.acquire()
    result = step()
    lock.release()
    return result
