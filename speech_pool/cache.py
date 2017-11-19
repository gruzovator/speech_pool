import asyncio

__all__ = ['Cache']


class Item:
    def __init__(self):
        self.data = bytearray()
        self.cond = asyncio.Condition()
        self.completed = False


class ItemWriter:
    def __init__(self, item):
        self._item = item

    async def write(self, data):
        async with self._item.cond:
            self._item.data.extend(data)
            self._item.cond.notify_all()

    async def close(self):
        async with self._item.cond:
            self._item.completed = True
            self._item.cond.notify_all()


class ItemReader:
    def __init__(self, item):
        self._item = item
        self._offset = 0

    async def read(self):
        async with self._item.cond:
            while True:
                if self._item.completed:
                    offset, size = self._offset, len(self._item.data)
                    if offset == size:
                        return None
                    self._offset = size
                    return self._item.data[offset:]
                else:
                    offset, size = self._offset, len(self._item.data)
                    if offset < size:
                        self._offset = size
                        return self._item.data[offset:]
                    else:
                        await self._item.cond.wait()


class DataStreamCache:
    def __init__(self):
        self._items = {}

    def writer(self, key):
        item = self._items.get(key)
        if item:
            raise Exception('item exists')
        new_item = Item()
        self._items[key] = new_item
        return ItemWriter(new_item)

    def reader(self, key):
        item = self._items.get(key)
        if not item:
            raise KeyError(key)
        return ItemReader(item)

    def __contains__(self, key):
        return key in self._items


if __name__ == '__main__':
    async def producer(writer):
        for i in range(10):
            await asyncio.sleep(1)
            await writer.write([i])
        await writer.close()


    async def consumer(reader):
        while True:
            data = await reader.read()
            print(data)
            if not data:
                break


    async def test():
        cache = DataStreamCache()
        k = '1'
        # read while writing
        asyncio.ensure_future(producer(cache.writer(k)))
        await consumer(cache.reader(k))


    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
